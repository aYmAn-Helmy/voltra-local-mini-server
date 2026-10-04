from __future__ import annotations


def health_from_snapshot(snapshot: dict | None) -> dict:
    if not snapshot or not snapshot.get("online", True):
        return {"score": 0, "status": "offline", "reasons": ["device_offline"]}

    score = 100
    reasons: list[str] = []

    rssi = snapshot.get("wifi_rssi_dbm")
    if isinstance(rssi, (int, float)):
        if rssi <= -80:
            score -= 40
            reasons.append("wifi_very_weak")
        elif rssi <= -70:
            score -= 25
            reasons.append("wifi_weak")
        elif rssi <= -62:
            score -= 10
            reasons.append("wifi_fair")

    voltage = snapshot.get("voltage_v")
    if isinstance(voltage, (int, float)):
        if voltage < 190 or voltage > 255:
            score -= 40
            reasons.append("voltage_critical")
        elif voltage < 205 or voltage > 245:
            score -= 20
            reasons.append("voltage_warning")

    metrics = snapshot.get("metrics") or {}
    commands = int(metrics.get("command_count") or 0)
    failures = int(metrics.get("command_failures") or 0)
    if commands >= 3 and failures:
        failure_rate = failures / max(commands, 1)
        if failure_rate >= 0.30:
            score -= 30
            reasons.append("command_failures_high")
        elif failure_rate >= 0.10:
            score -= 15
            reasons.append("command_failures")

    disconnects = int(metrics.get("disconnects") or 0)
    if disconnects >= 10:
        score -= 20
        reasons.append("frequent_disconnects")
    elif disconnects >= 3:
        score -= 8
        reasons.append("some_disconnects")

    score = max(0, min(100, score))
    if score >= 85:
        status = "healthy"
    elif score >= 65:
        status = "warning"
    elif score >= 35:
        status = "unstable"
    else:
        status = "critical"
    return {"score": score, "status": status, "reasons": reasons}
