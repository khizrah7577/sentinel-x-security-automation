import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../services/api";
import { useTheme, type ThemeMode } from "../contexts/ThemeContext";
import { useAuth } from "../contexts/AuthContext";
import { GlassPanel, PageHeader } from "../components/nexus/primitives";

type AIStatus = {
  configured: boolean;
  masked_key: string;
  model: string;
  status: string;
  last_tested_at?: string | null;
  last_error?: string | null;
};

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [ai, setAi] = useState<AIStatus | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("gpt-4o-mini");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (user?.role !== "admin") return;
    try {
      const data = await api<AIStatus>("/settings/ai");
      setAi(data);
      setModel(data.model || "gpt-4o-mini");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load AI settings");
    }
  };

  useEffect(() => {
    void load();
  }, [user]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const data = await api<AIStatus>("/settings/ai", {
        method: "PUT",
        body: JSON.stringify({ api_key: apiKey, model }),
      });
      setAi(data);
      setApiKey("");
      setMessage("API key saved. It will never be shown in full again.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const test = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const data = await api<AIStatus>("/settings/ai/test", { method: "POST" });
      setAi(data);
      setMessage("Connection test succeeded.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Test failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await api("/settings/ai", { method: "DELETE" });
      setAi({
        configured: false,
        masked_key: "",
        model: "gpt-4o-mini",
        status: "not_configured",
      });
      setMessage("API key removed.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Remove failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        eyebrow="System"
        title="Settings"
        description="Theme preference and optional OpenAI configuration for agent narratives."
      />

      <GlassPanel className="space-y-3">
        <h2 className="text-base font-semibold m-0">Theme</h2>
        <div className="flex gap-2">
          {(["light", "dark", "system"] as ThemeMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className="rounded-md border px-3 py-2 text-sm capitalize"
              style={{
                borderColor: theme === mode ? "var(--accent)" : "var(--border)",
                background: theme === mode ? "var(--accent-soft)" : "transparent",
              }}
              onClick={() => setTheme(mode)}
            >
              {mode}
            </button>
          ))}
        </div>
      </GlassPanel>

      <GlassPanel className="space-y-4">
        <div>
          <h2 className="text-base font-semibold m-0">AI Configuration</h2>
          <p className="text-sm mt-1 mb-0" style={{ color: "var(--muted)" }}>
            OpenAI API key is stored encrypted on the backend. The full key is never returned to the
            browser after save.
          </p>
        </div>

        {user?.role !== "admin" ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Only administrators can manage the OpenAI API key.
          </p>
        ) : (
          <>
            <div className="text-sm">
              Status:{" "}
              <strong>{ai?.status || "loading…"}</strong>
              {ai?.masked_key ? ` (${ai.masked_key})` : ""}
            </div>
            <form onSubmit={save} className="space-y-3">
              <label className="block text-sm space-y-1">
                <span>OpenAI API key</span>
                <div className="flex gap-2">
                  <input
                    type={showKey ? "text" : "password"}
                    className="flex-1 rounded-md border px-3 py-2 bg-transparent"
                    style={{ borderColor: "var(--border)" }}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={ai?.configured ? "Enter new key to replace" : "sk-..."}
                    required
                  />
                  <button
                    type="button"
                    className="rounded-md border px-3 text-sm"
                    style={{ borderColor: "var(--border)" }}
                    onClick={() => setShowKey((s) => !s)}
                  >
                    {showKey ? "Hide" : "Show"}
                  </button>
                </div>
              </label>
              <label className="block text-sm space-y-1">
                <span>Model</span>
                <input
                  className="w-full rounded-md border px-3 py-2 bg-transparent"
                  style={{ borderColor: "var(--border)" }}
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-md px-4 py-2 text-sm text-white"
                  style={{ background: "var(--accent)" }}
                >
                  Save API key
                </button>
                <button
                  type="button"
                  disabled={busy || !ai?.configured}
                  className="rounded-md border px-4 py-2 text-sm"
                  style={{ borderColor: "var(--border)" }}
                  onClick={() => void test()}
                >
                  Test connection
                </button>
                <button
                  type="button"
                  disabled={busy || !ai?.configured}
                  className="rounded-md border px-4 py-2 text-sm"
                  style={{ borderColor: "var(--border)", color: "var(--danger)" }}
                  onClick={() => void remove()}
                >
                  Remove key
                </button>
              </div>
            </form>
            {message && <p className="text-sm m-0" style={{ color: "var(--accent)" }}>{message}</p>}
            {error && <p className="text-sm m-0" style={{ color: "var(--danger)" }}>{error}</p>}
            {ai?.last_tested_at && (
              <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
                Last successful test: {ai.last_tested_at}
              </p>
            )}
          </>
        )}
      </GlassPanel>

      <SettingsExtras />
    </div>
  );
}

function SettingsExtras() {
  const mode = useApiMode();
  const health = useHealth();
  const network = useNetworkStatus();

  return (
    <>
      <section
        className="rounded-xl border p-5 space-y-2"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <h2 className="text-base font-semibold m-0">Response Mode</h2>
        {mode && (
          <>
            <p className="text-sm m-0">
              Active: <strong>{mode.mode}</strong>
            </p>
            <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
              {mode.description[mode.mode]}
            </p>
            <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
              Mode changes with approval workflow controls are finalized in Phase 8.
            </p>
          </>
        )}
      </section>

      <section
        className="rounded-xl border p-5 space-y-2"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <h2 className="text-base font-semibold m-0">Network &amp; Zeek</h2>
        {network && (
          <ul className="text-sm m-0 pl-5 space-y-1" style={{ color: "var(--muted)" }}>
            <li>Monitoring mode: {network.monitoring_mode}</li>
            <li>Zeek enabled: {String(network.zeek_enabled)}</li>
            <li>Live capture: {String(network.live_capture_available)}</li>
          </ul>
        )}
      </section>

      <section
        className="rounded-xl border p-5 space-y-2"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <h2 className="text-base font-semibold m-0">Database Status</h2>
        {health ? (
          <p className="text-sm m-0">
            {health.database?.status === "connected" ? (
              <span style={{ color: "var(--accent)" }}>Connected</span>
            ) : (
              <span style={{ color: "var(--danger)" }}>
                {health.database?.status || "unknown"}
                {health.database?.error ? ` — ${health.database.error}` : ""}
              </span>
            )}
          </p>
        ) : (
          <p className="text-sm m-0" style={{ color: "var(--muted)" }}>Checking…</p>
        )}
      </section>
    </>
  );
}

function useApiMode() {
  const [mode, setMode] = useState<{
    mode: string;
    description: Record<string, string>;
  } | null>(null);
  useEffect(() => {
    void api<{ mode: string; description: Record<string, string> }>("/response/mode")
      .then(setMode)
      .catch(() => setMode(null));
  }, []);
  return mode;
}

function useHealth() {
  const [health, setHealth] = useState<{
    database?: { status: string; error?: string };
  } | null>(null);
  useEffect(() => {
    void fetch("/api/v1/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);
  return health;
}

function useNetworkStatus() {
  const [network, setNetwork] = useState<{
    monitoring_mode: string;
    zeek_enabled: boolean;
    live_capture_available: boolean;
  } | null>(null);
  useEffect(() => {
    void api<{
      monitoring_mode: string;
      zeek_enabled: boolean;
      live_capture_available: boolean;
    }>("/network/status")
      .then(setNetwork)
      .catch(() => setNetwork(null));
  }, []);
  return network;
}
