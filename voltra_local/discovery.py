from __future__ import annotations

import json
import socket
import threading

from . import __version__


class DiscoveryResponder:
    """Small LAN UDP responder for Voltra-X server discovery."""

    MAGIC = b"VOLTRAX_DISCOVER"

    def __init__(
        self,
        *,
        port: int = 10087,
        http_port: int = 8086,
        tcp_port: int = 10086,
        name: str = "Voltra Server",
    ) -> None:
        self.port = int(port)
        self.http_port = int(http_port)
        self.tcp_port = int(tcp_port)
        self.name = str(name)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._sock: socket.socket | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="voltra-discovery")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        sock = self._sock
        if sock:
            try:
                sock.close()
            except OSError:
                pass

    def _loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock = sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        sock.bind(("0.0.0.0", self.port))
        while not self._stop.is_set():
            try:
                payload, address = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            if payload.strip() != self.MAGIC:
                continue
            response = json.dumps(
                {
                    "service": "voltra-x",
                    "name": self.name,
                    "version": __version__,
                    "http_port": self.http_port,
                    "tcp_port": self.tcp_port,
                    "discovery_port": self.port,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            try:
                sock.sendto(response, address)
            except OSError:
                pass
