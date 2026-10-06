import type {
  AutomationSnapshot,
  EnergyHistory,
  EnergySummary,
  Overview,
  Settings,
} from "./types";

const API = "/voltra/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (init?.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  const text = await response.text();
  let payload: unknown = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: text || response.statusText };
  }
  if (!response.ok) {
    const message =
      typeof payload === "object" && payload && "error" in payload
        ? String((payload as { error: unknown }).error)
        : response.statusText;
    throw new Error(message);
  }
  return payload as T;
}

export const api = {
  overview: () => request<Overview>(`${API}/overview`),
  automation: () => request<AutomationSnapshot>(`${API}/automation`),
  settings: () => request<Settings>(`${API}/settings`),

  setOutlet: (mac: string, outlet: number, on: boolean) =>
    request(`${API}/strips/${encodeURIComponent(mac)}/outlets/${outlet}/state`, {
      method: "POST",
      body: JSON.stringify({ on }),
    }),

  adoptStrip: (mac: string, name: string) =>
    request(`${API}/strips/${encodeURIComponent(mac)}/adopt`, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),

  ignoreStrip: (mac: string) =>
    request(`${API}/strips/${encodeURIComponent(mac)}/ignore`, {
      method: "POST",
      body: "{}",
    }),

  renameStrip: (mac: string, name: string) =>
    request(`${API}/strips/${encodeURIComponent(mac)}`, {
      method: "PUT",
      body: JSON.stringify({ name }),
    }),

  stripPreferences: (
    mac: string,
    value: { room?: string; favorite?: boolean; sort_order?: number },
  ) =>
    request(`${API}/strips/${encodeURIComponent(mac)}/preferences`, {
      method: "PUT",
      body: JSON.stringify(value),
    }),

  setStripEnabled: (mac: string, enabled: boolean) =>
    request(`${API}/strips/${encodeURIComponent(mac)}/enabled`, {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),

  removeStrip: (mac: string) =>
    request(`${API}/strips/${encodeURIComponent(mac)}`, { method: "DELETE" }),

  provision: (value: {
    ssid: string;
    password: string;
    server_ip: string;
    device_ip?: string;
  }) =>
    request(`${API}/provision`, {
      method: "POST",
      body: JSON.stringify(value),
    }),

  createSchedule: (value: Record<string, unknown>) =>
    request(`${API}/schedules`, {
      method: "POST",
      body: JSON.stringify(value),
    }),

  createCountdown: (value: Record<string, unknown>) =>
    request(`${API}/countdown`, {
      method: "POST",
      body: JSON.stringify(value),
    }),

  deleteSchedule: (id: string) =>
    request(`${API}/schedules/${encodeURIComponent(id)}`, { method: "DELETE" }),

  createRule: (value: Record<string, unknown>) =>
    request(`${API}/rules`, {
      method: "POST",
      body: JSON.stringify(value),
    }),

  deleteRule: (id: string) =>
    request(`${API}/rules/${encodeURIComponent(id)}`, { method: "DELETE" }),

  clearQueue: () => request(`${API}/queue`, { method: "DELETE" }),

  setMapping: (deviceId: string, mac: string, outlet: number) =>
    request(`${API}/ps4/${encodeURIComponent(deviceId)}/power-mapping`, {
      method: "PUT",
      body: JSON.stringify({ mac, outlet }),
    }),

  clearMapping: (deviceId: string) =>
    request(`${API}/ps4/${encodeURIComponent(deviceId)}/power-mapping`, {
      method: "DELETE",
    }),

  runScene: (sceneId: string) =>
    request(`${API}/scenes/${encodeURIComponent(sceneId)}/run`, {
      method: "POST",
      body: "{}",
    }),

  energySummary: (mac: string, hours: number, outlet?: number | null) => {
    const qs = new URLSearchParams({ mac, hours: String(hours) });
    if (outlet) qs.set("outlet", String(outlet));
    return request<EnergySummary>(`${API}/energy?${qs}`);
  },

  energyHistory: (mac: string, hours: number, outlet?: number | null) => {
    const qs = new URLSearchParams({ mac, hours: String(hours), limit: "120" });
    if (outlet) qs.set("outlet", String(outlet));
    return request<EnergyHistory>(`${API}/energy/history?${qs}`);
  },

  updateSettings: (value: Partial<Settings>) =>
    request<Settings>(`${API}/settings`, {
      method: "PUT",
      body: JSON.stringify(value),
    }),

  backup: () => request<Record<string, unknown>>(`${API}/backup`),

  restore: (value: Record<string, unknown>) =>
    request(`${API}/restore`, {
      method: "POST",
      body: JSON.stringify(value),
    }),
};

export function subscribeEvents(onEvent: () => void): () => void {
  const source = new EventSource(`${API}/events`);
  const handler = () => onEvent();
  source.onmessage = handler;
  const eventNames = [
    "device_state",
    "device_online",
    "device_offline",
    "physical_onoff",
    "outlet_command",
    "schedule_created",
    "schedule_deleted",
    "queued_command_executed",
    "rule_fired",
    "scene_run",
    "restore_completed",
  ];
  eventNames.forEach((name) => source.addEventListener(name, handler));
  return () => source.close();
}
