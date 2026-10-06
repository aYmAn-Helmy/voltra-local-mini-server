import type { ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Bolt,
  CalendarClock,
  ChevronLeft,
  CirclePlus,
  Clock3,
  Gauge,
  Home,
  MapPin,
  MoreVertical,
  PlugZap,
  RefreshCw,
  Search,
  Settings,
  SlidersHorizontal,
  Sparkles,
  Wifi,
  X,
  Zap,
} from "lucide-react";

import type { EnergyPoint, Mapping, Outlet, Ps4Device, Strip, ViewName } from "./types";

export const viewMeta: Record<ViewName, { title: string; icon: typeof Home }> = {
  dashboard: { title: "My strips", icon: Home },
  energy: { title: "Consumption", icon: BarChart3 },
  automation: { title: "Automation", icon: CalendarClock },
  rooms: { title: "Rooms", icon: MapPin },
  add: { title: "Add strip", icon: CirclePlus },
  settings: { title: "Settings", icon: Settings },
};

export function AppHeader({
  view,
  onBack,
  onRefresh,
  onSettings,
  busy,
}: {
  view: ViewName;
  onBack: () => void;
  onRefresh: () => void;
  onSettings: () => void;
  busy: boolean;
}) {
  const home = view === "dashboard";
  return (
    <header className="app-header">
      <div className="title-stack">
        <div className="live-label"><span /> VOLTRA LIVE</div>
        <div className="title-row">
          {!home && (
            <button className="icon-button subtle" onClick={onBack} aria-label="Back to My strips">
              <ChevronLeft size={20} />
            </button>
          )}
          <h1>{viewMeta[view].title}</h1>
        </div>
      </div>
      <div className="header-actions">
        <button className="icon-button" onClick={onRefresh} aria-label="Refresh" disabled={busy}>
          <RefreshCw size={18} className={busy ? "spin" : ""} />
        </button>
        <button className="icon-button" onClick={onSettings} aria-label="Settings">
          <Settings size={18} />
        </button>
      </div>
    </header>
  );
}

export function BottomNav({
  view,
  onChange,
}: {
  view: ViewName;
  onChange: (view: ViewName) => void;
}) {
  const entries: ViewName[] = ["dashboard", "energy", "automation", "rooms"];
  return (
    <nav className="bottom-nav" aria-label="Primary">
      {entries.map((name) => {
        const meta = viewMeta[name];
        const Icon = meta.icon;
        return (
          <button
            key={name}
            className={view === name ? "active" : ""}
            onClick={() => onChange(name)}
            aria-label={meta.title}
          >
            <Icon size={19} />
            <span>{meta.title}</span>
          </button>
        );
      })}
    </nav>
  );
}

export function QuickActions({ onOpen }: { onOpen: (view: ViewName) => void }) {
  const actions = [
    { view: "energy" as ViewName, label: "Consumption", icon: Activity },
    { view: "automation" as ViewName, label: "Schedules", icon: Clock3 },
    { view: "automation" as ViewName, label: "Power automation", icon: Bolt },
    { view: "rooms" as ViewName, label: "Rooms", icon: MapPin },
  ];
  return (
    <section className="quick-grid" aria-label="Quick actions">
      {actions.map(({ view, label, icon: Icon }) => (
        <button key={label} className="quick-card" onClick={() => onOpen(view)} aria-label={label}>
          <span className="quick-icon"><Icon size={19} /></span>
          <span>{label}</span>
        </button>
      ))}
    </section>
  );
}

export function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="search-box">
      <Search size={18} />
      <input
        aria-label="Search strips and outlets"
        placeholder="Search strips and outlets"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
  footer,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="eyebrow">VOLTRA</span>
            <h2>{title}</h2>
          </div>
          <button className="icon-button subtle" onClick={onClose} aria-label="Close">
            <X size={19} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </section>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  danger,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      open={open}
      title={title}
      onClose={onClose}
      footer={
        <>
          <button className="button secondary" onClick={onClose}>Cancel</button>
          <button className={`button ${danger ? "danger" : "primary"}`} onClick={onConfirm}>{confirmLabel}</button>
        </>
      }
    >
      <p className="dialog-message">{message}</p>
    </Modal>
  );
}

function mappingName(
  mac: string,
  channel: number,
  mappings: Record<string, Mapping>,
  devices: Ps4Device[],
) {
  const found = Object.entries(mappings).find(([, value]) => value.mac === mac && Number(value.outlet) === channel);
  if (!found) return `Outlet ${channel}`;
  const device = devices.find((item) => String(item.id) === String(found[0]));
  return device?.name || found[0];
}

function OutletTile({
  strip,
  outlet,
  label,
  onToggle,
  busy,
}: {
  strip: Strip;
  outlet: Outlet | undefined;
  label: string;
  onToggle: () => void;
  busy: boolean;
}) {
  const on = Boolean(outlet?.relay);
  const canControl = strip.online && strip.enabled && strip.state === "active" && !busy;
  return (
    <button
      className={`outlet-tile ${on ? "on" : ""}`}
      disabled={!canControl}
      onClick={onToggle}
      aria-label={`${label}: ${on ? "on" : "off"}`}
    >
      <span className="outlet-icon"><PlugZap size={17} /></span>
      <span className="outlet-name" dir="auto">{label}</span>
      <span className="outlet-state">{on ? "ON" : "OFF"}</span>
      <span className="outlet-power">{on ? `${Number(outlet?.power_w || 0).toFixed(1)} W` : " "}</span>
    </button>
  );
}

export function StripCard({
  strip,
  mappings,
  devices,
  busyChannels,
  onToggle,
  onSetAll,
  onSettings,
}: {
  strip: Strip;
  mappings: Record<string, Mapping>;
  devices: Ps4Device[];
  busyChannels: Set<string>;
  onToggle: (outlet: number, on: boolean) => void;
  onSetAll: (on: boolean) => void;
  onSettings: () => void;
}) {
  const canControl = strip.online && strip.enabled && strip.state === "active";
  const status = strip.state === "disabled" ? "DISABLED" : strip.online ? "ONLINE" : "OFFLINE";
  const health = strip.health?.status?.replaceAll("_", " ") || "unknown";
  return (
    <article className={`strip-card ${strip.online ? "" : "offline"}`}>
      <div className="strip-head">
        <span className="status-dot" />
        <div className="strip-title" dir="auto">{strip.name}</div>
        <span className={`status-pill ${strip.online ? "" : "offline"}`}>{status}</span>
        <button className="strip-menu" onClick={onSettings} aria-label={`Settings for ${strip.name}`}>
          <MoreVertical size={18} />
        </button>
      </div>

      <div className="strip-meta">
        <span>{strip.room || "Local strip"} · {health}</span>
        <strong>{Number(strip.total_power_w || 0).toFixed(1)} W</strong>
      </div>

      <div className="outlet-grid">
        {[1, 2, 3, 4].map((channel) => {
          const outlet = strip.outlets?.find((item) => Number(item.channel) === channel);
          const label = mappingName(strip.mac, channel, mappings, devices);
          return (
            <OutletTile
              key={channel}
              strip={strip}
              outlet={outlet}
              label={label}
              busy={busyChannels.has(`${strip.mac}:${channel}`)}
              onToggle={() => onToggle(channel, !Boolean(outlet?.relay))}
            />
          );
        })}
      </div>

      <div className="bulk-grid">
        <button className="button soft-green" disabled={!canControl} onClick={() => onSetAll(true)}>
          Turn all on
        </button>
        <button className="button secondary" disabled={!canControl} onClick={() => onSetAll(false)}>
          Turn all off
        </button>
      </div>

      <div className="diagnostic-row">
        <span><Gauge size={13} /> {strip.voltage_v == null ? "—" : `${Number(strip.voltage_v).toFixed(1)} V`}</span>
        <span><Wifi size={13} /> {strip.wifi_rssi_dbm == null ? "—" : `${strip.wifi_rssi_dbm} dBm`}</span>
        <span><Sparkles size={13} /> {strip.health?.score ?? "—"}%</span>
      </div>
    </article>
  );
}

export function EmptyState({
  icon: Icon = Zap,
  title,
  description,
  action,
}: {
  icon?: typeof Zap;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <section className="empty-state">
      <span className="empty-icon"><Icon size={24} /></span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </section>
  );
}

export function EnergyChart({ points }: { points: EnergyPoint[] }) {
  const width = 680;
  const height = 220;
  const pad = 14;
  if (!points.length) {
    return <div className="chart-empty">No samples in this period yet.</div>;
  }
  const max = Math.max(1, ...points.map((point) => Number(point.power_w || 0)));
  const coords = points.map((point, index) => {
    const x = pad + (index / Math.max(1, points.length - 1)) * (width - pad * 2);
    const y = height - pad - (Number(point.power_w || 0) / max) * (height - pad * 2);
    return [x, y] as const;
  });
  const line = coords.map(([x, y]) => `${x},${y}`).join(" ");
  const area = [
    `${coords[0][0]},${height - pad}`,
    ...coords.map(([x, y]) => `${x},${y}`),
    `${coords[coords.length - 1][0]},${height - pad}`,
  ].join(" ");

  return (
    <div className="chart-shell" aria-label="Power history chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <defs>
          <linearGradient id="powerFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity=".28" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={area} fill="url(#powerFill)" />
        <polyline points={line} fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="chart-legend">
        <span>0 W</span>
        <strong>Peak {max.toFixed(1)} W</strong>
      </div>
    </div>
  );
}

export function MetricCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className={`metric-card ${accent ? "accent" : ""}`}>
      <span className="metric-icon"><Icon size={16} /></span>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export const Icons = {
  Activity,
  BarChart3,
  Bolt,
  CalendarClock,
  CirclePlus,
  Clock3,
  Gauge,
  Home,
  MapPin,
  Settings,
  SlidersHorizontal,
  Wifi,
  Zap,
};
