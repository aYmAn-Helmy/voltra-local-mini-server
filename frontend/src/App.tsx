import { useCallback, useEffect, useRef, useState } from "react";
import { CirclePlus, LoaderCircle, Star, Trash2 } from "lucide-react";

import { AuthError, api, getApiToken, setApiToken, subscribeEvents } from "./api";
import { AddStripView, AutomationView, DashboardView, EnergyView, RoomsView, SettingsView } from "./views";
import { AppHeader, BottomNav, ConfirmDialog, Modal } from "./ui";
import { DesktopDashboard, DesktopHeader, DesktopSidebar } from "./desktop";
import { OutletManagerDialog } from "./outlet_manager";
import { initialLocale, LocaleContext, persistLocale, t } from "./i18n";
import type { Locale } from "./i18n";
import type { AutomationSnapshot, Overview, Strip, ViewName } from "./types";

const emptyAutomation: AutomationSnapshot = { schedules: {}, rules: {}, queue: [] };

// Mount only one responsive workspace, so hidden device controls are never duplicated.
function useDesktopLayout(): boolean {
  const [desktop, setDesktop] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(min-width: 1120px)").matches,
  );
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1120px)");
    const sync = () => setDesktop(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);
  return desktop;
}


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
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const toggleLanguage = () => setLocale((prev) => { const next = prev === "en" ? "ar" : "en"; persistLocale(next); return next; });
  const desktop = useDesktopLayout();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [automation, setAutomation] = useState<AutomationSnapshot>(emptyAutomation);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyChannels, setBusyChannels] = useState<Set<string>>(new Set());
  const [toast, setToast] = useState<{ message: string; error: boolean } | null>(null);
  const [editingStrip, setEditingStrip] = useState<Strip | null>(null);
  const [editingOutlet, setEditingOutlet] = useState<{ strip: Strip; channel: number } | null>(null);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [authRequired, setAuthRequired] = useState(false);
  const [tokenDraft, setTokenDraft] = useState(() => getApiToken());
  const [stripDraft, setStripDraft] = useState({ name: "", room: "", favorite: false, enabled: true });
  const refreshTimer = useRef<number | null>(null);
  // Keep pending user intent in the rendered state while SSE/poll snapshots arrive.
  const pendingCommands = useRef(new Map<string, boolean>());
  const busyRef = useRef(new Set<string>());
  const withPending = useCallback((next: Overview): Overview => {
    let merged = next;
    pendingCommands.current.forEach((on, key) => {
      const separator = key.lastIndexOf(":");
      if (separator > 0) merged = updateOutletLocal(merged, key.slice(0, separator), Number(key.slice(separator + 1)), on);
    });
    return merged;
  }, []);

  const notify = useCallback((message: string, error = false) => {
    setToast({ message, error });
    window.setTimeout(() => setToast((current) => (current?.message === message ? null : current)), 3600);
  }, []);

  const refreshOverview = useCallback(async () => {
    try {
      const next = await api.overview();
      setOverview(withPending(next));
      setAuthRequired(false);
    } catch (error) {
      if (error instanceof AuthError) {
        setAuthRequired(true);
        return;
      }
      throw error;
    }
  }, [withPending]);

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
      setOverview(withPending(nextOverview));
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
  }, [notify, overview, withPending]);

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

  async function sendOutlet(strip: Strip, channel: number, on: boolean, confirmed = false): Promise<boolean> {
    const key = `${strip.mac}:${channel}`;
    if (busyRef.current.has(key)) return false;
    busyRef.current.add(key);
    pendingCommands.current.set(key, on);
    setBusyChannels(new Set(busyRef.current));
    setOverview((old) => old ? updateOutletLocal(old, strip.mac, channel, on) : old);
    try {
      const result = await api.setOutlet(strip.mac, channel, on, confirmed);
      // An ACK is not an electrical state verification. Never claim confirmed success without GETINFO.
      if (result.metrics?.last_command_confirmed !== true) {
        notify(t(locale, "Command sent; outlet state is not verified yet."), true);
      }
      return result.metrics?.last_command_confirmed === true;
    } catch (error) {
      notify(error instanceof Error ? error.message : String(error), true);
      return false;
    } finally {
      pendingCommands.current.delete(key);
      busyRef.current.delete(key);
      setBusyChannels(new Set(busyRef.current));
    }
  }

  async function setOutlet(strip: Strip, channel: number, on: boolean): Promise<void> {
    const prefs = strip.outlets.find((x) => x.channel === channel)?.preferences
      || strip.outlet_preferences?.[String(channel)];
    if (prefs?.locked) {
      notify(t(locale, "This outlet is locked"), true);
      return;
    }
    if (!on && prefs?.protected) {
      setConfirm({
        title: t(locale, "Protected outlet"),
        message: t(locale, "Confirm switching off the protected outlet?"),
        confirmLabel: t(locale, "Switch OFF"),
        danger: true,
        action: async () => {
          try {
            await sendOutlet(strip, channel, on, true);
          } finally {
            await refreshOverview().catch((error) => notify(String(error), true));
          }
        },
      });
      return;
    }
    try {
      await sendOutlet(strip, channel, on);
    } finally {
      await refreshOverview().catch((error) => notify(String(error), true));
    }
  }

  function requestSetAll(strip: Strip, on: boolean) {
    if ([1, 2, 3, 4].some((channel) => busyRef.current.has(`${strip.mac}:${channel}`))) return;
    setConfirm({
      title: t(locale, on ? "Turn all outlets on?" : "Turn all outlets off?"),
      message: `${strip.name} will switch all four outlets ${on ? "on" : "off"}. Commands are sent and verified one outlet at a time.`,
      confirmLabel: t(locale, on ? "Turn all on" : "Turn all off"),
      danger: !on,
      action: async () => {
        let failed = 0;
        try {
          for (const channel of [1, 2, 3, 4]) {
            const current = strip.outlets?.find((item) => Number(item.channel) === channel);
            if (Boolean(current?.relay) === on) continue;
            if (!(await sendOutlet(strip, channel, on, !on))) failed++;
          }
        } finally {
          await refreshOverview().catch((error) => notify(String(error), true));
        }
        notify(t(locale, failed ? "Some outlets could not be updated. Please check device status." : on ? "All outlets are on." : "All outlets are off."), failed > 0);
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
    <LocaleContext.Provider value={locale}>
    <div className="app-shell" lang={locale} dir={locale === "ar" ? "rtl" : "ltr"}>
      {desktop && <DesktopSidebar view={view} onNavigate={setView} overview={overview} />}
      <div className="app-frame">
        {desktop ? <DesktopHeader view={view} onRefresh={refreshAll} onSettings={() => setView("settings")} onLanguageToggle={toggleLanguage} busy={loading} /> : <AppHeader
          view={view}
          onBack={() => setView("dashboard")}
          onRefresh={refreshAll}
          onSettings={() => setView("settings")}
          onLanguageToggle={toggleLanguage}
          busy={loading}
        />}

        <main className="main-content">
          {view === "dashboard" && !desktop && (
            <div className="mobile-dashboard"><DashboardView
              overview={overview}
              automation={automation}
              search={search}
              onSearch={setSearch}
              busyChannels={busyChannels}
              onNavigate={setView}
              onToggleOutlet={setOutlet}
              onSetAll={requestSetAll}
              onStripSettings={setEditingStrip}
              onConfigureOutlet={(strip, channel) => setEditingOutlet({ strip, channel })}
            /></div>
          )}
          {view === "dashboard" && desktop && (
            <div className="desktop-dashboard"><DesktopDashboard
              overview={overview}
              automation={automation}
              search={search}
              onSearch={setSearch}
              busyChannels={busyChannels}
              onNavigate={setView}
              onToggleOutlet={setOutlet}
              onSetAll={requestSetAll}
              onStripSettings={setEditingStrip}
              onConfigureOutlet={(strip, channel) => setEditingOutlet({ strip, channel })}
            /></div>
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

        {!desktop && <BottomNav view={view} onChange={setView} />}
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

      <OutletManagerDialog
        selection={editingOutlet}
        overview={overview}
        automation={automation}
        onClose={() => setEditingOutlet(null)}
        onChanged={refreshAll}
        notify={notify}
      />

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
    </LocaleContext.Provider>
  );
}
