from __future__ import annotations

import os
import signal
import threading

from .http_api import start_http
from .tcp_server import MTTLServer
from .demo_device import run_demo_device


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def main() -> None:
    bind = os.getenv("VOLTRA_BIND", "0.0.0.0")
    tcp_port = env_int("VOLTRA_TCP_PORT", 10086)
    http_port = env_int("PORT", env_int("VOLTRA_HTTP_PORT", 8086))
    poll_interval = env_float("VOLTRA_POLL_INTERVAL", 10.0)
    response_timeout = env_float("VOLTRA_RESPONSE_TIMEOUT", 3.0)
    api_token = os.getenv("VOLTRA_API_TOKEN", "")
    cors_origin = os.getenv("VOLTRA_CORS_ORIGIN", "*")

    mttl = MTTLServer(
        host=bind,
        port=tcp_port,
        poll_interval=poll_interval,
        response_timeout=response_timeout,
    )
    mttl.start()

    if os.getenv("VOLTRA_DEMO", "0").lower() in {"1", "true", "yes", "on"}:
        threading.Thread(
            target=run_demo_device,
            kwargs={"host": "127.0.0.1", "port": tcp_port},
            daemon=True,
        ).start()
        print("[DEMO] fake MTTL-W01 enabled")

    http = start_http(mttl, bind, http_port, api_token=api_token, cors_origin=cors_origin)

    stop = threading.Event()

    def shutdown(*_):
        if stop.is_set():
            return
        stop.set()
        print("[APP] shutting down")
        http.shutdown()
        http.server_close()
        mttl.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    stop.wait()


if __name__ == "__main__":
    main()
