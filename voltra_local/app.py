from __future__ import annotations

import os
from pathlib import Path
import signal
import threading

from . import __version__
from .audit import AuditLog
from .automation import AutomationEngine
from .demo_device import run_demo_device
from .discovery import DiscoveryResponder
from .events import EventBus
from .http_api import start_http
from .mqtt_adapter import StandaloneMQTT
from .device_manager import DeviceManager
from .store import ConfigStore
from .tcp_server import MTTLServer
from .telemetry import TelemetryStore


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw else default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw else default


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def main() -> None:
    legacy_bind = os.getenv("VOLTRA_BIND")
    tcp_bind = os.getenv("VOLTRA_TCP_BIND", legacy_bind or "0.0.0.0")
    http_bind = os.getenv("VOLTRA_HTTP_BIND", legacy_bind or "127.0.0.1")
    tcp_port = env_int("VOLTRA_TCP_PORT", 10086)
    http_port = env_int("PORT", env_int("VOLTRA_HTTP_PORT", 8086))
    poll_interval = env_float("VOLTRA_POLL_INTERVAL", 10.0)
    response_timeout = env_float("VOLTRA_RESPONSE_TIMEOUT", 3.0)
    diagnostics_interval = env_float("VOLTRA_DIAGNOSTICS_INTERVAL", 30.0)
    telemetry_interval = env_float("VOLTRA_TELEMETRY_INTERVAL", 60.0)
    discovery_port = env_int("VOLTRA_DISCOVERY_PORT", 10087)
    command_attempts = env_int("VOLTRA_COMMAND_ATTEMPTS", 2)
    confirm_delay = env_float("VOLTRA_COMMAND_CONFIRM_DELAY", 0.15)
    rate_limit = env_int("VOLTRA_RATE_LIMIT_PER_MINUTE", 60)
    cors_origin = os.getenv("VOLTRA_CORS_ORIGIN", "*")
    api_token = os.getenv("VOLTRA_API_TOKEN", "").strip()
    trusted_proxy = os.getenv("VOLTRA_TRUSTED_PROXY", "").strip()
    public_origin = os.getenv("VOLTRA_PUBLIC_ORIGIN", "").strip()
    if api_token and len(api_token) < 32:
        raise ValueError("VOLTRA_API_TOKEN must be at least 32 characters")
    if public_origin and cors_origin == "*":
        cors_origin = public_origin
    demo = env_bool("VOLTRA_DEMO", False)
    data_dir = Path(os.getenv("VOLTRA_DATA_DIR", "data"))
    store = ConfigStore(data_dir / "voltra.json")

    print(f"[APP] Voltra Local Mini Server v{__version__}")
    print(f"[APP] demo={'ON' if demo else 'OFF'}")
    print(f"[APP] data={store.path}")
    print(f"[APP] TCP={tcp_bind}:{tcp_port} HTTP={http_bind}:{http_port}")
    print(f"[APP] API auth={'ON' if api_token else 'OFF'}")
    if public_origin:
        print(f"[APP] public origin={public_origin}")

    event_bus = EventBus()
    audit = AuditLog(data_dir / "audit.jsonl")
    mttl = MTTLServer(
        host=tcp_bind,
        port=tcp_port,
        poll_interval=poll_interval,
        response_timeout=response_timeout,
        diagnostics_interval=diagnostics_interval,
        command_attempts=command_attempts,
        confirm_delay=confirm_delay,
        event_bus=event_bus,
        audit=audit,
        on_device_seen=store.record_strip,
    )
    mttl.start()
    mqtt_adapter = None
    if env_bool("VOLTRA_MQTT_ENABLED"):
        mqtt_adapter = StandaloneMQTT(
            host=os.getenv("VOLTRA_MQTT_HOST", "mosquitto"),
            port=env_int("VOLTRA_MQTT_PORT", 1883),
            username=os.getenv("VOLTRA_MQTT_USERNAME", ""),
            password=os.getenv("VOLTRA_MQTT_PASSWORD", ""),
            prefix=os.getenv("VOLTRA_MQTT_TOPIC_PREFIX", "voltra"),
            on_device_seen=store.record_strip,
            event_bus=event_bus,
        )
        mqtt_adapter.start()
    devices = DeviceManager(mttl, mqtt_adapter)

    if demo:
        threading.Thread(
            target=run_demo_device,
            kwargs={"host": "127.0.0.1", "port": tcp_port},
            daemon=True,
        ).start()
        print("[DEMO] fake MTTL-W01 enabled")

    telemetry = TelemetryStore(data_dir / "telemetry.jsonl", sample_interval=telemetry_interval)
    telemetry.start(devices.list_devices)

    def automation_command(mac: str, outlet: int, on: bool, source: str) -> dict:
        store.require_strip_controllable(mac)
        result = devices.get(mac).set_outlet(outlet, on)
        audit.append("automation", "command_executed", mac=mac, outlet=outlet, on=on, source=source)
        return result

    automation = AutomationEngine(
        data_dir / "automation.json",
        snapshot_provider=devices.list_devices,
        command_executor=automation_command,
        audit=audit,
        event_bus=event_bus,
    )
    automation.start()

    http = start_http(
        devices,
        http_bind,
        http_port,
        store=store,
        cors_origin=cors_origin,
        automation=automation,
        telemetry=telemetry,
        audit=audit,
        event_bus=event_bus,
        rate_limit_per_minute=rate_limit,
        api_token=api_token,
        trusted_proxy=trusted_proxy,
        public_origin=public_origin,
    )
    discovery = DiscoveryResponder(
        port=discovery_port,
        http_port=http_port,
        tcp_port=tcp_port,
        name=os.getenv("VOLTRA_SERVER_NAME", "Voltra Server"),
    )
    discovery.start()
    print(f"[DISCOVERY] UDP 0.0.0.0:{discovery_port}")

    stop = threading.Event()

    def shutdown(*_):
        if stop.is_set():
            return
        stop.set()
        print("[APP] shutting down")
        automation.stop()
        discovery.stop()
        telemetry.stop()
        http.shutdown()
        http.server_close()
        if mqtt_adapter:
            mqtt_adapter.stop()
        mttl.stop()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    stop.wait()


if __name__ == "__main__":
    main()
