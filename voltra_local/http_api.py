from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading
from urllib.parse import unquote, urlsplit

from .tcp_server import MTTLServer

_DEVICE_RE = re.compile(r"^/api/devices/([^/]+)$")
_REFRESH_RE = re.compile(r"^/api/devices/([^/]+)/refresh$")
_STATE_RE = re.compile(r"^/api/devices/([^/]+)/outlets/([1-4])/state$")
_ACTION_RE = re.compile(r"^/api/devices/([^/]+)/outlets/([1-4])/(on|off)$")

DASHBOARD = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Voltra Local Mini Server</title>
<style>
body{font-family:system-ui,Arial,sans-serif;margin:0;background:#101218;color:#eef1f6}.wrap{max-width:980px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center}.badge{padding:6px 10px;border:1px solid #3a4050;border-radius:999px}.card{background:#181c24;border:1px solid #2b3140;border-radius:16px;padding:18px;margin:16px 0}.row{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap}.outlets{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:14px}.outlet{background:#11151c;border:1px solid #303748;border-radius:12px;padding:14px}button{border:0;border-radius:9px;padding:9px 12px;margin:3px;cursor:pointer}button.on{background:#dcebdc}button.off{background:#ead9d9}.muted{color:#9aa4b6;font-size:.9rem}.state{font-weight:700}
</style></head><body><div class="wrap"><div class="top"><div><h1>Voltra Local Mini Server</h1><div class="muted">MTTL-W01 local control</div></div><div class="badge" id="health">...</div></div><div id="devices"></div></div>
<script>
async function api(path,opt={}){const r=await fetch(path,{headers:{'content-type':'application/json'},...opt});const t=await r.text();let d={};try{d=t?JSON.parse(t):{}}catch{d={raw:t}}if(!r.ok)throw new Error(d.error||r.statusText);return d}
async function setState(mac,n,on){try{await api(`/api/devices/${mac}/outlets/${n}/state`,{method:'POST',body:JSON.stringify({on})});await refresh()}catch(e){alert(e.message)}}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function refresh(){try{const data=await api('/api/devices');health.textContent=`${data.devices.length} device(s)`;devices.innerHTML=data.devices.length?'':'<div class="card">No MTTL-W01 connected yet.</div>';for(const d of data.devices){let html=`<div class="card"><div class="row"><div><h2>${esc(d.mac)}</h2><div class="muted">${esc(d.model)} · FW ${esc(d.firmware_version)} · ${esc(d.remote_address)}</div></div><div class="state">${d.online?'ONLINE':'OFFLINE'}</div></div><div class="outlets">`;for(let n=1;n<=4;n++){const o=(d.outlets||[]).find(x=>x.channel===n);html+=`<div class="outlet"><div class="row"><strong>Outlet ${n}</strong><span>${o?(o.relay?'ON':'OFF'):'?'}</span></div><div><button class="on" onclick="setState('${d.mac}',${n},true)">ON</button><button class="off" onclick="setState('${d.mac}',${n},false)">OFF</button></div>${o?`<div class="muted">${o.power_w.toFixed(2)} W · ${o.energy_wh} Wh · ${o.temperature_c} °C</div>`:''}</div>`}html+='</div></div>';devices.innerHTML+=html}}catch(e){health.textContent='API ERROR'}}
refresh();setInterval(refresh,3000)
</script></body></html>'''


class APIHandler(BaseHTTPRequestHandler):
    server_version = "VoltraLocal/0.1"

    @property
    def app(self) -> "VoltraHTTPServer":
        return self.server

    def do_OPTIONS(self):
        self.send_response(204)
        self._common_headers()
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            if path == "/":
                return self._send_text(200, DASHBOARD, "text/html; charset=utf-8")
            if path == "/health":
                return self._json(200, {"ok": True})
            if path == "/api/devices":
                self._require_auth()
                return self._json(200, {"devices": self.app.mttl.list_devices()})
            match = _DEVICE_RE.match(path)
            if match:
                self._require_auth()
                return self._json(200, self.app.mttl.get(unquote(match.group(1))).snapshot())
            return self._json(404, {"error": "not found"})
        except KeyError as exc:
            return self._json(404, {"error": str(exc)})
        except PermissionError as exc:
            return self._json(401, {"error": str(exc)})
        except Exception as exc:
            return self._json(500, {"error": str(exc)})

    def do_POST(self):
        try:
            path = urlsplit(self.path).path
            self._require_auth()
            match = _REFRESH_RE.match(path)
            if match:
                return self._json(200, self.app.mttl.get(unquote(match.group(1))).query_info())
            match = _STATE_RE.match(path)
            if match:
                body = self._read_json()
                if not isinstance(body.get("on"), bool):
                    return self._json(400, {"error": "JSON field 'on' must be boolean"})
                session = self.app.mttl.get(unquote(match.group(1)))
                return self._json(200, session.set_outlet(int(match.group(2)), body["on"]))
            match = _ACTION_RE.match(path)
            if match:
                session = self.app.mttl.get(unquote(match.group(1)))
                return self._json(200, session.set_outlet(int(match.group(2)), match.group(3) == "on"))
            return self._json(404, {"error": "not found"})
        except KeyError as exc:
            return self._json(404, {"error": str(exc)})
        except TimeoutError as exc:
            return self._json(504, {"error": str(exc)})
        except PermissionError as exc:
            return self._json(401, {"error": str(exc)})
        except Exception as exc:
            return self._json(500, {"error": str(exc)})

    def _require_auth(self):
        token = self.app.api_token
        if not token:
            return
        if self.headers.get("Authorization") != f"Bearer {token}":
            raise PermissionError("invalid or missing API token")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1024 * 1024:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object expected")
        return value

    def _json(self, status: int, value: object):
        payload = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self._common_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, status: int, value: str, content_type: str):
        payload = value.encode("utf-8")
        self.send_response(status)
        self._common_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _common_headers(self):
        self.send_header("Access-Control-Allow-Origin", self.app.cors_origin)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")

    def log_message(self, fmt, *args):
        print("[HTTP] " + (fmt % args))


class VoltraHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, mttl: MTTLServer, api_token: str = "", cors_origin: str = "*"):
        self.mttl = mttl
        self.api_token = api_token
        self.cors_origin = cors_origin
        super().__init__(address, APIHandler)


def start_http(mttl: MTTLServer, host: str, port: int, api_token: str = "", cors_origin: str = "*"):
    server = VoltraHTTPServer((host, port), mttl, api_token=api_token, cors_origin=cors_origin)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HTTP] dashboard/API listening on http://{host}:{port}")
    return server
