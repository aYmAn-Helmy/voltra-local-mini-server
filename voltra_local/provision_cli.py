from __future__ import annotations

import argparse
from getpass import getpass
import json

from .provisioner import ProvisioningError, provision_device


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Provision an MTTL-W01 from a computer connected to its TONLY_TAP setup Wi-Fi."
    )
    parser.add_argument("--server-ip", required=True, help="LAN IP of the Voltra/CasaOS host")
    parser.add_argument("--ssid", required=True, help="2.4 GHz Wi-Fi SSID the strip should join")
    parser.add_argument("--password", help="Wi-Fi password; omitted = prompt securely")
    parser.add_argument("--device-ip", default="192.168.1.1", help="strip setup IP")
    parser.add_argument("--port", type=int, default=30300, help="strip setup TCP port")
    args = parser.parse_args()

    password = args.password
    if password is None:
        password = getpass("Wi-Fi password: ")

    try:
        result = provision_device(
            ssid=args.ssid,
            password=password,
            server_ip=args.server_ip,
            device_ip=args.device_ip,
            port=args.port,
        )
    except (ValueError, ProvisioningError, OSError, TimeoutError) as exc:
        print(f"Provisioning failed: {exc}")
        return 1

    safe = {
        "ok": result.get("ok"),
        "device_ip": result.get("device_ip"),
        "server_ip": result.get("server_ip"),
        "steps": [
            {
                "step": item.get("step"),
                "ok": item.get("ok"),
                "attempt": item.get("attempt"),
                "response": item.get("response"),
            }
            for item in result.get("responses", [])
        ],
    }
    print(json.dumps(safe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
