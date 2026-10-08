import { useCallback, useEffect, useRef, useState } from "react";
import { CirclePlus, LoaderCircle, Star, Trash2 } from "lucide-react";

import { AuthError, api, getApiToken, setApiToken, subscribeEvents } from "./api";
import { AddStripView, AutomationView, DashboardView, EnergyView, RoomsView, SettingsView } from "./views";
import { AppHeader, BottomNav, ConfirmDialog, Modal } from "./ui";
import type { AutomationSnapshot, Overview, Strip, ViewName } from "./types";

const emptyAutomation: AutomationSnapshot = { schedules: {}, rules: {}, queue: [] };

type ConfirmState = {
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  action: () => Promise<void> | void;
} | null;

function updateOutletLocal(overview: Overview, mac: string, outlet: number, on: boolean): Overview {
  return {
    ...overview,
    strips: overview.strips.map((strip) => {
      if (strip.mac !== mac) return strip;
      const nextOutlets = [1, 2, 3, 4].map((channel) => {
        const current = strip.outlets?.find((item) => Number(item.channel) === channel) || { channel };
        return channel === outlet ? { ...current, relay: on } : current;
      });
      return { ...strip, outlets: nextOutlets };
    }),
  };
}

export default function App() {
  const [view, setView] = useState<ViewName>("dashboard");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [automation, setAutomation] = useState<AutomationSnapshot>(emptyAutomation);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyChannels, setBusyChannels] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);
  const [editingStrip, setEditingStrip] = useState<Strip | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [tokenDraft, setTokenDraft] = useState(() => getApiToken());
  const [stripDraft, setStripDraft] = useState({ name: "", room: "", favorite: false, enabled: true });
  const refreshTimer = useRef<number | null>(null);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast((current) => (current?.message === message ? null : current)), 3600);
  }, []);

  const refreshOverview = useCallback(async () => {
    try {
      const next = await api.overview();
      setOverview(next);
      setAuthRequired(false);
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthRequired(true);
        return;
      }
      throw error;
    }
  }, []);

  const refreshAutomation = useCallback(async () => {
    try {
      const next = await api.automation();
      setAutomation(next);
      setAuthRequired(false);
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthRequired(true);
        return;
      }
      throw error;
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setLoading((current) => current || !overview);
    try {
      const [nextOverview, nextAutomation] = await Promise.all([api.overview(), api.automation()]);
      setOverview(nextOverview);
      setAutomation(nextAutomation);
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthRequired(true);
      } else {
        notify(error instanceof Error ? error.message : String(error), true);
      }
    } finally {
      setLoading(false);
    }
  }, [notify, overview]);

  useEffect(() => {
    refreshAll();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeEvents(
      () => {
        if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
        refreshTimer.current = window.setTimeout(() => {
          refreshAll();
        }, 180);
      },
      () => setAuthRequired(true),
    );
    const fallback = window.setInterval(refreshOverview, 15_000);
    return () => {
      unsubscribe();
      window.clearInterval(fallback);
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };
  }, [refreshAll, refreshOverview]);

  useEffect(() => {
    if (!editingStrip) return;
    setStripDraft({
      name: editingStrip.name || "",
      room: editingStrip.room || "",
      favorite: Boolean(editingStrip.favorite),
      enabled: Boolean(editingStrip.enabled),
    });
  }, [editingStrip]);

  async function setOutlet(strip: Strip, outlet: number, on: boolean) {
    const key = `${strip.mac}:${outlet}`;
    if (busyChannels.has(key)) return;
    setBusyChannels((current) => new Set(current).add(key));
    setOverview((current) => (current ? updateOutletLocal(current, strip.mac, outlet, on) : current));
    try {
      await api.setOutlet(strip.mac, outlet, on);
      await refreshOverview();
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
      await refreshOverview();
    } finally {
      setBusyChannels((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  }

  function requestSetAll(strip: Strip, on: boolean) {
    setConfirm({
      title: on ? "Turn all outlets on?" : "Turn all outlets off?",
      message: `${strip.name} will switch all four outlets ${on ? "on" : "off"}. Commands are sent and verified one outlet at a time.`,
      confirmLabel: on ? "Turn all on" : "Turn all off",
      danger: !on,
      action: async () => {
        for (const channel of [1, 2, 3, 4]) {
          const current = strip.outlets?.find((item) => Number(item.channel) === channel);
          if (Boolean(current?.relay) === on) continue;
          await setOutlet(strip, channel, on);
        }
        notify(on ? "All outlets are on." : "All outlets are off.");
      },
    });
  }

  async function saveStripSettings() {
    if (!editingStrip) return;
    try {
      const original = editingStrip;
      if (stripDraft.name.trim() && stripDraft.name.trim() !== original.name) {
        await api.renameStrip(original.mac, stripDraft.name.trim());
      }
      if (
        stripDraft.room !== (original.room || "") ||
        stripDraft.favorite !== Boolean(original.favorite)
      ) {
        await api.stripPreferences(original.mac, {
          room: stripDraft.room,
          favorite: stripDraft.favorite,
        });
      }
      if (stripDraft.enabled !== Boolean(original.enabled)) {
        await api.setStripEnabled(original.mac, stripDraft.enabled);
      }
      setEditingStrip(null);
      await refreshOverview();
      notify("Strip settings saved.");
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
    }
  }

  function requestRemoveStrip(strip: Strip) {
    setConfirm({
      title: "Remove this strip?",
      message: `${strip.name} will be removed from active control and any PlayStation mappings to it will be cleared. The historical record is kept to avoid accidental rediscovery.`,
      confirmLabel: "Remove strip",
      danger: true,
      action: async () => {
        await api.removeStrip(strip.mac);
        setEditingStrip(null);
        await refreshOverview();
        notify("Strip removed.");
      },
    });
  }

  if (authRequired) {
    return (
      <div className="boot-screen">
        <span className="boot-mark">V</span>
        <strong>Voltra authentication</strong>
        <small>Enter the access token configured on your Voltra server. The token is kept only in this browser session.</small>
        <div className="settings-form" style={{ width: "min(420px, 92vw)" }}>
          <label>
            <span>Access token</span>
            <input
              type="password"
              autoComplete="off"
              value={tokenDraft}
              onChange={(event) => setTokenDraft(event.target.value)}
              placeholder="Paste Voltra access token"
            />
          </label>
        </div>
        <div className="boot-actions">
          <button
            className="button primary"
            onClick={() => {
              setApiToken(tokenDraft);
              setAuthRequired(false);
              setLoading(true);
              void refreshAll();
            }}
            disabled={!tokenDraft.trim()}
          >
            Connect securely
          </button>
          {getApiToken() && (
            <button
              className="button secondary"
              onClick={() => {
                setApiToken("");
                setTokenDraft("");
              }}
            >
              Clear saved session token
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!overview && loading) {
    return (
      <div className="boot-screen">
        <span className="boot-mark">V</span>
        <LoaderCircle className="spin" size={24} />
        <strong>Starting Voltra</strong>
        <small>Loading local device state…</small>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="boot-screen">
        <span className="boot-mark error">!</span>
        <strong>Voltra UI could not load</strong>
        <small>Open the legacy console or retry the local API.</small>
        <div className="boot-actions">
          <button className="button primary" onClick={refreshAll}>Retry</button>
          <a className="button secondary" href="/voltra/legacy">Legacy console</a>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="app-frame">
        <AppHeader
          view={view}
          onBack={() => setView("dashboard")}
          onRefresh={refreshAll}
          onSettings={() => setView("settings")}
          busy={loading}
        />

        <main className="main-content">
          {view === "dashboard" && (
            <DashboardView
              overview={overview}
              automation={automation}
              search={search}
              onSearch={setSearch}
              busyChannels={busyChannels}
              onNavigate={setView}
              onToggleOutlet={setOutlet}
              onSetAll={requestSetAll}
              onStripSettings={setEditingStrip}
            />
          )}
          {view === "energy" && <EnergyView overview={overview} notify={notify} />}
          {view === "automation" && (
            <AutomationView
              overview={overview}
              automation={automation}
              reload={refreshAutomation}
              notify={notify}
            />
          )}
          {view === "rooms" && <RoomsView overview={overview} refresh={refreshOverview} notify={notify} />}
          {view === "add" && <AddStripView overview={overview} refresh={refreshOverview} notify={notify} />}
          {view === "settings" && <SettingsView overview={overview} refresh={refreshOverview} notify={notify} />}
        </main>

        <BottomNav view={view} onChange={setView} />
      </div>

      <Modal
        open={Boolean(editingStrip)}
        title={editingStrip?.name || "Strip settings"}
        onClose={() => setEditingStrip(null)}
        footer={
          <>
            <button className="button secondary" onClick={() => setEditingStrip(null)}>Cancel</button>
            <button className="button primary" onClick={saveStripSettings}>Save changes</button>
          </>
        }
      >
        {editingStrip && (
          <div className="settings-form">
            <label><span>Strip name</span><input value={stripDraft.name} onChange={(e) => setStripDraft({ ...stripDraft, name: e.target.value })} /></label>
            <label><span>Room</span><input placeholder="Living Room" value={stripDraft.room} onChange={(e) => setStripDraft({ ...stripDraft, room: e.target.value })} /></label>
            <div className="toggle-row">
              <span><Star size={17} /><span><strong>Favorite</strong><small>Keep this strip prominent in future layouts.</small></span></span>
              <button className={`switch ${stripDraft.favorite ? "on" : ""}`} onClick={() => setStripDraft({ ...stripDraft, favorite: !stripDraft.favorite })} aria-label="Favorite"><i /></button>
            </div>
            <div className="toggle-row">
              <span><CirclePlus size={17} /><span><strong>Control enabled</strong><small>Disable commands while preserving mappings.</small></span></span>
              <button className={`switch ${stripDraft.enabled ? "on" : ""}`} onClick={() => setStripDraft({ ...stripDraft, enabled: !stripDraft.enabled })} aria-label="Control enabled"><i /></button>
            </div>
            <div className="device-facts">
              <span><b>MAC</b>{editingStrip.mac}</span>
              <span><b>IP</b>{editingStrip.last_ip || "—"}</span>
              <span><b>Firmware</b>{editingStrip.firmware_version || "—"}</span>
            </div>
            <button className="button danger wide" onClick={() => requestRemoveStrip(editingStrip)}>
              <Trash2 size={16} /> Remove strip
            </button>
          </div>
        )}
      </Modal>

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.title || ""}
        message={confirm?.message || ""}
        confirmLabel={confirm?.confirmLabel || "Confirm"}
        danger={confirm?.danger}
        onClose={() => setConfirm(null)}
        onConfirm={() => {
          const action = confirm?.action;
          setConfirm(null);
          Promise.resolve(action?.()).catch((error) =>
            notify(error instanceof Error ? error.message : String(error), true),
          );
        }}
      />

      {toast && <div className={`toast ${toast.error ? "error" : ""}`}>{toast.message}</div>}
    </div>
  );
}
