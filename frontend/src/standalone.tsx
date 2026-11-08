import { useCallback, useEffect, useState } from "react";
import { Activity, CalendarClock, Clock3, Cpu, LockKeyhole, RefreshCw, Router, ShieldCheck, Wifi, Zap } from "lucide-react";
import { api } from "./api";

type Rule = { minute: number; mode: number; day: number; channel: number; on: number };
type Schedule = { timezone: number; rules: Rule[] };
type Protection = { enabled: number; temperature: number; current: number; power: number };
type Settings = {
  device: string; channels: string[]; language: number; broker: string; port: number;
  user: string; topic: string; enabled: boolean; mqtt_password_set: boolean;
  protection: Protection; button_lock: number; timer_minutes: number[];
  persistent: boolean; revision: string; schedule: Schedule;
};
type Device = {
  name: string; channels: Array<{ name: string; on: boolean; locked: boolean; power_mw: number | null;
    meter_wh: number | null; current_ma: number | null; temp_dc: number | null }>;
  power_mw: number | null; meter_wh: number | null; voltage_dv: number | null;
  current_ma: number | null; hardware_ready: boolean; timer_running: number; timer_end: number[];
  protection?: { reason: number; error: number }; mqtt_state: number;
};
type Status = { mac: string; state: number; ip: number; uptime_ms: number; rssi: number | null;
  unix_ms: number | null; storage: number[]; ssid_hex: string; hardware_ready: boolean };
type Details = { device: Device; status: Status; config: Settings;
  energy: Record<string, number> | null; memory: Record<string, number> | null;
  firmware: Record<string, unknown> | null };
type Tab = "power" | "wifi" | "mqtt" | "protection" | "scheduler" | "timer" | "firmware" | "logs";
type LogEvent = Record<string, unknown>;

const tabs: Array<{ id: Tab; name: string }> = [
  { id: "power", name: "Power strip" }, { id: "wifi", name: "Wi-Fi setup" },
  { id: "mqtt", name: "HA · MQTT" }, { id: "protection", name: "Protection" },
  { id: "scheduler", name: "Scheduler" }, { id: "timer", name: "Timer" },
  { id: "firmware", name: "Firmware" }, { id: "logs", name: "Logs" },
];
const emptyRule = (): Rule => ({ minute: 0, mode: 0, day: 0, channel: 0, on: 0 });
const n = (value: number | null | undefined, divisor: number, digits: number) =>
  value == null ? "—" : (value / divisor).toFixed(digits);
const ssidText = (hex: string) => {
  try {
    if (hex.length % 2 || !/^[0-9a-f]*$/i.test(hex)) return "";
    return new TextDecoder().decode(Uint8Array.from(hex.match(/.{2}/g) || [], x => parseInt(x, 16)));
  } catch { return ""; }
};
const bit = (mask: number, index: number, enabled: boolean) =>
  enabled ? mask | (1 << index) : mask & ~(1 << index);

export function StandaloneView({ mac, name, onRefresh, notify }: {
  mac: string; name: string; onRefresh: () => Promise<void>;
  notify: (message: string, error?: boolean) => void;
}) {
  const [tab, setTab] = useState<Tab>("power");
  const [details, setDetails] = useState<Details | null>(null);
  const [live, setLive] = useState<{ device: Device; status: Status } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyRelay, setBusyRelay] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [names, setNames] = useState<string[]>([]);
  const [deviceName, setDeviceName] = useState("");
  const [deviceLanguage, setDeviceLanguage] = useState(1);
  const [locks, setLocks] = useState(0);
  const [mqtt, setMqtt] = useState({ broker: "", port: 1883, user: "", topic: "mttl", enabled: false, password: "" });
  const [protection, setProtection] = useState<Protection>({ enabled: 7, temperature: 90, current: 16000, power: 3000 });
  const [schedule, setSchedule] = useState<Schedule>({ timezone: 120, rules: Array.from({ length: 8 }, emptyRule) });
  const [timers, setTimers] = useState<number[]>([0, 0, 0, 0]);
  const [scans, setScans] = useState<Array<{ ssid_hex: string; rssi: number; security: number }>>([]);
  const [wifi, setWifi] = useState({ ssid: "", password: "" });
  const [firmware, setFirmware] = useState<File | null>(null);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [legacySchedules, setLegacySchedules] = useState(0);

  const reload = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const data = await api.nativeDetails(mac) as Details;
      setDetails(data); setLive({ device: data.device, status: data.status });
      const config = data.config;
      setNames([...config.channels]); setDeviceName(config.device);
      setDeviceLanguage(config.language);
      setLocks(config.button_lock); setProtection({ ...config.protection });
      setSchedule({ timezone: config.schedule.timezone, rules: config.schedule.rules.map(r => ({ ...r })) });
      setTimers([...config.timer_minutes]);
      setMqtt({ broker: config.broker, port: config.port, user: config.user,
        topic: config.topic, enabled: config.enabled, password: "" });
      await onRefresh();
    } catch (exc) { setError(exc instanceof Error ? exc.message : String(exc)); }
    finally { setLoading(false); }
  }, [mac, onRefresh]);

  useEffect(() => { void reload(); }, [mac]);
  useEffect(() => {
    void api.automation().then(snapshot => {
      const schedules = Object.values(snapshot.schedules);
      setLegacySchedules(schedules.filter(item => item.mac === mac && item.enabled !== false).length);
    }).catch(() => setLegacySchedules(0));
  }, [mac]); // Do not reload a dirty form on routine overview refresh.
  useEffect(() => {
    if (tab !== "power") return;
    let active = true;
    const poll = async () => {
      try {
        const result = await api.nativeLive(mac) as { device: Device; status: Status };
        if (active) setLive(result);
      } catch { /* Keep last confirmed state; server shows offline via overview. */ }
    };
    const timer = window.setInterval(() => void poll(), 2400);
    return () => { active = false; window.clearInterval(timer); };
  }, [mac, tab]);

  useEffect(() => {
    if (tab !== "logs") return;
    void api.nativeLogs(mac).then((result: { events: LogEvent[] }) => setLogs(result.events || []))
      .catch(exc => setError(String(exc)));
  }, [mac, tab]);

  async function save(patch: Record<string, unknown>, success: string) {
    if (!details || busy) return;
    setBusy(true);
    try {
      await api.nativeConfig(mac, { ...patch, revision: details.config.revision });
      notify(success);
      await reload();
    } catch (exc) { notify(exc instanceof Error ? exc.message : String(exc), true); }
    finally { setBusy(false); }
  }

  async function toggle(channel: number, on: boolean) {
    if (busyRelay !== null) return;
    setBusyRelay(channel);
    setLive(old => old ? { ...old,
      device: { ...old.device,
        channels: old.device.channels.map((item, index) =>
          channel === 4 || index === channel ? { ...item, on } : item) } } : old);
    try {
      await api.nativeControl(mac, channel, on);
      const fresh = await api.nativeLive(mac) as { device: Device; status: Status };
      setLive(fresh);
      await onRefresh();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : String(exc), true);
      try { setLive(await api.nativeLive(mac) as { device: Device; status: Status }); } catch {}
    } finally { setBusyRelay(null); }
  }

  const current = live?.device || details?.device;
  const status = live?.status || details?.status;
  const config = details?.config;
  const valid = status?.state === 5 && current?.hardware_ready === true;
  const editable = !busy && !loading && Boolean(config);

  function updateRule(index: number, change: Partial<Rule>) {
    setSchedule(prev => ({ ...prev, rules: prev.rules.map((r, i) => i === index ? { ...r, ...change } : r) }));
  }
  const activeRules = schedule.rules.filter(r => (r.mode & 127) !== 0);
  const addRule = () => {
    const slot = schedule.rules.findIndex(r => r.mode === 0);
    if (slot >= 0) updateRule(slot, { minute: 600, mode: 129, day: 0, channel: 4, on: 1 });
  };
  const conflicting = schedule.rules.some(r => (r.mode & 127) && timers.some((t, i) => t > 0 && (r.channel === i || r.channel === 4)));

  return <div className="view-stack native-console">
    <div className="native-toolbar">
      <div>
        <span className="eyebrow">DEVICE-OWNED CONTROL · HTTP LOCAL</span>
        <h2>{name}</h2>
        <small>{mac} · {status?.state === 5 ? "Connected" : "Disconnected"} · Firmware v2.1.x</small>
      </div>
      <button className="button secondary" disabled={busy || loading} onClick={() => void reload()}>
        <RefreshCw size={16} /> Refresh
      </button>
    </div>
    <div className="native-tabs" role="tablist" aria-label="Native firmware services">
      {tabs.map(item => <button role="tab" key={item.id} className={tab === item.id ? "active" : ""}
        aria-selected={tab === item.id} onClick={() => setTab(item.id)}>{item.name}</button>)}
    </div>
    {error && <div className="native-alert" role="alert">{error}</div>}
    {loading && !details && <div className="surface-card">Loading native firmware status…</div>}
    {details && <>
      {tab === "power" && <section className="surface-card">
        <div className="card-title-row"><div><span className="eyebrow">DIRECT RELAY CONTROL</span><h3>Power strip</h3></div><Zap size={20} /></div>
        <p className="card-copy">Commands use the strip's own HTTP API. Changes are confirmed against actual firmware state. An accepted command is not physical contact feedback.</p>
        <div className="native-metrics">
          <div><small>Total power</small><strong>{n(current?.power_mw, 1000, 2)} W</strong></div>
          <div><small>Meter</small><strong>{n(current?.meter_wh, 1000, 3)} kWh</strong></div>
          <div><small>Voltage</small><strong>{n(current?.voltage_dv, 10, 1)} V</strong></div>
          <div><small>Current</small><strong>{n(current?.current_ma, 1000, 3)} A</strong></div>
        </div>
        <div className="native-power-grid">
          {current?.channels.map((item, index) => <button type="button" key={index}
            disabled={!valid || busyRelay !== null}
            className={item.on ? "native-switch on" : "native-switch"}
            onClick={() => void toggle(index, !item.on)}>
            <strong>{item.name || `SW ${index + 1}`}</strong>
            <span>{item.on ? "ON" : "OFF"}</span>
            <small>{n(item.power_mw, 1000, 2)} W · {n(item.temp_dc, 10, 1)} °C</small>
          </button>)}
        </div>
        <div className="two-buttons">
          <button className="button soft-green" disabled={!valid || busyRelay !== null} onClick={() => void toggle(4, true)}>ALL ON</button>
          <button className="button secondary" disabled={!valid || busyRelay !== null} onClick={() => void toggle(4, false)}>ALL OFF</button>
        </div>
        <div className="native-form">
          <h3>Device names and physical-button lock</h3>
          <label><span>Strip name</span><input value={deviceName} onChange={e => setDeviceName(e.target.value)} /></label>
          <label><span>Firmware interface language</span>
            <select value={deviceLanguage} onChange={e => setDeviceLanguage(Number(e.target.value))}>
              <option value={1}>English</option><option value={0}>Korean</option>
            </select>
          </label>
          <div className="native-grid">
            {names.map((channel, i) => <label key={i}><span>Outlet {i + 1}</span><input value={channel}
              onChange={e => setNames(old => old.map((s, j) => i === j ? e.target.value : s))} /></label>)}
          </div>
          <div className="native-grid">
            {names.map((_, i) => <label key={i} className="native-checkbox"><input type="checkbox"
              checked={Boolean(locks & (1 << i))} onChange={e => setLocks(old => bit(old, i, e.target.checked))} />
              <span>Lock physical switch {i + 1}</span></label>)}
          </div>
          <button className="button primary" disabled={!editable} onClick={() => void save({ device: deviceName, channels: names,
            button_lock: locks, language: deviceLanguage }, "Device names, language and physical-button locks saved in flash.")}>
            Save to device
          </button>
        </div>
        <p className="card-copy">Last safety trip: {current?.protection?.reason ?? 0} · Sensor errors: {current?.protection?.error ?? 0} · Hardware ready: {String(valid)}</p>
      </section>}
      {tab === "wifi" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">LOCAL NETWORK</span><h3>Wi-Fi setup</h3></div><Wifi size={20}/></div>
        <p className="card-copy">Changing Wi-Fi may move the device to another IP. Pair it again from Add strip after the change. Current SSID: {ssidText(status?.ssid_hex || "") || "—"}</p>
        <button className="button secondary" disabled={busy} onClick={async () => {
          try {
            setBusy(true);
            await api.nativeScan(mac, true);
            let answer = await api.nativeScan(mac, false);
            for (let i = 0; i < 8 && answer.pending; i++) {
              await new Promise(resolve => window.setTimeout(resolve, 550));
              answer = await api.nativeScan(mac, false);
            }
            setScans(answer.networks || []);
          } catch (exc) { notify(String(exc), true); } finally { setBusy(false); }
        }}><Wifi size={16}/> Scan 2.4 GHz networks</button>
        {scans.length > 0 && <select value={wifi.ssid} onChange={e => setWifi(old => ({ ...old, ssid: e.target.value }))}>
          <option value="">Select network</option>
          {scans.map((item, i) => <option key={i} value={ssidText(item.ssid_hex)}>
            {ssidText(item.ssid_hex)} ({item.rssi} dBm)
          </option>)}
        </select>}
        <label><span>Wi-Fi SSID</span><input value={wifi.ssid} onChange={e => setWifi(old => ({ ...old, ssid: e.target.value }))}/></label>
        <label><span>Wi-Fi password</span><input type="password" autoComplete="new-password" value={wifi.password}
          onChange={e => setWifi(old => ({ ...old, password: e.target.value }))}/></label>
        <button className="button primary" disabled={busy || !wifi.ssid} onClick={async () => {
          if (!window.confirm("Changing Wi-Fi can disconnect this strip. Continue?")) return;
          setBusy(true);
          try { await api.nativeWifi(mac, wifi.ssid, wifi.password); setWifi(old => ({ ...old, password: "" }));
            notify("Wi-Fi reconnect requested. Re-pair the strip if its IP changes.");
          } catch (exc) { notify(String(exc), true); } finally { setBusy(false); }
        }}>Connect using this Wi-Fi</button>
      </section>}
      {tab === "mqtt" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">HOME ASSISTANT / MQTT</span><h3>MQTT configuration</h3></div><Router size={20}/></div>
        <p className="card-copy">MQTT remains optional. Direct controls and schedules work over HTTP with no MQTT Broker.</p>
        <label className="native-checkbox"><input type="checkbox" checked={mqtt.enabled} onChange={e => setMqtt(old => ({ ...old, enabled: e.target.checked }))}/> Enable MQTT</label>
        <div className="native-grid">
          <label><span>Broker IPv4</span><input value={mqtt.broker} onChange={e => setMqtt(old => ({ ...old, broker: e.target.value }))}/></label>
          <label><span>Port</span><input type="number" min={1} max={65535} value={mqtt.port} onChange={e => setMqtt(old => ({ ...old, port: Number(e.target.value) }))}/></label>
          <label><span>Username</span><input value={mqtt.user} onChange={e => setMqtt(old => ({ ...old, user: e.target.value }))}/></label>
          <label><span>Topic prefix</span><input value={mqtt.topic} onChange={e => setMqtt(old => ({ ...old, topic: e.target.value }))}/></label>
        </div>
        <label><span>New MQTT password (leave blank to keep existing)</span>
          <input type="password" autoComplete="new-password" placeholder={config?.mqtt_password_set ? "Stored in device" : "No password stored"}
            value={mqtt.password} onChange={e => setMqtt(old => ({ ...old, password: e.target.value }))}/></label>
        <button className="button primary" disabled={!editable} onClick={() => {
          const patch: Record<string, unknown> = { broker: mqtt.broker, port: mqtt.port, user: mqtt.user,
            topic: mqtt.topic, enabled: mqtt.enabled };
          if (mqtt.password) patch.mqtt_password = mqtt.password;
          void save(patch, "MQTT settings saved on device.");
        }}>Save MQTT to device</button>
        <p className="card-copy">Current MQTT internal state: {current?.mqtt_state ?? "—"}. LAN MQTT port 1883 is unencrypted.</p>
      </section>}
      {tab === "protection" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">LOCAL SAFETY LIMITS</span><h3>Protection</h3></div><ShieldCheck size={20}/></div>
        <p className="card-copy">Firmware-level automatic shutdown remains active without Voltra. Set limits only within supported hardware ranges.</p>
        {(["temperature", "current", "power"] as const).map((key, i) => <div key={key}>
          <label className="native-checkbox"><input type="checkbox" checked={Boolean(protection.enabled & (1 << i))}
            onChange={e => setProtection(old => ({ ...old, enabled: bit(old.enabled, i, e.target.checked) }))}/>
            Enable {key} protection</label>
          <label><span>{key === "temperature" ? "Temperature (50–90 °C)" : key === "current" ? "Current (1–16 A)" : "Power (100–3000 W)"}</span>
            <input type="number" min={key === "temperature" ? 50 : key === "current" ? 1 : 100}
              max={key === "temperature" ? 90 : key === "current" ? 16 : 3000}
              step={key === "current" ? 0.1 : 1}
              value={key === "current" ? protection.current / 1000 : protection[key]}
              onChange={e => setProtection(old => ({ ...old, [key]: key === "current" ? Math.round(Number(e.target.value) * 1000) : Number(e.target.value) }))}/>
          </label>
        </div>)}
        <button className="button primary" disabled={!editable}
          onClick={() => void save({ protection }, "Protection thresholds saved on device.")}>Save protection to device</button>
      </section>}
      {tab === "scheduler" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">FLASH-RESIDENT SCHEDULER</span><h3>Scheduler</h3></div><CalendarClock size={20}/></div>
        <p className="card-copy">Eight rules supported: Daily, Weekly, Monthly date, Last day of month. Clock requires NTP. DST is manual; missed times are skipped.</p>
        {!status?.unix_ms && <div className="native-alert">Device clock is not synchronized. Connect the strip to Wi-Fi/NTP before relying on calendar schedules.</div>}
        {legacySchedules > 0 && <div className="native-alert">
          This strip still has {legacySchedules} old Voltra server schedule(s). They are blocked to avoid duplicate commands. Delete them in Automation after recreating the schedules here on-device.
        </div>}
        <label><span>Timezone (minutes east of UTC)</span>
          <select value={schedule.timezone} onChange={e => setSchedule(old => ({ ...old, timezone: Number(e.target.value) }))}>
            {Array.from({length: 105}, (_, i) => -720 + i * 15).map(t => <option key={t} value={t}>UTC{t < 0 ? "-" : "+"}{String(Math.floor(Math.abs(t) / 60)).padStart(2,"0")}:{String(Math.abs(t) % 60).padStart(2,"0")}</option>)}
          </select>
        </label>
        {schedule.rules.map((r, i) => (r.mode & 127) ? <div className="native-rule" key={i}>
          <div className="native-rule-head"><strong>Rule {i + 1}</strong>
            <label className="native-checkbox"><input type="checkbox" checked={Boolean(r.mode & 128)}
              onChange={e => updateRule(i, { mode: (r.mode & 127) | (e.target.checked ? 128 : 0) })}/> Enabled</label>
            <button className="button secondary" onClick={() => updateRule(i, emptyRule())}>Delete</button>
          </div>
          <div className="native-grid">
            <label><span>Repeat</span><select value={r.mode & 127} onChange={e => {
              const mode = Number(e.target.value);
              updateRule(i, { mode: mode | (r.mode & 128), day: mode === 2 ? 127 : mode === 3 ? 1 : 0 });
            }}>
              <option value={1}>Daily</option><option value={2}>Weekly</option>
              <option value={3}>Monthly date</option><option value={4}>Last day of month</option>
            </select></label>
            <label><span>Time</span><input type="time" value={String(Math.floor(r.minute / 60)).padStart(2,"0")+":"+String(r.minute % 60).padStart(2,"0")}
              onChange={e => { const [h,m] = e.target.value.split(":").map(Number); updateRule(i, {minute: h * 60 + m}); }}/></label>
            <label><span>Target</span><select value={r.channel} onChange={e => updateRule(i, {channel: Number(e.target.value)})}>
              {[0,1,2,3,4].map(c => <option key={c} value={c}>{c === 4 ? "All outlets" : `Outlet ${c + 1}`}</option>)}
            </select></label>
            <label><span>Action</span><select value={r.on} onChange={e => updateRule(i, {on: Number(e.target.value)})}>
              <option value={1}>ON</option><option value={0}>OFF</option></select></label>
          </div>
          {(r.mode & 127) === 2 && <div className="native-weekdays">
            {["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((day, weekday) => <label key={day} className="native-checkbox">
              <input type="checkbox" checked={Boolean(r.day & (1 << weekday))}
                onChange={e => updateRule(i, {day: bit(r.day, weekday, e.target.checked)})}/>{day}
            </label>)}
          </div>}
          {(r.mode & 127) === 3 && <label><span>Day of month</span><input type="number" min={1} max={31} value={r.day}
            onChange={e => updateRule(i, {day: Number(e.target.value)})}/></label>}
        </div> : null)}
        {conflicting && <div className="native-alert">A rule conflicts with an Auto OFF timer. Remove the timer or change the scheduled target before saving.</div>}
        <div className="two-buttons"><button className="button secondary" disabled={!editable || activeRules.length >= 8} onClick={addRule}>Add rule</button>
          <button className="button primary" disabled={!editable || conflicting}
            onClick={() => void save({ schedule }, "Schedule saved in device flash.")}>Save schedule to device</button></div>
        <p className="card-copy">The device retains these rules even if Voltra and Mosquitto stop. After power loss it needs a valid NTP clock to run calendar rules.</p>
      </section>}
      {tab === "timer" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">DEVICE AUTO OFF</span><h3>Timer</h3></div><Clock3 size={20}/></div>
        <p className="card-copy">Auto OFF from 1 minute to 24 hours after ON. 0 disables. A channel cannot have both an internal schedule and an auto-off timer.</p>
        <div className="native-grid">
          {timers.map((minutes, i) => <label key={i}><span>Outlet {i+1} · Minutes (0–1440)</span>
            <input type="number" min={0} max={1440} step={1} value={minutes}
              onChange={e => setTimers(old => old.map((t,j) => j === i ? Number(e.target.value) : t))}/></label>)}
        </div>
        {conflicting && <div className="native-alert">One or more timers conflict with scheduler rules. Remove the overlapping rule first.</div>}
        <button className="button primary" disabled={!editable || conflicting}
          onClick={() => void save({ timer_minutes: timers }, "Local auto-off timers saved in device flash.")}>Save timers to device</button>
        <p className="card-copy">After restart, an ON outlet starts its full auto-off countdown again.</p>
      </section>}
      {tab === "firmware" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">DEVICE UPDATE</span><h3>Firmware</h3></div><Cpu size={20}/></div>
        <p className="card-copy">Version: {String(details.firmware?.version || "2.1.x")} · Build: {String(details.firmware?.build_id || "—")} · OTA: {details.firmware?.ota_ready === true ? "Ready" : "Not supported or unavailable"}</p>
        <label><span>Firmware image (.fwr)</span><input type="file" accept=".fwr"
          onChange={e => setFirmware(e.target.files?.[0] || null)}/></label>
        <button className="button danger" disabled={busy || details.firmware?.ota_ready !== true || !firmware}
          onClick={async () => {
            if (!firmware || !window.confirm("Firmware flash may brick the strip. Do not unplug it. Proceed?")) return;
            const answer = window.prompt(`Type the device MAC ${mac} to authorize this flash:`);
            if (answer !== mac) return;
            setBusy(true);
            try { const result = await api.nativeOta(mac, firmware);
              notify("Firmware upload accepted. Reboot may take time; verify the new version after reconnect.");
              setError(JSON.stringify(result));
            } catch (exc) { notify("OTA result uncertain. Check device status before retrying: " + String(exc), true); }
            finally { setBusy(false); }
          }}>Upload firmware to this strip</button>
        <p className="card-copy">Not all firmware builds include OTA support. If unavailable, use the strip's own firmware updater.</p>
      </section>}
      {tab === "logs" && <section className="surface-card native-form">
        <div className="card-title-row"><div><span className="eyebrow">DIAGNOSTICS</span><h3>Logs and status</h3></div><Activity size={20}/></div>
        <p className="card-copy">The original firmware UI keeps its event history in the browser. Voltra can show its own audit events and live status, not recover a browser's private log.</p>
        <div className="native-metrics">
          <div><small>Wi-Fi RSSI</small><strong>{status?.rssi ?? "—"} dBm</strong></div>
          <div><small>Uptime</small><strong>{Math.floor((status?.uptime_ms || 0) / 60000)} min</strong></div>
          <div><small>Flash saves</small><strong>{status?.storage?.[0] ?? "—"}</strong></div>
          <div><small>Free heap</small><strong>{details.memory?.heap_free_bytes ?? "—"} B</strong></div>
        </div>
        <button className="button secondary" onClick={() => void api.nativeLogs(mac).then((r: {events: LogEvent[]}) => setLogs(r.events || []))}>Refresh activity</button>
        <div className="native-log">
          {logs.map((event, i) => <pre key={i}>{JSON.stringify(event, null, 2)}</pre>)}
          {!logs.length && <p className="card-copy">No Voltra events recorded for this strip.</p>}
        </div>
      </section>}
    </>}
  </div>;
}
