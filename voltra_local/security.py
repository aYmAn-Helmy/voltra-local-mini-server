from __future__ import annotations

import hmac
import ipaddress
from urllib.parse import urlsplit
from typing import Iterable


class RemoteAccessSecurity:
    """Small, dependency-free HTTP security policy for Voltra remote access."""

    def __init__(self, api_token: str = "", trusted_proxies: str = "") -> None:
        self._token = str(api_token or "").strip()
        self._trusted = tuple(self._parse_networks(trusted_proxies))

    @property
    def enabled(self) -> bool:
        return bool(self._token)

    @staticmethod
    def _parse_networks(value: str) -> Iterable[ipaddress._BaseNetwork]:
        for raw in str(value or "").split(","):
            item = raw.strip()
            if not item:
                continue
            try:
                yield ipaddress.ip_network(item, strict=False)
            except ValueError as exc:
                raise ValueError(f"invalid trusted proxy network: {item}") from exc

    def is_trusted_proxy(self, peer_ip: str) -> bool:
        try:
            address = ipaddress.ip_address(str(peer_ip))
        except ValueError:
            return False
        return any(address in network for network in self._trusted)

    def authorized(self, authorization: str | None) -> bool:
        if not self.enabled:
            return True
        header = str(authorization or "")
        if not header.startswith("Bearer "):
            return False
        candidate = header[7:]
        return bool(candidate) and hmac.compare_digest(candidate, self._token)

    def client_ip(self, peer_ip: str, forwarded_for: str | None) -> str:
        if not self.is_trusted_proxy(peer_ip):
            return str(peer_ip)
        first = str(forwarded_for or "").split(",", 1)[0].strip()
        if not first:
            return str(peer_ip)
        try:
            return str(ipaddress.ip_address(first))
        except ValueError:
            return str(peer_ip)

    @staticmethod
    def is_local_peer(peer_ip: str) -> bool:
        """Allow loopback, RFC1918 LAN and IPv6 unique-local peers."""
        try:
            address = ipaddress.ip_address(str(peer_ip))
        except ValueError:
            return False
        if address.version == 4:
            networks = (
                ipaddress.ip_network("127.0.0.0/8"),
                ipaddress.ip_network("10.0.0.0/8"),
                ipaddress.ip_network("172.16.0.0/12"),
                ipaddress.ip_network("192.168.0.0/16"),
            )
            return any(address in network for network in networks)
        return address.is_loopback or address in ipaddress.ip_network("fc00::/7")

    @staticmethod
    def is_local_host(host_header: str | None) -> bool:
        """Reject public Host names in no-token LAN installations (DNS rebinding guard)."""
        try:
            host = urlsplit("http://" + str(host_header or "")).hostname
        except ValueError:
            return False
        if not host:
            return False
        if host == "localhost" or host.endswith((".local", ".lan", ".home.arpa")):
            return True
        try:
            return RemoteAccessSecurity.is_local_peer(host)
        except ValueError:
            return False

    @staticmethod
    def same_origin_host(host_header: str | None, origin: str | None) -> bool:
        """Disallow cross-origin browser writes to a tokenless server."""
        if not origin:
            return True
        try:
            origin_parts = urlsplit(origin)
            host_parts = urlsplit("http://" + str(host_header or ""))
        except ValueError:
            return False
        return (
            origin_parts.scheme in {"http", "https"}
            and origin_parts.hostname == host_parts.hostname
            and origin_parts.port == host_parts.port
        )

    def request_scheme(self, peer_ip: str, forwarded_proto: str | None) -> str:
        if self.is_trusted_proxy(peer_ip):
            value = str(forwarded_proto or "").split(",", 1)[0].strip().lower()
            if value in {"http", "https"}:
                return value
        return "http"
