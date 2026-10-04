from __future__ import annotations

import ipaddress
import socket
import time


class ProvisioningError(RuntimeError):
    """Raised when the strip setup service cannot complete a provisioning step."""


def _validate_ipv4(value: str, field: str) -> str:
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise ValueError(f"{field} must be a valid IPv4 address") from exc


def _validate_credentials(ssid: str, password: str) -> None:
    if not ssid or len(ssid) > 64:
        raise ValueError("invalid Wi-Fi SSID")
    if len(password) > 128:
        raise ValueError("Wi-Fi password is too long")
    for label, value in (("SSID", ssid), ("Wi-Fi password", password)):
        if any(char in value for char in (":", "\r", "\n")):
            raise ValueError(f"{label} contains unsupported characters for MTTL setup protocol")


def _read_response(sock: socket.socket, limit: int = 2048) -> str:
    chunks: list[bytes] = []
    remaining = limit
    while remaining > 0:
        chunk = sock.recv(min(512, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
        if b"\n" in chunk:
            break
    return b"".join(chunks).decode("utf-8", errors="replace").strip("\x00\r\n ")


def _exchange(device_ip: str, port: int, timeout: float, command: str) -> str:
    with socket.create_connection((device_ip, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        sock.sendall((command + "\r\n").encode("utf-8"))
        return _read_response(sock)


def _run_step(
    *,
    device_ip: str,
    port: int,
    timeout: float,
    attempts: int,
    retry_delay: float,
    command: str,
    expected_token: str,
    step: str,
) -> dict:
    last_error: Exception | None = None
    last_response = ""

    for attempt in range(1, attempts + 1):
        try:
            response = _exchange(device_ip, port, timeout, command)
            last_response = response
            if expected_token in response:
                return {
                    "step": step,
                    "ok": True,
                    "attempt": attempt,
                    "response": response,
                }
            last_error = ProvisioningError(
                f"{step} returned an unexpected response: {response or '<empty>'}"
            )
        except (OSError, TimeoutError) as exc:
            last_error = exc

        if attempt < attempts and retry_delay > 0:
            time.sleep(retry_delay)

    detail = str(last_error) if last_error else (last_response or "no response")
    raise ProvisioningError(f"{step} failed after {attempts} attempts: {detail}")


def provision_device(
    ssid: str,
    password: str,
    server_ip: str,
    device_ip: str = "192.168.1.1",
    port: int = 30300,
    timeout: float = 3.0,
    attempts: int = 3,
    retry_delay: float = 0.8,
) -> dict:
    """Provision an MTTL-W01 while this host can reach its TONLY_TAP setup AP.

    The setup service is short-lived, so each command is sent on its own TCP
    connection. Transport failures and empty/unexpected responses are retried.
    """
    _validate_credentials(ssid, password)
    server_ip = _validate_ipv4(server_ip, "server_ip")
    device_ip = _validate_ipv4(device_ip, "device_ip")

    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    if timeout <= 0:
        raise ValueError("timeout must be greater than 0")
    if attempts < 1 or attempts > 10:
        raise ValueError("attempts must be between 1 and 10")
    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")

    steps = (
        ("server_ip", f"up:ip:{server_ip}", "ip_ok"),
        ("wifi", f"up:connect:{ssid}:{password}", "connect_ok"),
    )

    responses: list[dict] = []
    for step, command, expected in steps:
        responses.append(
            _run_step(
                device_ip=device_ip,
                port=port,
                timeout=timeout,
                attempts=attempts,
                retry_delay=retry_delay,
                command=command,
                expected_token=expected,
                step=step,
            )
        )

    return {
        "ok": True,
        "device_ip": device_ip,
        "server_ip": server_ip,
        "responses": responses,
    }
