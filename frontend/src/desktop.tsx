import { useState } from "react";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  CalendarClock,
  CirclePlus,
  Gauge,
  Home,
  MapPin,
  PlugZap,
  RefreshCw,
  Search,
  Server,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Wifi,
  WifiOff,
  Zap,
} from "lucide-react";

import { EmptyState, SearchBar, StripCard, viewMeta } from "./ui";
import type { AutomationSnapshot, Overview, Strip, ViewName } from "./types";

type WorkspaceProps = {
  view: ViewName;
  onNavigate: (view: ViewName) => void;
};

const navigation: Array<{ label: string; view: ViewName; icon: typeof Home }> = [
  { label: "Dashboard", view: "dashboard", icon: Home },
  { label: "Consumption", view: "energy", icon: BarChart3 },
  { label: "Automation", view: "automation", icon: CalendarClock },
  { label: "Rooms", view: "rooms", icon: MapPin },
];

export function DesktopSidebar({
  view,
  onNavigate,
  overview,
}: WorkspaceProps & { overview: Overview }) {
  const online = overview.summary.online_strips;
  const strips = overview.strips.filter(
    (strip) => strip.managed && (strip.state === "active" || strip.state === "disabled"),
  );

  return (
    <aside className="dw-sidebar" aria-label="Desktop navigation">
      <div className="dw-brand">
        <div className="dw-logo"><Zap size={25} strokeWidth={2.5} /></div>
        <div className="dw-brand-type"><strong>VOLTRA</strong><span>SMART POWER SYSTEM</span></div>
      </div>

      <div className="dw-nav-overline">WORKSPACE</div>
      <nav className="dw-primary-nav" aria-label="Workspace pages">
        {navigation.map(({ view: target, label, icon: Icon }) => (
          <button
            key={target}
            type="button"
            className={view === target ? "active" : ""}
            aria-current={view === target ? "page" : undefined}
            onClick={() => onNavigate(target)}
          >
            <Icon size={19} strokeWidth={1.8} />
            <span>{label}</span>
            {view === target && <span className="dw-nav-active-indicator" aria-hidden="true" />}
          </button>
        ))}
      </nav>

      <div className="dw-nav-overline dw-nav-overline-second">MANAGEMENT</div>
      <nav className="dw-primary-nav" aria-label="Device management">
        <button type="button" className={view === "add" ? "active" : ""} onClick={() => onNavigate("add")} aria-current={view === "add" ? "page" : undefined}>
          <CirclePlus size={19} strokeWidth={1.8} /><span>Add strip</span>
        </button>
        <button type="button" className={view === "settings" ? "active" : ""} onClick={() => onNavigate("settings")} aria-current={view === "settings" ? "page" : undefined}>
          <Settings size={19} strokeWidth={1.8} /><span>Settings</span>
        </button>
      </nav>

      <div className="dw-sidebar-spacer" />
      <div className="dw-side-status">
        <div className="dw-side-status-header">
          <span className="dw-side-icon"><Server size={17} /></span>
          <span>VOLTRA LOCAL</span>
          <span className="dw-side-status-dot" aria-hidden="true" />
        </div>
        <strong>{online} of {strips.length} strips online</strong>
        <small>Local server · v{overview.version}</small>
      </div>
      <div className="dw-side-foot">LOCAL CONTROL · NO CLOUD REQUIRED</div>
    </aside>
  );
}

export function DesktopHeader({
  view,
  onRefresh,
  onSettings,
  busy,
}: {
  view: ViewName;
  onRefresh: () => void;
  onSettings: () => void;
  busy: boolean;
}) {
  return (
    <header className="dw-topbar">
      <div>
        <div className="dw-breadcrumb"><span>WORKSPACE</span><span className="dw-breadcrumb-slash">/</span><strong>{viewMeta[view].title}</strong></div>
        <h1>{view === "dashboard" ? "My strips" : viewMeta[view].title}</h1>
        <p>{view === "dashboard" ? "Your smart home, connected and in control." : "Manage your Voltra local smart power system."}</p>
      </div>
      <div className="dw-topbar-actions">
        <span className="dw-local-pill"><span /> LOCAL SYSTEM</span>
        <button className="dw-toolbar-btn" onClick={onRefresh} aria-label="Refresh dashboard" title="Refresh" disabled={busy}>
          <RefreshCw size={19} className={busy ? "spin" : ""} />
        </button>
        <button className="dw-toolbar-btn" onClick={onSettings} aria-label="Open settings" title="Settings">
          <Settings size={19} />
        </button>
        <span className="dw-avatar" aria-label="Voltra Local">VL</span>
      </div>
    </header>
  );
}

type DashboardProps = {
  overview: Overview;
  automation: AutomationSnapshot;
  search: string;
  onSearch: (value: string) => void;
  busyChannels: Set<string>;
  onNavigate: (view: ViewName) => void;
  onToggleOutlet: (strip: Strip, outlet: number, on: boolean) => void;
  onSetAll: (strip: Strip, on: boolean) => void;
  onStripSettings: (strip: Strip) => void;
};

type DeviceFilter = "all" | "online" | "offline";

export function DesktopDashboard({
  overview,
  automation,
  search,
  onSearch,
  busyChannels,
  onNavigate,
  onToggleOutlet,
  onSetAll,
  onStripSettings,
}: DashboardProps) {
  const [filter, setFilter] = useState<DeviceFilter>("all");
  const strips = overview.strips.filter(
    (strip) => strip.managed && (strip.state === "active" || strip.state === "disabled"),
  );
  const totalOutlets = strips.length * 4;
  const activeOutlets = strips.flatMap((strip) => strip.outlets || []).filter((outlet) => outlet.relay).length;
  const onlineCount = strips.filter((strip) => strip.online && strip.enabled && strip.state === "active").length;
  const schedules = Object.values(automation.schedules || {}).filter((schedule) => schedule.enabled !== false).length;
  const normalized = search.trim().toLocaleLowerCase();
  const matches = strips.filter((strip) => {
    if (filter === "online" && !strip.online) return false;
    if (filter === "offline" && strip.online) return false;
    if (!normalized) return true;
    const mappedNames = Object.entries(overview.mappings)
      .filter(([, mapping]) => mapping.mac === strip.mac)
      .map(([id]) => overview.ps4_devices.find((device) => String(device.id) === id)?.name || id);
    return [strip.name, strip.mac, strip.room, ...mappedNames]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase()
      .includes(normalized);
  });
  const hasAttention = strips.some((strip) => !strip.online || !strip.enabled || strip.health?.status === "critical");
  const searching = Boolean(normalized) || filter !== "all";

  return (
    <div className="dw-dashboard">
      <section className="dw-welcome" aria-label="Dashboard introduction">
        <div>
          <span className="dw-eyebrow"><span className="dw-eyebrow-dot" /> REAL-TIME OVERVIEW</span>
          <h2>Power at a glance<span className="dw-title-period">.</span></h2>
          <p>Monitor energy, manage outlets, and keep every room running smoothly.</p>
        </div>
        <span className={"dw-health-label " + (hasAttention ? "attention" : "")}>
          {hasAttention ? <WifiOff size={15} /> : <ShieldCheck size={15} />}
          {strips.length === 0 ? "No devices configured" : hasAttention ? "Devices need attention" : "All managed devices connected"}
        </span>
      </section>

      <section className="dw-overview" aria-label="Power and connectivity overview">
        <div className="dw-hero">
          <div className="dw-hero-top">
            <span>LIVE POWER CONSUMPTION</span>
            <span className="dw-hero-live"><span /> LIVE</span>
          </div>
          <div className="dw-hero-inner">
            <div>
              <div className="dw-hero-number">
                <strong>{Number(overview.summary.total_power_w || 0).toFixed(1)}</strong>
                <span>W</span>
              </div>
              <span className="dw-hero-caption">Total power right now</span>
            </div>
            <div className="dw-energy-symbol" aria-hidden="true"><Zap size={51} strokeWidth={1.35} /></div>
          </div>
          <div className="dw-hero-footer">
            <span><Activity size={15} /> Real-time device telemetry</span>
            <span>{onlineCount} active strips reporting</span>
          </div>
        </div>

        <div className="dw-stat-grid">
          <div className="dw-stat-card">
            <span className="dw-stat-icon green"><Wifi size={20} /></span>
            <span className="dw-stat-label">Online strips</span>
            <div><strong>{overview.summary.online_strips}</strong><span>/ {strips.length}</span></div>
            <small>Connected to Voltra</small>
          </div>
          <div className="dw-stat-card">
            <span className="dw-stat-icon blue"><PlugZap size={20} /></span>
            <span className="dw-stat-label">Active outlets</span>
            <div><strong>{activeOutlets}</strong><span>/ {totalOutlets}</span></div>
            <small>Currently powered on</small>
          </div>
          <div className="dw-stat-card">
            <span className="dw-stat-icon amber"><CalendarClock size={20} /></span>
            <span className="dw-stat-label">Active schedules</span>
            <div><strong>{schedules}</strong></div>
            <small>Automation plans enabled</small>
          </div>
        </div>
      </section>

      <section className="dw-shortcuts" aria-label="Quick actions">
        <div className="dw-mini-heading"><span>QUICK ACCESS</span><small>Everything you need, one click away</small></div>
        <div className="dw-shortcut-grid">
          {[
            { view: "energy" as ViewName, label: "Consumption", hint: "Power insights", icon: BarChart3 },
            { view: "automation" as ViewName, label: "Schedules", hint: "Timed actions", icon: CalendarClock },
            { view: "automation" as ViewName, label: "Power automation", hint: "Smart rules", icon: SlidersHorizontal },
            { view: "rooms" as ViewName, label: "Rooms", hint: "Organize devices", icon: MapPin },
          ].map(({ view, label, hint, icon: Icon }) => (
            <button className="dw-shortcut" key={label} onClick={() => onNavigate(view)}>
              <span className="dw-shortcut-icon"><Icon size={21} strokeWidth={1.8} /></span>
              <span className="dw-shortcut-text"><strong>{label}</strong><small>{hint}</small></span>
              <ArrowUpRight size={16} className="dw-shortcut-arrow" />
            </button>
          ))}
        </div>
      </section>

      <section className="dw-devices" aria-label="Connected strips">
        <div className="dw-device-title-row">
          <div>
            <span className="dw-eyebrow">DEVICE MANAGEMENT</span>
            <h2>Your strips <span className="dw-device-count">{strips.length}</span></h2>
            <p>Control and monitor all your connected power strips.</p>
          </div>
          <button className="dw-add-button" onClick={() => onNavigate("add")}>
            <CirclePlus size={19} /> Add strip
          </button>
        </div>

        <div className="dw-device-toolbar">
          <div className="dw-filters" role="group" aria-label="Filter devices by connection">
            {(["all", "online", "offline"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={filter === option}
                className={filter === option ? "selected" : ""}
                onClick={() => setFilter(option)}
              >
                {option === "all" ? "All devices" : option === "online" ? "Online" : "Offline"}
              </button>
            ))}
          </div>
          <div className="dw-search"><SearchBar value={search} onChange={onSearch} /></div>
          <span className="dw-result-count">{matches.length} showing</span>
        </div>

        <div className="dw-device-grid">
          {matches.map((strip) => (
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
          {matches.length === 0 && (
            <div className="dw-empty">
              <EmptyState
                icon={Search}
                title={searching ? "No matching devices" : strips.length ? "No matching devices" : "No strips yet"}
                description={searching || strips.length ? "Try another search or connection filter." : "Add your first MTTL-W01 strip to start monitoring."}
                action={!strips.length && !searching ? (
                  <button className="dw-add-button" onClick={() => onNavigate("add")}>
                    <CirclePlus size={17} /> Add strip
                  </button>
                ) : undefined}
              />
            </div>
          )}
        </div>
      </section>
      <footer className="dw-footer"><span>© VOLTRA LOCAL · SMART POWER CONTROL</span><span><Gauge size={14} /> LOCAL SERVER v{overview.version}</span></footer>
    </div>
  );
}
