import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlarmClock,
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  BellRing,
  Bolt,
  CalendarClock,
  CirclePlus,
  Clock3,
  Coins,
  Gauge,
  HardDriveDownload,
  HeartPulse,
  History,
  MapPin,
  Play,
  Power,
  PowerOff,
  Router,
  Save,
  Server,
  ShieldCheck,
  Sparkles,
  Trash2,
  Wifi,
  Zap,
} from "lucide-react";

import { api } from "./api";
import {
  EmptyState,
  EnergyChart,
  Icons,
  MetricCard,
  QuickActions,
  SearchBar,
  StripCard,
} from "./ui";
import type {
  AutomationSnapshot,
  EnergyHistory,
  EnergySummary,
  Mapping,
  Overview,
  Settings,
  Strip,
  ViewName,
} from "./types";

function activeStrips(overview: Overview) {
  return overview.strips.filter(
    (strip) => strip.managed && (strip.state === "active" || strip.state === "disabled"),
  );
}

function targetOptions(overview: Overview) {
  return activeStrips(overview)
    .filter((strip) => strip.enabled && strip.state === "active")
    .flatMap((strip) =>
      [1, 2, 3, 4].map((outlet) => ({
        value: `${strip.mac}:${outlet}`,
        label: `${strip.name} · Outlet ${outlet}`,
        mac: strip.mac,
        outlet,
      })),
    );
}

function parseTarget(value: string) {
  const index = value.lastIndexOf(":");
  if (index < 1) throw new Error("Choose an outlet first.");
  return { mac: value.slice(0, index), outlet: Number(value.slice(index + 1)) };
}

export function DashboardView({
  overview,
  automation,
  search,
  onSearch,
  busyChannels,
  onNavigate,
  onToggleOutlet,
  onSetAll,
  onStripSettings,
}: {
  overview: Overview;
  automation: AutomationSnapshot;
  search: string;
  onSearch: (value: string) => void;
  busyChannels: Set<string>;
  onNavigate: (view: ViewName) => void;
  onToggleOutlet: (strip: Strip, outlet: number, on: boolean) => void;
  onSetAll: (strip: Strip, on: boolean) => void;
  onStripSettings: (strip: Strip) => void;
}) {
  const strips = activeStrips(overview);
  const normalized = search.trim().toLowerCase();
  const filtered = strips.filter((strip) => {
    if (!normalized) return true;
    const mappedNames = Object.entries(overview.mappings)
      .filter(([, mapping]) => mapping.mac === strip.mac)
      .map(([id]) => overview.ps4_devices.find((device) => String(device.id) === id)?.name || id);
    return [strip.name, strip.mac, strip.room, ...mappedNames]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(normalized);
  });

  const outlets = strips.flatMap((strip) => strip.outlets || []);
  const outletOn = outlets.filter((outlet) => outlet.relay).length;
  const outletTotal = strips.length * 4;
  const schedules = Object.values(automation.schedules || {}).filter(
    (schedule) => schedule.enabled !== false,
  ).length;

  return (
    <>
      <button className="profile-card" onClick={() => onNavigate("settings")}>
        <span className="avatar">VL</span>
        <span className="profile-copy">
          <strong>Voltra Local</strong>
          <small>v{overview.version} · Local mini server</small>
        </span>
        <span className="profile-chevron">›</span>
      </button>

      <section className="power-hero">
        <span>Total power right now</span>
        <div className="power-value">
          <strong>{Number(overview.summary.total_power_w || 0).toFixed(1)}</strong>
          <small>W</small>
        </div>
        <div className="hero-meta">
          <span><b>{overview.summary.online_strips}</b> strips online</span>
          <span><b>{outletOn}/{outletTotal}</b> outlets on</span>
          <span><b>{schedules}</b> plans active</span>
        </div>
      </section>

      <QuickActions onOpen={onNavigate} />
      <SearchBar value={search} onChange={onSearch} />

      <section className="section-head compact">
        <div>
          <span className="eyebrow">LIVE DEVICES</span>
          <h2>{normalized ? "Search results" : "Your strips"}</h2>
        </div>
        <span className="count-badge">{filtered.length}</span>
      </section>

      <div className="strip-list">
        {filtered.map((strip) => (
          <StripCard
            key={strip.mac}
            strip={strip}
            mappings={overview.mappings}
            devices={overview.ps4_devices}
            busyChannels={busyChannels}
            onToggle={(outlet, on) => onToggleOutlet(strip, outlet, on)}
            onSetAll={(on) => onSetAll(strip, on)}
            onSettings={() => onStripSettings(strip)}
          />
        ))}
        {!filtered.length && (
          <EmptyState
            title={normalized ? "No matching strips" : "No strips yet"}
            description={
              normalized
                ? "Try a strip name, room, MAC address, or mapped device name."
                : "Add your first MTTL-W01 strip and it will appear here."
            }
            action={
              !normalized ? (
                <button className="button primary" onClick={() => onNavigate("add")}>
                  <CirclePlus size={17} /> Add strip
                </button>
              ) : undefined
            }
          />
        )}
      </div>

      <button className="fab" onClick={() => onNavigate("add")} aria-label="Add strip">
        <CirclePlus size={20} /> <span>Add strip</span>
      </button>
    </>
  );
}

export function EnergyView({
  overview,
  notify,
}: {
  overview: Overview;
  notify: (message: string, error?: boolean) => void;
}) {
  const strips = activeStrips(overview);
  const [mac, setMac] = useState(strips[0]?.mac || "");
  const [hours, setHours] = useState(24);
  const [outlet, setOutlet] = useState<number | null>(null);
  const [summary, setSummary] = useState<EnergySummary | null>(null);
  const [history, setHistory] = useState<EnergyHistory | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!mac && strips[0]) setMac(strips[0].mac);
  }, [mac, strips]);

  useEffect(() => {
    if (!mac) return;
    let cancelled = false;
    setBusy(true);
    Promise.all([api.energySummary(mac, hours, outlet), api.energyHistory(mac, hours, outlet)])
      .then(([nextSummary, nextHistory]) => {
        if (cancelled) return;
        setSummary(nextSummary);
        setHistory(nextHistory);
      })
      .catch((error) => {
        if (!cancelled) notify(error instanceof Error ? error.message : String(error), true);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mac, hours, outlet]);

  const cost =
    Number(summary?.energy_kwh || 0) * Number(overview.settings.energy_price_per_kwh || 0);

  return (
    <div className="view-stack">
      <section className="section-head">
        <div>
          <span className="eyebrow">ENERGY INSIGHTS</span>
          <h2>Consumption</h2>
          <p>Local history from Voltra telemetry. No cloud required.</p>
        </div>
      </section>

      <section className="filter-card">
        <label>
          <span>Strip</span>
          <select value={mac} onChange={(e) => setMac(e.target.value)}>
            {strips.map((strip) => <option key={strip.mac} value={strip.mac}>{strip.name}</option>)}
          </select>
        </label>
        <label>
          <span>Period</span>
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            <option value={6}>6 hours</option>
            <option value={24}>24 hours</option>
            <option value={168}>7 days</option>
            <option value={720}>30 days</option>
          </select>
        </label>
        <label>
          <span>Scope</span>
          <select value={outlet ?? ""} onChange={(e) => setOutlet(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Whole strip</option>
            <option value="1">Outlet 1</option>
            <option value="2">Outlet 2</option>
            <option value="3">Outlet 3</option>
            <option value="4">Outlet 4</option>
          </select>
        </label>
      </section>

      <div className="metric-grid">
        <MetricCard icon={Activity} label="Average power" value={`${Number(summary?.average_power_w || 0).toFixed(1)} W`} />
        <MetricCard icon={Zap} label="Peak power" value={`${Number(summary?.max_power_w || 0).toFixed(1)} W`} />
        <MetricCard icon={BarChart3} label="Energy" value={`${Number(summary?.energy_kwh || 0).toFixed(3)} kWh`} accent />
        <MetricCard icon={Coins} label="Estimated cost" value={`${cost.toFixed(2)} ${overview.settings.currency}`} />
      </div>

      <section className="surface-card chart-card">
        <div className="card-title-row">
          <div>
            <span className="eyebrow">POWER HISTORY</span>
            <h3>{outlet ? `Outlet ${outlet}` : "Whole strip"}</h3>
          </div>
          <span className={`live-chip ${busy ? "loading" : ""}`}>{busy ? "Updating" : `${history?.samples || 0} samples`}</span>
        </div>
        <EnergyChart points={history?.points || []} />
      </section>
    </div>
  );
}

export function AutomationView({
  overview,
  automation,
  reload,
  notify,
}: {
  overview: Overview;
  automation: AutomationSnapshot;
  reload: () => Promise<void>;
  notify: (message: string, error?: boolean) => void;
}) {
  const options = targetOptions(overview);
  const [target, setTarget] = useState(options[0]?.value || "");
  const [actionOn, setActionOn] = useState(false);
  const [time, setTime] = useState("23:00");
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [offlinePolicy, setOfflinePolicy] = useState<"queue" | "skip">("queue");
  const [ruleCondition, setRuleCondition] = useState("weak_wifi");
  const [ruleThreshold, setRuleThreshold] = useState("-75");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!target && options[0]) setTarget(options[0].value);
  }, [target, options]);

  const schedules = Object.values(automation.schedules || {}).sort((a, b) =>
    String(b.created_at || "").localeCompare(String(a.created_at || "")),
  );
  const rules = Object.values(automation.rules || {});

  async function createSchedule() {
    try {
      setBusy(true);
      const parsed = parseTarget(target);
      await api.createSchedule({
        ...parsed,
        on: actionOn,
        time,
        days,
        offline_policy: offlinePolicy,
      });
      await reload();
      notify("Schedule created.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  async function countdown(minutes: number) {
    try {
      setBusy(true);
      const parsed = parseTarget(target);
      await api.createCountdown({
        ...parsed,
        on: actionOn,
        delay_seconds: minutes * 60,
        offline_policy: offlinePolicy,
      });
      await reload();
      notify(`${minutes} minute timer created.`);
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  async function createRule() {
    try {
      setBusy(true);
      const parsed = parseTarget(target);
      const threshold = ruleCondition === "offline" ? undefined : Number(ruleThreshold);
      await api.createRule({
        mac: parsed.mac,
        outlet: ruleCondition === "low_power" ? parsed.outlet : undefined,
        condition: ruleCondition,
        threshold,
        duration_s: ruleCondition === "low_power" ? 900 : 0,
        cooldown_s: 300,
        action: { type: "audit" },
      });
      await reload();
      notify("Automation rule created.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];

  return (
    <div className="view-stack">
      <section className="section-head">
        <div>
          <span className="eyebrow">LOCAL AUTOMATION</span>
          <h2>Automation</h2>
          <p>Schedules and timers keep running without Internet while the Voltra server is online.</p>
        </div>
        <span className="count-badge">{schedules.length + rules.length}</span>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div>
            <span className="eyebrow">NEW PLAN</span>
            <h3>Schedule an outlet</h3>
          </div>
          <CalendarClock size={20} />
        </div>
        <div className="form-grid">
          <label className="span-2">
            <span>Target outlet</span>
            <select value={target} onChange={(e) => setTarget(e.target.value)}>
              {options.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label>
            <span>Time</span>
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          </label>
          <label>
            <span>Action</span>
            <select value={actionOn ? "on" : "off"} onChange={(e) => setActionOn(e.target.value === "on")}>
              <option value="off">Turn off</option>
              <option value="on">Turn on</option>
            </select>
          </label>
          <label>
            <span>If strip is offline</span>
            <select value={offlinePolicy} onChange={(e) => setOfflinePolicy(e.target.value as "queue" | "skip")}>
              <option value="queue">Queue until reconnect</option>
              <option value="skip">Skip this run</option>
            </select>
          </label>
        </div>
        <div className="day-row" aria-label="Schedule days">
          {dayLabels.map((label, day) => (
            <button
              key={day}
              className={days.includes(day) ? "active" : ""}
              onClick={() => setDays((current) =>
                current.includes(day) ? current.filter((item) => item !== day) : [...current, day].sort(),
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <button className="button primary wide" disabled={busy || !target || !days.length} onClick={createSchedule}>
          <CalendarClock size={17} /> Create schedule
        </button>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div>
            <span className="eyebrow">QUICK TIMER</span>
            <h3>Countdown</h3>
          </div>
          <AlarmClock size={20} />
        </div>
        <div className="countdown-grid">
          {[15, 30, 60, 120].map((minutes) => (
            <button key={minutes} onClick={() => countdown(minutes)} disabled={busy || !target}>
              <Clock3 size={16} /> {minutes < 60 ? `${minutes}m` : `${minutes / 60}h`}
            </button>
          ))}
        </div>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div>
            <span className="eyebrow">SMART RULES</span>
            <h3>Health & power alerts</h3>
          </div>
          <BellRing size={20} />
        </div>
        <div className="form-grid">
          <label>
            <span>Condition</span>
            <select value={ruleCondition} onChange={(e) => setRuleCondition(e.target.value)}>
              <option value="weak_wifi">Weak Wi-Fi</option>
              <option value="low_power">Low power for 15m</option>
              <option value="voltage_below">Voltage below</option>
              <option value="voltage_above">Voltage above</option>
              <option value="offline">Device offline</option>
            </select>
          </label>
          {ruleCondition !== "offline" && (
            <label>
              <span>Threshold</span>
              <input value={ruleThreshold} onChange={(e) => setRuleThreshold(e.target.value)} inputMode="decimal" />
            </label>
          )}
        </div>
        <button className="button secondary wide" disabled={busy || !target} onClick={createRule}>
          <Sparkles size={17} /> Create audit rule
        </button>
      </section>

      <section className="section-head compact">
        <div><span className="eyebrow">ACTIVE PLANS</span><h2>Schedules</h2></div>
      </section>
      <div className="list-stack">
        {schedules.map((schedule) => {
          const strip = overview.strips.find((item) => item.mac === schedule.mac);
          const detail = schedule.type === "once" || schedule.run_at
            ? new Date(String(schedule.run_at)).toLocaleString()
            : `${schedule.time || "—"} · ${schedule.days?.length || 0} days`;
          return (
            <article className="list-card" key={schedule.id}>
              <span className="list-icon"><CalendarClock size={18} /></span>
              <div>
                <strong>{strip?.name || schedule.mac} · Outlet {schedule.outlet}</strong>
                <small>{detail} · {schedule.on ? "Turn on" : "Turn off"} · {schedule.offline_policy || "queue"}</small>
              </div>
              <button
                className="icon-button danger-ghost"
                onClick={async () => {
                  await api.deleteSchedule(schedule.id);
                  await reload();
                  notify("Schedule removed.");
                }}
                aria-label="Delete schedule"
              >
                <Trash2 size={16} />
              </button>
            </article>
          );
        })}
        {!schedules.length && <EmptyState icon={CalendarClock} title="No schedules" description="Create a schedule or countdown above." />}
      </div>

      <section className="section-head compact">
        <div><span className="eyebrow">RULES</span><h2>Automation rules</h2></div>
      </section>
      <div className="list-stack">
        {rules.map((rule) => (
          <article className="list-card" key={rule.id}>
            <span className="list-icon"><Sparkles size={18} /></span>
            <div>
              <strong>{rule.condition.replaceAll("_", " ")}</strong>
              <small>{overview.strips.find((item) => item.mac === rule.mac)?.name || rule.mac}{rule.threshold != null ? ` · threshold ${rule.threshold}` : ""}</small>
            </div>
            <button
              className="icon-button danger-ghost"
              onClick={async () => {
                await api.deleteRule(rule.id);
                await reload();
                notify("Rule removed.");
              }}
              aria-label="Delete rule"
            >
              <Trash2 size={16} />
            </button>
          </article>
        ))}
      </div>

      {!!automation.queue?.length && (
        <button
          className="button danger wide"
          onClick={async () => {
            await api.clearQueue();
            await reload();
            notify("Offline queue cleared.");
          }}
        >
          <Trash2 size={17} /> Clear {automation.queue.length} queued commands
        </button>
      )}

      {!!overview.scenes.length && (
        <>
          <section className="section-head compact">
            <div><span className="eyebrow">SCENES</span><h2>Saved scenes</h2></div>
          </section>
          <div className="scene-grid">
            {overview.scenes.map((scene) => (
              <button
                key={scene.id}
                className="scene-card"
                onClick={async () => {
                  try {
                    await api.runScene(scene.id);
                    notify(`${scene.name} executed.`);
                  } catch (error) {
                    notify(error instanceof Error ? error.message : String(error), true);
                  }
                }}
              >
                <span><Play size={18} /></span>
                <strong>{scene.name}</strong>
                <small>{scene.actions.length} actions</small>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function RoomsView({
  overview,
  refresh,
  notify,
}: {
  overview: Overview;
  refresh: () => Promise<void>;
  notify: (message: string, error?: boolean) => void;
}) {
  const strips = activeStrips(overview);
  const [roomDrafts, setRoomDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    setRoomDrafts(Object.fromEntries(strips.map((strip) => [strip.mac, strip.room || ""])));
  }, [overview.version, overview.strips.length]);

  const outletOptions = useMemo(() => {
    const rows: Array<{ value: string; label: string }> = [];
    strips
      .filter((strip) => strip.enabled && strip.state === "active")
      .forEach((strip) => {
        [1, 2, 3, 4].forEach((outlet) => {
          rows.push({ value: `${strip.mac}:${outlet}`, label: `${strip.name} · Outlet ${outlet}` });
        });
      });
    return rows;
  }, [strips]);

  async function saveRoom(strip: Strip) {
    try {
      await api.stripPreferences(strip.mac, { room: roomDrafts[strip.mac] || "" });
      await refresh();
      notify("Room updated.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    }
  }

  async function updateMapping(deviceId: string, value: string) {
    try {
      if (!value) {
        await api.clearMapping(deviceId);
      } else {
        const parsed = parseTarget(value);
        await api.setMapping(deviceId, parsed.mac, parsed.outlet);
      }
      await refresh();
      notify("Mapping saved.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    }
  }

  return (
    <div className="view-stack">
      <section className="section-head">
        <div>
          <span className="eyebrow">ORGANIZE</span>
          <h2>Rooms</h2>
          <p>Group strips by location and map each PlayStation/display to a physical outlet.</p>
        </div>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">STRIP LOCATIONS</span><h3>Room names</h3></div>
          <MapPin size={20} />
        </div>
        <div className="room-list">
          {strips.map((strip) => (
            <div className="room-row" key={strip.mac}>
              <span className="room-device"><span className={`mini-dot ${strip.online ? "" : "offline"}`} /> <b dir="auto">{strip.name}</b></span>
              <input
                value={roomDrafts[strip.mac] ?? ""}
                placeholder="e.g. Living Room"
                onChange={(e) => setRoomDrafts((current) => ({ ...current, [strip.mac]: e.target.value }))}
              />
              <button className="icon-button" onClick={() => saveRoom(strip)} aria-label="Save room"><Save size={16} /></button>
            </div>
          ))}
        </div>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">PLAYSTATION MAPPING</span><h3>Devices → outlets</h3></div>
          <Router size={20} />
        </div>
        <div className="mapping-list">
          {overview.ps4_devices.map((device) => {
            const mapping = overview.mappings[device.id];
            const value = mapping ? `${mapping.mac}:${mapping.outlet}` : "";
            return (
              <label className="mapping-row" key={device.id}>
                <span><strong dir="auto">{device.name}</strong><small>{device.id}</small></span>
                <select value={value} onChange={(e) => updateMapping(device.id, e.target.value)}>
                  <option value="">Not mapped</option>
                  {outletOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                </select>
              </label>
            );
          })}
          {!overview.ps4_devices.length && (
            <EmptyState icon={Router} title="No PlayStation devices" description="Sync devices from PlayZone or use the legacy console to add them manually." />
          )}
        </div>
      </section>
    </div>
  );
}

export function AddStripView({
  overview,
  refresh,
  notify,
}: {
  overview: Overview;
  refresh: () => Promise<void>;
  notify: (message: string, error?: boolean) => void;
}) {
  const pending = overview.strips.filter((strip) => strip.state === "pending");
  const [names, setNames] = useState<Record<string, string>>({});
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [serverIp, setServerIp] = useState("");
  const [deviceIp, setDeviceIp] = useState("192.168.1.1");
  const [busy, setBusy] = useState(false);

  async function adopt(strip: Strip) {
    try {
      setBusy(true);
      await api.adoptStrip(strip.mac, names[strip.mac]?.trim() || strip.name || `Voltra ${strip.mac.slice(-4)}`);
      await refresh();
      notify("Strip added.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  async function provision() {
    try {
      setBusy(true);
      await api.provision({ ssid, password, server_ip: serverIp, device_ip: deviceIp });
      setPassword("");
      notify("Wi-Fi settings sent. Wait for the strip to reboot and reconnect.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view-stack">
      <section className="section-head">
        <div>
          <span className="eyebrow">ONBOARDING</span>
          <h2>Add strip</h2>
          <p>Voltra automatically discovers strips that connect to TCP 10086.</p>
        </div>
        <span className="count-badge">{pending.length}</span>
      </section>

      <div className="pending-grid">
        {pending.map((strip) => (
          <article className="pending-card" key={strip.mac}>
            <div className="pending-head">
              <span className="device-orb"><Zap size={20} /></span>
              <div><strong>New MTTL-W01</strong><small>{strip.online ? "Online now" : "Seen previously"}</small></div>
              <span className={`live-chip ${strip.online ? "" : "muted"}`}>{strip.online ? "READY" : "OFFLINE"}</span>
            </div>
            <div className="mono-info">{strip.mac} · {strip.last_ip || "No IP"}</div>
            <input
              placeholder="Strip name"
              value={names[strip.mac] ?? strip.name}
              onChange={(e) => setNames((current) => ({ ...current, [strip.mac]: e.target.value }))}
            />
            <div className="two-buttons">
              <button className="button primary" disabled={busy || !strip.online} onClick={() => adopt(strip)}>
                <CirclePlus size={16} /> Add strip
              </button>
              <button
                className="button secondary"
                disabled={busy}
                onClick={async () => {
                  await api.ignoreStrip(strip.mac);
                  await refresh();
                  notify("Strip ignored.");
                }}
              >
                Ignore
              </button>
            </div>
          </article>
        ))}
        {!pending.length && (
          <EmptyState icon={Wifi} title="Waiting for a new strip" description="When an MTTL-W01 connects to this server, it will appear here automatically." />
        )}
      </div>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">WI-FI SETUP</span><h3>Provision a new strip</h3></div>
          <Wifi size={20} />
        </div>
        <p className="card-copy">Use this only while the Voltra host can reach the strip's temporary TONLY_TAP Wi-Fi network.</p>
        <div className="form-grid">
          <label><span>2.4 GHz Wi-Fi SSID</span><input value={ssid} onChange={(e) => setSsid(e.target.value)} /></label>
          <label><span>Wi-Fi password</span><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <label><span>Voltra server LAN IP</span><input placeholder="192.168.1.65" value={serverIp} onChange={(e) => setServerIp(e.target.value)} /></label>
          <label><span>Strip setup IP</span><input value={deviceIp} onChange={(e) => setDeviceIp(e.target.value)} /></label>
        </div>
        <button className="button primary wide" disabled={busy || !ssid || !serverIp} onClick={provision}>
          <Router size={17} /> Send network settings
        </button>
      </section>
    </div>
  );
}

export function SettingsView({
  overview,
  refresh,
  notify,
}: {
  overview: Overview;
  refresh: () => Promise<void>;
  notify: (message: string, error?: boolean) => void;
}) {
  const [settings, setSettings] = useState<Settings>(overview.settings);
  const [busy, setBusy] = useState(false);

  useEffect(() => setSettings(overview.settings), [overview.settings]);

  async function save() {
    try {
      setBusy(true);
      await api.updateSettings(settings);
      await refresh();
      notify("Settings saved.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  async function exportBackup() {
    try {
      const backup = await api.backup();
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `voltra-backup-${new Date().toISOString().slice(0, 10)}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      notify("Backup exported.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    }
  }

  async function restoreFile(file: File | undefined) {
    if (!file) return;
    try {
      setBusy(true);
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      await api.restore(parsed);
      await refresh();
      notify("Backup restored.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="view-stack">
      <section className="section-head">
        <div>
          <span className="eyebrow">SYSTEM</span>
          <h2>Settings</h2>
          <p>Local preferences, safety thresholds, backup and advanced access.</p>
        </div>
      </section>

      <div className="system-grid">
        <MetricCard icon={Server} label="Server version" value={`v${overview.version}`} accent />
        <MetricCard icon={HeartPulse} label="Online strips" value={String(overview.summary.online_strips)} />
        <MetricCard icon={ShieldCheck} label="Mode" value={overview.mode.toUpperCase()} />
        <MetricCard icon={Bolt} label="Current load" value={`${Number(overview.summary.total_power_w || 0).toFixed(1)} W`} />
      </div>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">ENERGY</span><h3>Cost settings</h3></div>
          <Coins size={20} />
        </div>
        <div className="form-grid">
          <label><span>Price per kWh</span><input type="number" step="0.01" value={settings.energy_price_per_kwh} onChange={(e) => setSettings({ ...settings, energy_price_per_kwh: Number(e.target.value) })} /></label>
          <label><span>Currency</span><input value={settings.currency} onChange={(e) => setSettings({ ...settings, currency: e.target.value.toUpperCase() })} /></label>
        </div>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">HEALTH THRESHOLDS</span><h3>Diagnostics</h3></div>
          <Gauge size={20} />
        </div>
        <div className="form-grid">
          <label><span>Weak Wi-Fi dBm</span><input type="number" value={settings.weak_wifi_dbm} onChange={(e) => setSettings({ ...settings, weak_wifi_dbm: Number(e.target.value) })} /></label>
          <label><span>Unusual power W</span><input type="number" value={settings.unusual_power_w} onChange={(e) => setSettings({ ...settings, unusual_power_w: Number(e.target.value) })} /></label>
          <label><span>Minimum voltage</span><input type="number" value={settings.voltage_min_v} onChange={(e) => setSettings({ ...settings, voltage_min_v: Number(e.target.value) })} /></label>
          <label><span>Maximum voltage</span><input type="number" value={settings.voltage_max_v} onChange={(e) => setSettings({ ...settings, voltage_max_v: Number(e.target.value) })} /></label>
        </div>
        <button className="button primary wide" disabled={busy} onClick={save}><Save size={17} /> Save settings</button>
      </section>

      <section className="surface-card">
        <div className="card-title-row">
          <div><span className="eyebrow">BACKUP</span><h3>Configuration safety</h3></div>
          <HardDriveDownload size={20} />
        </div>
        <div className="backup-grid">
          <button className="button secondary" onClick={exportBackup}><ArrowDownToLine size={17} /> Export backup</button>
          <label className="button secondary file-button">
            <ArrowUpFromLine size={17} /> Restore backup
            <input type="file" accept="application/json,.json" onChange={(e) => restoreFile(e.target.files?.[0])} />
          </label>
        </div>
      </section>

      <section className="legacy-card">
        <span><History size={20} /></span>
        <div><strong>Legacy console</strong><small>All older advanced controls remain available as a safety fallback.</small></div>
        <a className="button secondary" href="/voltra/legacy">Open</a>
      </section>
    </div>
  );
}
