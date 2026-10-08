import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

/// Android-only HTTP client backed by a small native socket/TLS bridge.
///
/// The native side uses the platform trust store and HTTPS hostname verification.
/// It never installs a permissive TrustManager or certificate callback.
class AndroidNativeHttpClient extends http.BaseClient {
  static const MethodChannel _channel =
      MethodChannel('com.ayman.voltra/native_http');

  bool _closed = false;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    if (_closed) {
      throw http.ClientException('HTTP client is closed.', request.url);
    }

    final bodyBytes = await request.finalize().toBytes();
    try {
      final raw = await _channel.invokeMapMethod<String, dynamic>(
        'request',
        <String, dynamic>{
          'url': request.url.toString(),
          'method': request.method,
          'headers': request.headers,
          'body': utf8.decode(bodyBytes, allowMalformed: true),
          'connectTimeoutMs': 8000,
          'readTimeoutMs': 10000,
        },
      );

      if (raw == null) {
        throw http.ClientException(
          'Android HTTP transport returned no response.',
          request.url,
        );
      }

      final statusCode = raw['statusCode'];
      if (statusCode is! int) {
        throw http.ClientException(
          'Android HTTP transport returned an invalid status.',
          request.url,
        );
      }

      final responseHeaders = <String, String>{};
      final dynamic headerData = raw['headers'];
      if (headerData is Map) {
        for (final entry in headerData.entries) {
          responseHeaders[entry.key.toString()] = entry.value.toString();
        }
      }

      final responseBody = raw['body']?.toString() ?? '';
      final encodedBody = utf8.encode(responseBody);
      return http.StreamedResponse(
        Stream<List<int>>.value(encodedBody),
        statusCode,
        contentLength: encodedBody.length,
        headers: responseHeaders,
        reasonPhrase: raw['reasonPhrase']?.toString(),
        request: request,
      );
    } on PlatformException catch (error) {
      final detail = error.message?.trim();
      throw http.ClientException(
        detail == null || detail.isEmpty
            ? 'Android HTTPS transport failed.'
            : detail,
        request.url,
      );
    }
  }

  @override
  void close() {
    _closed = true;
  }
}
