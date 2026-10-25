import { useState } from "react";
import { api } from "./api";
import type { Outlet, OutletPreferences, Strip } from "./types";

const icons = ["plug", "tv", "gamepad", "router", "computer", "light", "fan", "other"];
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
type Props = { strip: Strip; outlet: Outlet; onClose: () => void; onSaved: () => Promise<void> };

export function OutletEditor({ strip, outlet, onClose, onSaved }: Props) {
  const prefs = outlet.preferences || {};
  const [name, setName] = useState(prefs.name || "");
  const [icon, setIcon] = useState(prefs.icon || "plug");
  const [protectedOutlet, setProtected] = useState(Boolean(prefs.protected));
  const [locked, setLocked] = useState(Boolean(prefs.locked));
  const [notifications, setNotifications] = useState(Boolean(prefs.notifications));
  const [minutes, setMinutes] = useState(60);
  const [scheduleTime, setScheduleTime] = useState("23:00");
  const [scheduleOn, setScheduleOn] = useState(false);
  const [days, setDays] = useState([0, 1, 2, 3, 4, 5, 6]);
  const [threshold, setThreshold] = useState(5);
  const [duration, setDuration] = useState(120);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const act = async (action: () => Promise<unknown>) => {
    if (busy) return;
    setBusy(true); setMessage("");
    try { await action(); await onSaved(); setMessage("Saved / تم الحفظ"); }
    catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  };
  const target = { mac: strip.mac, outlet: outlet.channel };
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className="modal-card outlet-editor" role="dialog" aria-modal="true" aria-label="Outlet settings" onMouseDown={e => e.stopPropagation()}>
        <div className="modal-head"><h2>Outlet {outlet.channel} · إعدادات المخرج</h2><button className="icon-button" onClick={onClose}>×</button></div>
        <div className="outlet-editor-scroll">
          <label>Outlet name / اسم المخرج <input dir="auto" maxLength={80} value={name} onChange={e => setName(e.target.value)} /></label>
          <label>Icon / الأيقونة <select value={icon} onChange={e => setIcon(e.target.value)}>{icons.map(x => <option key={x} value={x}>{x}</option>)}</select></label>
          <label><input type="checkbox" checked={protectedOutlet} onChange={e => setProtected(e.target.checked)} /> Protected off / تأكيد قبل الإيقاف</label>
          <label><input type="checkbox" checked={locked} onChange={e => setLocked(e.target.checked)} /> Lock outlet / قفل التحكم</label>
          <label><input type="checkbox" checked={notifications} onChange={e => setNotifications(e.target.checked)} /> Log preference / تسجيل حالة التنبيهات</label>
          <button className="button primary" disabled={busy} onClick={() => act(() => api.outletPreferences(strip.mac, outlet.channel, { name, icon, protected: protectedOutlet, locked, notifications, restore_policy: "device" } satisfies OutletPreferences))}>Save preferences / حفظ</button>
          <hr />
          <h3>Auto-Off / الإيقاف بعد مدة</h3>
          <label>Minutes / دقائق <input type="number" min="1" max="43200" value={minutes} onChange={e => setMinutes(Number(e.target.value))}/></label>
          <button className="button secondary" disabled={busy || locked || protectedOutlet || minutes < 1} onClick={() => act(() => api.createCountdown({ ...target, on: false, delay_seconds: Math.min(2592000, minutes * 60), offline_policy: "skip" }))}>Start auto-off timer / بدء المؤقت</button>
          <hr />
          <h3>Weekly schedule / جدول أسبوعي</h3>
          <label>Time <input type="time" value={scheduleTime} onChange={e => setScheduleTime(e.target.value)} /></label>
          <label>Action <select value={scheduleOn ? "on" : "off"} onChange={e => setScheduleOn(e.target.value === "on")}><option value="on">ON</option><option value="off">OFF</option></select></label>
          <div className="outlet-weekdays">{weekdays.map((day, i) => <label key={day}><input type="checkbox" checked={days.includes(i)} onChange={e => setDays(prev => e.target.checked ? [...prev, i] : prev.filter(v => v !== i))}/>{day}</label>)}</div>
          <button className="button secondary" disabled={busy || !days.length || locked || (protectedOutlet && !scheduleOn)} onClick={() => act(() => api.createSchedule({ ...target, on: scheduleOn, time: scheduleTime, days, offline_policy: "skip" }))}>Add weekly schedule / إضافة جدول</button>
          <hr />
          <h3>Low-power auto-off / إيقاف عند انخفاض الاستهلاك</h3>
          <label>Watts threshold <input type="number" min="0" max="3000" value={threshold} onChange={e => setThreshold(Number(e.target.value))}/></label>
          <label>Stable for seconds <input type="number" min="10" max="86400" value={duration} onChange={e => setDuration(Number(e.target.value))}/></label>
          <button className="button secondary" disabled={busy || locked || protectedOutlet || threshold < 0 || duration < 10} onClick={() => act(() => api.createRule({ ...target, condition: "low_power", threshold, duration_s: duration, cooldown_s: 3600, action: { type: "set_outlet", outlet: outlet.channel, on: false } }))}>Create low-power rule / حفظ القاعدة</button>
          <small>Firmware controls power-loss restore. Protected/locked outlets reject automatic shutoff. Historical power and audit logs are available in Consumption and Settings.</small>
          {message && <p role="status">{message}</p>}
        </div>
      </section>
    </div>
  );
}
