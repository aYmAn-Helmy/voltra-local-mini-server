package com.ayman.voltra.voltra_mobile

import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.ByteArrayOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URI
import java.nio.charset.StandardCharsets
import java.util.Locale
import java.util.concurrent.Executors
import javax.net.ssl.SSLSocket
import javax.net.ssl.SSLSocketFactory

class MainActivity : FlutterFragmentActivity() {
    private val executor = Executors.newCachedThreadPool()
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.ayman.voltra/native_http"
        ).setMethodCallHandler { call, result ->
            if (call.method != "request") {
                result.notImplemented()
                return@setMethodCallHandler
            }

            executor.execute {
                try {
                    val response = executeRequest(call)
                    mainHandler.post { result.success(response) }
                } catch (error: Exception) {
                    val message = error.message ?: error.javaClass.simpleName
                    mainHandler.post {
                        result.error("native_http_error", message, null)
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        executor.shutdownNow()
        super.onDestroy()
    }

    private fun executeRequest(call: MethodCall): Map<String, Any> {
        val url = call.argument<String>("url")
            ?: throw IllegalArgumentException("URL is required")
        val method = (call.argument<String>("method") ?: "GET")
            .uppercase(Locale.US)
        val body = call.argument<String>("body") ?: ""
        val connectTimeout = call.argument<Int>("connectTimeoutMs") ?: 8000
        val readTimeout = call.argument<Int>("readTimeoutMs") ?: 10000
        val headers = call.argument<Map<String, String>>("headers") ?: emptyMap()

        val uri = URI(url)
        val scheme = uri.scheme?.lowercase(Locale.US)
            ?: throw IllegalArgumentException("URL scheme is required")
        if (scheme != "http" && scheme != "https") {
            throw IllegalArgumentException("Only HTTP and HTTPS are supported")
        }

        val host = uri.host ?: throw IllegalArgumentException("URL host is required")
        val port = if (uri.port > 0) {
            uri.port
        } else if (scheme == "https") {
            443
        } else {
            80
        }

        val rawSocket = Socket()
        rawSocket.connect(InetSocketAddress(host, port), connectTimeout)
        rawSocket.soTimeout = readTimeout

        val socket: Socket = if (scheme == "https") {
            createVerifiedTlsSocket(rawSocket, host, port, readTimeout)
        } else {
            rawSocket
        }

        socket.use { active ->
            val output = BufferedOutputStream(active.getOutputStream())
            val input = BufferedInputStream(active.getInputStream())
            val bodyBytes = body.toByteArray(StandardCharsets.UTF_8)

            val rawPath = uri.rawPath?.takeIf { it.isNotEmpty() } ?: "/"
            val target = if (uri.rawQuery.isNullOrEmpty()) {
                rawPath
            } else {
                "$rawPath?${uri.rawQuery}"
            }

            val defaultPort = (scheme == "https" && port == 443) ||
                (scheme == "http" && port == 80)
            val hostHeader = if (defaultPort) host else "$host:$port"

            val request = StringBuilder()
            request.append(method).append(' ').append(target)
                .append(" HTTP/1.1\r\n")
            request.append("Host: ").append(hostHeader).append("\r\n")
            request.append("Connection: close\r\n")
            request.append("Accept: application/json\r\n")
            request.append("User-Agent: Voltra-Mobile/1.3.1 (Android)\r\n")

            for ((name, value) in headers) {
                val lower = name.lowercase(Locale.US)
                if (lower == "host" ||
                    lower == "connection" ||
                    lower == "content-length" ||
                    lower == "user-agent"
                ) {
                    continue
                }
                request.append(name).append(": ").append(value).append("\r\n")
            }

            if (bodyBytes.isNotEmpty()) {
                request.append("Content-Length: ")
                    .append(bodyBytes.size)
                    .append("\r\n")
            }
            request.append("\r\n")

            output.write(request.toString().toByteArray(StandardCharsets.ISO_8859_1))
            if (bodyBytes.isNotEmpty()) {
                output.write(bodyBytes)
            }
            output.flush()

            val statusLine = readAsciiLine(input)
                ?: throw IllegalStateException("Server closed before HTTP status")
            val statusParts = statusLine.split(' ', limit = 3)
            if (statusParts.size < 2) {
                throw IllegalStateException("Invalid HTTP status line: $statusLine")
            }
            val statusCode = statusParts[1].toIntOrNull()
                ?: throw IllegalStateException("Invalid HTTP status code")
            val reasonPhrase = if (statusParts.size >= 3) statusParts[2] else ""

            val responseHeaders = linkedMapOf<String, String>()
            while (true) {
                val line = readAsciiLine(input)
                    ?: throw IllegalStateException("Server closed while reading headers")
                if (line.isEmpty()) break
                val separator = line.indexOf(':')
                if (separator <= 0) continue
                val name = line.substring(0, separator).trim()
                val value = line.substring(separator + 1).trim()
                val existing = responseHeaders[name]
                responseHeaders[name] =
                    if (existing == null) value else "$existing, $value"
            }

            val lowerHeaders = responseHeaders.entries.associate {
                it.key.lowercase(Locale.US) to it.value
            }
            val responseBody = when {
                method == "HEAD" || statusCode == 204 || statusCode == 304 ->
                    ByteArray(0)
                lowerHeaders["transfer-encoding"]
                    ?.lowercase(Locale.US)
                    ?.contains("chunked") == true ->
                    readChunkedBody(input)
                lowerHeaders["content-length"] != null -> {
                    val length = lowerHeaders["content-length"]!!
                        .substringBefore(',')
                        .trim()
                        .toIntOrNull()
                        ?: throw IllegalStateException("Invalid Content-Length")
                    readExact(input, length)
                }
                else -> readUntilClose(input)
            }

            return mapOf(
                "statusCode" to statusCode,
                "reasonPhrase" to reasonPhrase,
                "headers" to responseHeaders,
                "body" to String(responseBody, StandardCharsets.UTF_8),
            )
        }
    }

    private fun createVerifiedTlsSocket(
        rawSocket: Socket,
        host: String,
        port: Int,
        readTimeout: Int,
    ): SSLSocket {
        val factory = SSLSocketFactory.getDefault() as SSLSocketFactory
        val tls = factory.createSocket(rawSocket, host, port, true) as SSLSocket
        tls.soTimeout = readTimeout

        // RouterOS 7.24.5 is externally verified with TLS 1.2.
        if (tls.supportedProtocols.contains("TLSv1.2")) {
            tls.enabledProtocols = arrayOf("TLSv1.2")
        }

        // Keep Android's default trust store and require HTTPS hostname checks.
        val parameters = tls.sslParameters
        parameters.endpointIdentificationAlgorithm = "HTTPS"
        tls.sslParameters = parameters
        tls.startHandshake()
        return tls
    }

    private fun readAsciiLine(input: BufferedInputStream): String? {
        val buffer = ByteArrayOutputStream()
        var previous = -1
        while (true) {
            val current = input.read()
            if (current == -1) {
                if (buffer.size() == 0) return null
                break
            }
            if (previous == '\r'.code && current == '\n'.code) {
                val bytes = buffer.toByteArray()
                return String(
                    bytes,
                    0,
                    (bytes.size - 1).coerceAtLeast(0),
                    StandardCharsets.ISO_8859_1,
                )
            }
            buffer.write(current)
            previous = current
        }
        return buffer.toString(StandardCharsets.ISO_8859_1.name())
    }

    private fun readExact(input: BufferedInputStream, length: Int): ByteArray {
        if (length <= 0) return ByteArray(0)
        val result = ByteArray(length)
        var offset = 0
        while (offset < length) {
            val count = input.read(result, offset, length - offset)
            if (count < 0) {
                throw IllegalStateException(
                    "Server closed before Content-Length was received"
                )
            }
            offset += count
        }
        return result
    }

    private fun readChunkedBody(input: BufferedInputStream): ByteArray {
        val output = ByteArrayOutputStream()
        while (true) {
            val sizeLine = readAsciiLine(input)
                ?: throw IllegalStateException("Server closed during chunk header")
            val sizeText = sizeLine.substringBefore(';').trim()
            val size = sizeText.toIntOrNull(16)
                ?: throw IllegalStateException("Invalid chunk size")
            if (size == 0) {
                while (true) {
                    val trailer = readAsciiLine(input) ?: break
                    if (trailer.isEmpty()) break
                }
                break
            }
            output.write(readExact(input, size))
            val ending = readExact(input, 2)
            if (ending.size != 2 ||
                ending[0] != '\r'.code.toByte() ||
                ending[1] != '\n'.code.toByte()
            ) {
                throw IllegalStateException("Invalid chunk terminator")
            }
        }
        return output.toByteArray()
    }

    private fun readUntilClose(input: BufferedInputStream): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        while (true) {
            val count = try {
                input.read(buffer)
            } catch (error: Exception) {
                // RouterOS may close/reset TLS after a complete HTTP response.
                if (output.size() > 0) break else throw error
            }
            if (count < 0) break
            if (count > 0) output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }
}
