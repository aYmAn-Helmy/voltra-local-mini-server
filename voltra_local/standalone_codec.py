"""Codec for standalone MTTL-W01 v2.1.x device-owned configuration.

Reverse engineered from the public standalone firmware settings.c and
scheduler.js. This intentionally does not encode Wi-Fi credentials read from
/api/config: the firmware preserves Wi-Fi settings on config updates.
"""
from __future__ import annotations

import hashlib
import json
import struct

RULES = 8


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer from {low} to {high}")
    return value


def decode_schedule(hex_value: str) -> dict:
    if not isinstance(hex_value, str) or len(hex_value) != 100:
        raise ValueError("schedule must contain exactly 50 bytes")
    try:
        raw = bytes.fromhex(hex_value)
    except ValueError as exc:
        raise ValueError("invalid schedule hex") from exc
    timezone = struct.unpack_from("<h", raw)[0]
    rules = []
    for i in range(RULES):
        minute, mode, day, channel, on = struct.unpack_from("<HBBBB", raw, 2 + i * 6)
        rules.append({"minute": minute, "mode": mode, "day": day, "channel": channel, "on": on})
    result = {"timezone": timezone, "rules": rules}
    if encode_schedule(result) != raw:
        raise ValueError("invalid schedule")
    return result


def encode_schedule(schedule: dict) -> bytes:
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be an object")
    tz = _integer(schedule.get("timezone"), -720, 840, "timezone")
    if tz % 15:
        raise ValueError("timezone must be a 15-minute multiple")
    rules = schedule.get("rules")
    if not isinstance(rules, list) or len(rules) != RULES:
        raise ValueError("schedule must have eight rule slots")
    out = bytearray(struct.pack("<h", tz))
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError("rule must be an object")
        minute = _integer(rule.get("minute"), 0, 1439, "minute")
        mode = _integer(rule.get("mode"), 0, 255, "mode")
        day = _integer(rule.get("day"), 0, 127, "day")
        channel = _integer(rule.get("channel"), 0, 4, "channel")
        on = _integer(rule.get("on"), 0, 1, "on")
        repeat = mode & 127
        if repeat > 4:
            raise ValueError("unknown schedule mode")
        if repeat == 0 and (mode or minute or day or channel or on):
            raise ValueError("empty schedule rule must be cleared")
        if repeat == 2 and day == 0:
            raise ValueError("weekly rule needs at least one day")
        if repeat == 3 and not 1 <= day <= 31:
            raise ValueError("invalid monthly day")
        if repeat in (1, 4) and day:
            raise ValueError("daily/last-day rule cannot specify days")
        out.extend(struct.pack("<HBBBB", minute, mode, day, channel, on))
    return bytes(out)


def validate_timer_conflict(schedule: dict, timers: list[int]):
    if not isinstance(timers, list) or len(timers) != 4:
        raise ValueError("timer_minutes must be an array of four integers")
    for value in timers:
        _integer(value, 0, 1440, "timer")
    for rule in schedule["rules"]:
        if rule["mode"] & 127:
            for index, minutes in enumerate(timers):
                if minutes and rule["channel"] in (index, 4):
                    raise ValueError(f"channel {index + 1} has both a scheduler rule and a timer")


def configuration_revision(config: dict) -> str:
    """Optimistic concurrency token, excludes volatile firmware state."""
    names = ("device", "channels", "language", "broker", "port", "user", "topic",
             "enabled", "protection", "schedule_hex", "button_lock", "timer_minutes")
    value = {key: config.get(key) for key in names}
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def pack_configuration(config: dict, mqtt_password: str = "") -> bytes:
    if not isinstance(config, dict):
        raise ValueError("configuration must be object")
    language = _integer(config.get("language"), 0, 1, "language")
    enabled = config.get("enabled")
    if type(enabled) is not bool:
        raise ValueError("enabled must be boolean")
    port = _integer(config.get("port"), 1, 65535, "port")
    channels = config.get("channels")
    if not isinstance(channels, list) or len(channels) != 4:
        raise ValueError("channels must be four names")
    fields = [
        config.get("device"), *channels,
        "", "",  # Firmware copies current SSID/Wi-Fi password before flash write.
        config.get("broker"), config.get("user"), mqtt_password, config.get("topic")
    ]
    limits = [64, 64, 64, 64, 64, 32, 64, 253, 64, 64, 64]
    encoded = bytearray(struct.pack("<BBBH", 7, language, 1 if enabled else 0, port))
    for name, limit, value in zip(
        ["device", "ch1", "ch2", "ch3", "ch4", "ssid", "wifi", "broker", "user", "password", "topic"],
        limits, fields
    ):
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        raw = value.encode("utf-8")
        if len(raw) > limit or (name in ("device", "ch1", "ch2", "ch3", "ch4") and not raw):
            raise ValueError(f"invalid {name} length")
        if b"\x00" in raw or any(byte < 32 for byte in raw):
            raise ValueError(f"invalid {name} characters")
        encoded.extend(bytes([len(raw)]))
        encoded.extend(raw)
    protection = config.get("protection")
    if not isinstance(protection, dict):
        raise ValueError("protection must be an object")
    encoded.extend(struct.pack(
        "<BHHH",
        _integer(protection.get("enabled"), 0, 7, "protection.enabled"),
        _integer(protection.get("temperature"), 50, 90, "protection.temperature"),
        _integer(protection.get("current"), 1000, 16000, "protection.current"),
        _integer(protection.get("power"), 100, 3000, "protection.power")
    ))
    schedule = decode_schedule(config.get("schedule_hex", ""))
    timers = config.get("timer_minutes")
    validate_timer_conflict(schedule, timers)
    encoded.extend(encode_schedule(schedule))
    encoded.append(_integer(config.get("button_lock"), 0, 15, "button_lock"))
    for value in timers:
        encoded.extend(struct.pack("<H", value))
    if len(encoded) > 1024:
        raise ValueError("firmware settings exceed 1024-byte capacity")
    return bytes(encoded)


ALLOWED_PATCH = {"device", "channels", "language", "broker", "port", "user", "topic",
                 "enabled", "protection", "schedule", "button_lock", "timer_minutes", "mqtt_password"}


def merge_patch(current: dict, patch: dict) -> tuple[dict, str, bool]:
    if not isinstance(patch, dict) or not patch or set(patch) - ALLOWED_PATCH:
        raise ValueError("unsupported or empty config patch")
    candidate = {key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
                 for key, value in current.items()}
    password = patch.get("mqtt_password", "")
    if not isinstance(password, str):
        raise ValueError("mqtt_password must be text")
    for key, value in patch.items():
        if key == "schedule":
            candidate["schedule_hex"] = encode_schedule(value).hex()
        elif key != "mqtt_password":
            candidate[key] = value
    # Validate before any contact with the device.
    pack_configuration(candidate, password)
    return candidate, password, "mqtt_password" not in patch
