export type ViewName =
  | "dashboard"
  | "energy"
  | "automation"
  | "rooms"
  | "add"
  | "settings";

export type Outlet = {
  channel: number;
  relay?: boolean | null;
  power_w?: number | null;
  energy_kwh?: number | null;
};

export type Health = {
  score: number;
  status: string;
  reasons: string[];
};

export type Strip = {
  mac: string;
  name: string;
  online: boolean;
  managed: boolean;
  enabled: boolean;
  state: string;
  model?: string | null;
  firmware_version?: string | null;
  last_ip?: string | null;
  last_seen_at?: string | null;
  voltage_v?: number | null;
  wifi_rssi_dbm?: number | null;
  health?: Health;
  outlets: Outlet[];
  mapped_count?: number;
  total_power_w?: number;
  room?: string;
  favorite?: boolean;
  sort_order?: number;
};

export type Ps4Device = {
  id: string;
  name: string;
};

export type Mapping = {
  ps4_id?: string;
  mac: string;
  outlet: number;
  updated_at?: string;
};

export type Scene = {
  id: string;
  name: string;
  actions: Array<{ mac: string; outlet: number; on: boolean }>;
};

export type Overview = {
  version: string;
  mode: "demo" | "real";
  strips: Strip[];
  ps4_devices: Ps4Device[];
  mappings: Record<string, Mapping>;
  scenes: Scene[];
  settings: Settings;
  summary: {
    active_strips: number;
    online_strips: number;
    pending_strips: number;
    mapped_devices: number;
    total_power_w: number;
  };
};

export type Settings = {
  energy_price_per_kwh: number;
  currency: string;
  weak_wifi_dbm: number;
  voltage_min_v: number;
  voltage_max_v: number;
  unusual_power_w: number;
};

export type Schedule = {
  id: string;
  mac: string;
  outlet: number;
  on: boolean;
  type?: "once" | "recurring";
  time?: string | null;
  days?: number[];
  run_at?: string | null;
  enabled?: boolean;
  offline_policy?: "queue" | "skip";
  created_at?: string;
  last_run_at?: string | null;
};

export type Rule = {
  id: string;
  mac: string;
  outlet?: number | null;
  condition: "offline" | "weak_wifi" | "low_power" | "voltage_below" | "voltage_above";
  threshold?: number | null;
  duration_s?: number;
  cooldown_s?: number;
  action?: {
    type: "audit" | "set_outlet";
    outlet?: number;
    on?: boolean;
  };
  enabled?: boolean;
};

export type AutomationSnapshot = {
  schedules: Record<string, Schedule>;
  rules: Record<string, Rule>;
  queue: Array<Record<string, unknown>>;
};

export type EnergySummary = {
  mac: string;
  hours: number;
  outlet?: number | null;
  samples: number;
  energy_kwh: number;
  average_power_w: number;
  max_power_w: number;
};

export type EnergyPoint = {
  at: string;
  power_w: number;
  energy_kwh: number;
  voltage_v?: number | null;
  wifi_rssi_dbm?: number | null;
};

export type EnergyHistory = {
  mac: string;
  hours: number;
  outlet?: number | null;
  samples: number;
  points: EnergyPoint[];
};
