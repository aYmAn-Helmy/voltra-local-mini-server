"""Unify original TCP devices with standalone MQTT devices."""


class DeviceManager:
    def __init__(self, tcp, mqtt=None):
        self.tcp, self.mqtt = tcp, mqtt

    def list_devices(self):
        result = {d["mac"]: d for d in self.tcp.list_devices()}
        if self.mqtt:
            for item in self.mqtt.list_devices():
                result[item["mac"]] = item
        return list(result.values())

    def get(self, mac):
        mac = mac.replace(":", "").replace("-", "").upper()
        if self.mqtt and self.mqtt.has_device(mac):
            current = self.mqtt.snapshot(mac)
            if current and current["online"]:
                return self.mqtt.get(mac)
        return self.tcp.get(mac)
