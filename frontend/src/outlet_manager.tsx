import { useEffect, useState } from "react";
import { api } from "./api";
import { useLocale, t } from "./i18n";
import { Modal } from "./ui";
import type { AutomationSnapshot, EnergySummary, OutletPreferences, Overview, Strip } from "./types";

type Activity = { at: string; action: string; details: Record<string, unknown> };
const defaults: OutletPreferences = {
  name: "", icon: "plug", protected: false, locked: false, notify: true,
  restore_policy: "none", auto_off_minutes: 0, low_power_enabled: false,
  low_power_threshold_w: 5, low_power_duration_s: 300, alert_above_w: 0,
};
const icons = ["plug", "gamepad", "tv", "pc", "router", "lamp", "fan", "other"] as const;
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function OutletManagerDialog({
  selection, overview, automation, onClose, onChanged, notify,
}: {
  selection: { strip: Strip; channel: number } | null;
  overview: Overview;
  automation: AutomationSnapshot;
  onClose: () => void;
  onChanged: () => Promise<void>;
  notify: (text: string, error?: boolean) => void;
}) {
  const locale = useLocale();
  const [draft, setDraft] = useState<OutletPreferences>(defaults);
  const [today, setToday] = useState<EnergySummary | null>(null);
  const [month, setMonth] = useState<EnergySummary | null>(null);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [busy, setBusy] = useState(false);
  const [timerMins, setTimerMins] = useState(30);
  const [timerOn, setTimerOn] = useState(false);
  const [scheduleTime, setScheduleTime] = useState("23:00");
  const [scheduleOn, setScheduleOn] = useState(false);
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [sceneName, setSceneName] = useState("");
  const [sceneOn, setSceneOn] = useState(true);

  const strip = selection?.strip;
  const channel = selection?.channel || 1;
  const mac = strip?.mac || "";
  useEffect(() => {
    if (!selection) return;
    let alive = true;
    setToday(null); setMonth(null); setActivity([]);
    const fallback = strip?.outlets.find((x) => x.channel === channel)?.preferences
      || strip?.outlet_preferences?.[String(channel)] || {};
    setDraft({ ...defaults, ...fallback });
    void Promise.allSettled([
      api.outletPreferences(mac, channel),
      api.energySummary(mac, 24, channel),
      api.energySummary(mac, 24 * 30, channel),
      api.outletActivity(mac, channel),
    ]).then(([p, d, m, a]) => {
      if (!alive) return;
      if (p.status === "fulfilled") setDraft({ ...defaults, ...p.value });
      if (d.status === "fulfilled") setToday(d.value);
      if (m.status === "fulfilled") setMonth(m.value);
      if (a.status === "fulfilled") setActivity(a.value.events);
    });
    return () => { alive = false; };
  }, [mac, channel, Boolean(selection)]);

  if (!selection || !strip) return null;

  const update = <K extends keyof OutletPreferences>(key: K, value: OutletPreferences[K]) =>
    setDraft((old) => ({ ...old, [key]: value }));
  async function action(label: string, callback: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    try {
      await callback();
      await onChanged();
      notify(t(locale, label));
    } catch (e) {
      notify(e instanceof Error ? e.message : String(e), true);
    } finally { setBusy(false); }
  }
  const price = Number(overview.settings.energy_price_per_kwh || 0);
  const currency = overview.settings.currency || "EGP";
  const schedules = Object.values(automation.schedules).filter(
    (x) => x.mac === mac && x.outlet === channel && x.enabled !== false,
  );
  const label = draft.name.trim() || t(locale, "Outlet") + " " + channel;
  const nowPower = strip.outlets.find((x) => x.channel === channel)?.power_w || 0;

  return (
    <Modal open title={strip.name + " · " + label} onClose={onClose} footer={
      <>
        <button className="button secondary" onClick={onClose}>{t(locale, "Close")}</button>
        <button className="button primary" disabled={busy} onClick={() => void action("Saved", async () => {
          await api.saveOutletPreferences(mac, channel, draft);
          const fresh = await api.outletPreferences(mac, channel);
          setDraft(fresh);
        })}>{busy ? "…" : t(locale, "Save changes")}</button>
      </>
    }>
      <div className="outlet-manager">
        <div className="outlet-manager-energy">
          <span><strong>{Number(nowPower).toFixed(1)} W</strong><small>{t(locale, "Power now")}</small></span>
          <span><strong>{today ? today.energy_kwh.toFixed(3) + " kWh" : "—"}</strong><small>{t(locale, "Today")}</small></span>
          <span><strong>{month ? (month.energy_kwh * price).toFixed(2) + " " + currency : "—"}</strong><small>{t(locale, "Estimated 30-day cost")}</small></span>
        </div>

        <h3>{t(locale, "Customize outlet")}</h3>
        <label>{t(locale, "Outlet name")}
          <input dir="auto" maxLength={80} value={draft.name}
            placeholder={t(locale, "Example: PlayStation 5")}
            onChange={(e) => update("name", e.target.value)} />
        </label>
        <label>{t(locale, "Icon")}
          <select value={draft.icon} onChange={(e) => update("icon", e.target.value as OutletPreferences["icon"])}>
            {icons.map((x) => <option key={x} value={x}>{t(locale, x)}</option>)}
          </select>
        </label>

        <h3>{t(locale, "Safety and notifications")}</h3>
        <label className="outlet-check"><input type="checkbox" checked={draft.protected}
          onChange={(e) => update("protected", e.target.checked)} />
          <span><strong>{t(locale, "Protected outlet")}</strong><small>{t(locale, "Confirm manual power-off; block automated shutoff")}</small></span>
        </label>
        <label className="outlet-check"><input type="checkbox" checked={draft.locked}
          onChange={(e) => update("locked", e.target.checked)} />
          <span><strong>{t(locale, "Lock control")}</strong><small>{t(locale, "Block all ON/OFF commands until unlocked")}</small></span>
        </label>
        <label className="outlet-check"><input type="checkbox" checked={draft.notify}
          onChange={(e) => update("notify", e.target.checked)} />
          <span><strong>{t(locale, "Activity notifications")}</strong><small>{t(locale, "Show live activity in connected dashboards")}</small></span>
        </label>

        <h3>{t(locale, "Timers and automatic shutdown")}</h3>
        <label>{t(locale, "Auto-off after turning on (minutes, 0 = off)")}
          <input type="number" min={0} max={10080} value={draft.auto_off_minutes}
            onChange={(e) => update("auto_off_minutes", Number(e.target.value))} />
        </label>
        <label className="outlet-check"><input type="checkbox" checked={draft.low_power_enabled}
          onChange={(e) => update("low_power_enabled", e.target.checked)} />
          <span>{t(locale, "Auto-off when power stays low")}</span>
        </label>
        {draft.low_power_enabled && <div className="outlet-two">
          <label>{t(locale, "Power below (W)")}<input type="number" min={0} max={50000}
            value={draft.low_power_threshold_w}
            onChange={(e) => update("low_power_threshold_w", Number(e.target.value))} /></label>
          <label>{t(locale, "For seconds")}<input type="number" min={30} max={86400}
            value={draft.low_power_duration_s}
            onChange={(e) => update("low_power_duration_s", Number(e.target.value))} /></label>
        </div>}
        <label>{t(locale, "Alert when power exceeds (W, 0 = off)")}
          <input type="number" min={0} max={50000} value={draft.alert_above_w}
            onChange={(e) => update("alert_above_w", Number(e.target.value))} />
        </label>
        <label>{t(locale, "After reconnecting to server")}
          <select value={draft.restore_policy} onChange={(e) => update("restore_policy", e.target.value as OutletPreferences["restore_policy"])}>
            <option value="none">{t(locale, "Keep device state (recommended)")}</option>
            <option value="off">{t(locale, "Switch off on reconnect")}</option>
            <option value="last">{t(locale, "Restore last confirmed state on reconnect")}</option>
          </select>
        </label>
        <p className="outlet-help">{t(locale, "Reconnect policy runs only when the strip reconnects to Voltra, not on every power loss.")}</p>

        <h3>{t(locale, "Quick timer")}</h3>
        <div className="outlet-two">
          <label>{t(locale, "Minutes")}<input type="number" min={1} max={43200} value={timerMins}
            onChange={(e) => setTimerMins(Number(e.target.value))} /></label>
          <label>{t(locale, "Action")}<select value={String(timerOn)} onChange={(e) => setTimerOn(e.target.value === "true")}>
            <option value="false">{t(locale, "Switch OFF")}</option>
            <option value="true">{t(locale, "Switch ON")}</option>
          </select></label>
        </div>
        <button className="button secondary wide" disabled={busy || timerMins < 1 || timerMins > 43200}
          onClick={() => void action("Timer created", () => api.createCountdown({
            mac, outlet: channel, on: timerOn, delay_seconds: timerMins * 60, offline_policy: "skip",
          }))}>{t(locale, "Start timer")}</button>

        <h3>{t(locale, "Weekly schedule")}</h3>
        <div className="outlet-two">
          <label>{t(locale, "Time")}<input type="time" value={scheduleTime}
            onChange={(e) => setScheduleTime(e.target.value)} /></label>
          <label>{t(locale, "Action")}<select value={String(scheduleOn)}
            onChange={(e) => setScheduleOn(e.target.value === "true")}>
            <option value="true">{t(locale, "Switch ON")}</option>
            <option value="false">{t(locale, "Switch OFF")}</option>
          </select></label>
        </div>
        <div className="outlet-weekdays">{weekdays.map((day, index) => <label key={day}>
          <input type="checkbox" checked={days.includes(index)}
            onChange={(e) => setDays((old) => e.target.checked ? [...old, index] : old.filter((x) => x !== index))} />{t(locale, day)}
        </label>)}</div>
        <button className="button secondary wide" disabled={busy || !days.length} onClick={() => void action("Schedule created",
          () => api.createSchedule({ mac, outlet: channel, on: scheduleOn,
            time: scheduleTime, days: [...days].sort(), offline_policy: "skip" }))}>
          {t(locale, "Create weekly schedule")}
        </button>
        {schedules.length > 0 && <div className="outlet-plans">{schedules.map((schedule) => (
          <div key={schedule.id}><span>{schedule.on ? t(locale, "ON") : t(locale, "OFF")} · {schedule.time || schedule.run_at || "—"}</span>
          <button disabled={busy} onClick={() => void action("Schedule deleted", () => api.deleteSchedule(schedule.id))}>
            {t(locale, "Delete")}</button></div>
        ))}</div>}

        <h3>{t(locale, "Quick scene")}</h3>
        <label>{t(locale, "Scene name")}<input dir="auto" value={sceneName} maxLength={100}
          onChange={(e) => setSceneName(e.target.value)} placeholder={t(locale, "Example: Gaming mode")} /></label>
        <label>{t(locale, "Action")}<select value={String(sceneOn)} onChange={(e) => setSceneOn(e.target.value === "true")}>
          <option value="true">{t(locale, "Switch ON")}</option>
          <option value="false">{t(locale, "Switch OFF")}</option>
        </select></label>
        <button className="button secondary wide" disabled={busy || !sceneName.trim()}
          onClick={() => void action("Scene created", () => api.createScene({
            name: sceneName.trim(), actions: [{ mac, outlet: channel, on: sceneOn }],
          }))}>{t(locale, "Save quick scene")}</button>

        <h3>{t(locale, "Recent activity")}</h3>
        <div className="outlet-activity">{activity.length ? activity.map((x, i) => (
          <div key={x.at + i}><strong>{x.action.replaceAll("_", " ")}</strong>
          <small>{new Date(x.at).toLocaleString(locale === "ar" ? "ar-EG" : "en-US")}</small></div>
        )) : <p>{t(locale, "No outlet activity recorded yet.")}</p>}</div>
        <p className="outlet-help">{t(locale, "Settings are stored on the local server and shared with Android. Background push alerts require additional phone notification support.")}</p>
      </div>
    </Modal>
  );
}
