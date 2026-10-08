import type {
  AutomationSnapshot,
  EnergyHistory,
  EnergySummary,
  Overview,
  Settings,
} from "./types";

const API = "/voltra/api";
const TOKEN_KEY = "voltra.api.token";

export class AuthError extends Error {
  constructor(message = "Authentication required") {
    super(message);
    this.name = "AuthError";
  }
}

export function getApiToken(): string {
  return window.sessionStorage.getItem(TOKEN_KEY) || "";
}

export function setApiToken(value: string): void {
  const token = value.trim();
  if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
  else window.sessionStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (init?.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  const token = getApiToken();
  if (token) headers.set("authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  const text = await response.text();
  let payload: unknown = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: text || response.statusText };
  }
  if (response.status === 401) {
    throw new AuthError("Authentication required or access token is invalid.");
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

export function subscribeEvents(
  onEvent: () => void,
  onUnauthorized?: () => void,
): () => void {
  const controller = new AbortController();

  const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

  const run = async () => {
    while (!controller.signal.aborted) {
      try {
        const headers = new Headers();
        const token = getApiToken();
        if (token) headers.set("authorization", `Bearer ${token}`);

        const response = await fetch(`${API}/events`, {
          headers,
          signal: controller.signal,
          cache: "no-store",
        });
        if (response.status === 401) {
          onUnauthorized?.();
          return;
        }
        if (!response.ok || !response.body) {
          throw new Error(`Event stream failed (${response.status}).`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let splitAt = buffer.indexOf("\n\n");
          while (splitAt >= 0) {
            const packet = buffer.slice(0, splitAt);
            buffer = buffer.slice(splitAt + 2);
            if (packet.split("\n").some((line) => line.startsWith("data:"))) {
              onEvent();
            }
            splitAt = buffer.indexOf("\n\n");
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        await sleep(2000);
      }
    }
  };

  void run();
  return () => controller.abort();
}
