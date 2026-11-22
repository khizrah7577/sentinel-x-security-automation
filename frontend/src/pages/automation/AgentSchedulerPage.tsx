import { useState } from "react";
import { useApi } from "../../hooks/useApi";
import { api, ApiError } from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
import {
  Button,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
} from "../../components/nexus/primitives";
import { AutomationShell, CatalogNote, StatusBadge } from "./AutomationShared";

type Task = {
  id: number;
  name: string;
  kind: string;
  cron_or_interval: string;
  enabled: boolean;
  last_run_at?: string | null;
  last_status: string;
  last_error: string;
  is_running: boolean;
};

export default function AgentSchedulerPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const tasks = useApi<Task[]>(`/automation/scheduler?_=${tick}`, [tick]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = () => setTick((t) => t + 1);

  const patch = async (id: number, body: Record<string, unknown>) => {
    setError(null);
    try {
      await api(`/automation/scheduler/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Update failed");
    }
  };

  const runNow = async (id: number) => {
    setError(null);
    try {
      const out = await api<{ last_status: string; last_error: string }>(`/automation/scheduler/${id}/run`, {
        method: "POST",
      });
      setMessage(`Task #${id} → ${out.last_status}${out.last_error ? `: ${out.last_error}` : ""}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Run failed");
    }
  };

  return (
    <AutomationShell
      title="Agent Scheduler"
      description="Recurring health, summary, investigation review, ML report, and firewall cleanup jobs. Overlaps are prevented."
    >
      <CatalogNote />
      {message && (
        <p className="text-sm m-0" style={{ color: "var(--accent)" }}>
          {message}
        </p>
      )}
      {error && <ErrorBlock message={error} />}
      <GlassPanel>
        <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
          Interval format: <code>interval:SECONDS</code> (minimum 30s). Jobs run via APScheduler in the API process.
        </p>
      </GlassPanel>
      {tasks.loading && <LoadingBlock />}
      {tasks.error && <ErrorBlock message={tasks.error} />}
      {tasks.data && tasks.data.length === 0 && (
        <EmptyState title="No scheduled tasks" detail="Default tasks seed on API startup." />
      )}
      {tasks.data && tasks.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Kind", "Schedule", "Enabled", "Last", "Status", "Controls"]}
          rows={tasks.data.map((t) => [
            t.id,
            t.name,
            t.kind,
            t.cron_or_interval,
            t.enabled ? "Yes" : "No",
            t.last_run_at ? new Date(t.last_run_at).toLocaleString() : "—",
            <StatusBadge key={t.id} status={t.is_running ? "running" : t.last_status || "—"} />,
            user?.role === "admin" ? (
              <div className="flex flex-wrap gap-1">
                <Button variant="secondary" onClick={() => void patch(t.id, { enabled: !t.enabled })}>
                  {t.enabled ? "Disable" : "Enable"}
                </Button>
                <Button variant="ghost" onClick={() => void runNow(t.id)}>
                  Run now
                </Button>
              </div>
            ) : (
              "Admin only"
            ),
          ])}
        />
      )}
    </AutomationShell>
  );
}
