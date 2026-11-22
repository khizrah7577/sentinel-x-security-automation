import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Badge,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
  PageHeader,
  StatusDot,
} from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";

type Profiles = {
  ai_configured: boolean;
  message: string | null;
  agents: { name: string; title: string; description: string; status: string }[];
};

type Execution = {
  id: number;
  investigation_id: number | null;
  agent_name: string;
  status: string;
  error_message: string;
  duration_ms: number;
  output_json?: string;
  created_at: string;
};

type Investigation = {
  id: number;
  status: string;
  severity: string;
  summary: string;
  recommended_action: string;
  created_at: string;
};

const ORDER = ["monitoring", "investigation", "decision", "response", "explanation"];

function stageTone(status: string): "ok" | "warn" | "danger" | "neutral" | "ai" {
  if (status === "completed" || status === "ready") return "ok";
  if (status === "running") return "ai";
  if (status === "failed") return "danger";
  if (status === "pending") return "warn";
  return "neutral";
}

function stageDot(status: string): "ok" | "warn" | "danger" | "muted" | "ai" {
  const t = stageTone(status);
  return t === "neutral" ? "muted" : t;
}

export default function AgentsPage() {
  const [tick, setTick] = useState(0);
  const profiles = useApi<Profiles>(`/agents/profiles?_=${tick}`, [tick]);
  const executions = useApi<Execution[]>(`/agents/executions?limit=50&_=${tick}`, [tick]);
  const investigations = useApi<Investigation[]>(`/agents/investigations?_=${tick}`, [tick]);
  const [focusInv, setFocusInv] = useState<number | null>(null);

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 8000);
    return () => window.clearInterval(id);
  }, []);

  const activeInvId = focusInv ?? investigations.data?.[0]?.id ?? null;
  const activeInv = investigations.data?.find((i) => i.id === activeInvId) || null;

  const stageStatus = useMemo(() => {
    const map: Record<string, Execution | undefined> = {};
    const related = (executions.data || []).filter((e) => e.investigation_id === activeInvId);
    for (const name of ORDER) {
      map[name] = related.find((e) => e.agent_name === name);
    }
    return map;
  }, [executions.data, activeInvId]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Intelligence"
        title="Agent Command Center"
        description="Five LangGraph agents. Stage states reflect backend execution records only — no simulated progress."
        actions={
          <Link
            to="/investigations"
            className="rounded-xl px-3 py-2 text-sm font-semibold"
            style={{ background: "var(--accent-ai)", color: "#fff" }}
          >
            Open investigations
          </Link>
        }
      />

      {profiles.loading && <LoadingBlock />}
      {profiles.error && <ErrorBlock message={profiles.error} />}
      {profiles.data?.message && (
        <GlassPanel>
          <p className="text-sm m-0">
            {profiles.data.message}{" "}
            <Link to="/settings" style={{ color: "var(--accent)" }}>
              Open AI Configuration
            </Link>
          </p>
        </GlassPanel>
      )}

      {profiles.data && (
        <GlassPanel>
          <h3 className="text-sm font-bold m-0 mb-4">Workflow pipeline</h3>
          <div className="flex flex-col lg:flex-row gap-3 items-stretch">
            {ORDER.map((name, idx) => {
              const profile = profiles.data!.agents.find((a) => a.name === name);
              const exec = stageStatus[name];
              const status = exec?.status || (activeInv ? "idle" : profile?.status || "idle");
              return (
                <div key={name} className="flex-1 flex items-center gap-3">
                  <motion.div
                    layout
                    className="flex-1 rounded-2xl border p-3 min-h-[120px]"
                    style={{
                      borderColor: "var(--border)",
                      background:
                        status === "running"
                          ? "var(--accent-ai-soft)"
                          : status === "failed"
                            ? "color-mix(in srgb, var(--critical) 12%, var(--surface))"
                            : "var(--surface)",
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--accent-ai)" }}>
                        Agent {idx + 1}
                      </div>
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold">
                        <StatusDot tone={stageDot(status)} />
                        {status}
                      </span>
                    </div>
                    <div className="text-sm font-bold mt-1">{profile?.title || name}</div>
                    <p className="text-xs mt-1 mb-0 line-clamp-2" style={{ color: "var(--muted)" }}>
                      {profile?.description}
                    </p>
                    {exec && (
                      <div className="text-[11px] font-mono mt-2" style={{ color: "var(--muted)" }}>
                        {exec.duration_ms} ms · inv #{exec.investigation_id}
                      </div>
                    )}
                  </motion.div>
                  {idx < ORDER.length - 1 && (
                    <div className="hidden lg:block w-6 h-px" style={{ background: "var(--border)" }} />
                  )}
                </div>
              );
            })}
          </div>
          {activeInv && (
            <div className="mt-4 rounded-xl border p-3 text-sm" style={{ borderColor: "var(--border)" }}>
              <div className="flex flex-wrap gap-2 items-center">
                <Badge tone="ai">Investigation #{activeInv.id}</Badge>
                <Badge tone={stageTone(activeInv.status)}>{activeInv.status}</Badge>
                <Badge tone="warn">{activeInv.severity}</Badge>
              </div>
              <p className="mt-2 mb-1">{activeInv.summary || "No summary yet."}</p>
              <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
                Recommended: {activeInv.recommended_action || "—"}
              </p>
            </div>
          )}
        </GlassPanel>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <GlassPanel>
          <h3 className="text-sm font-bold m-0 mb-3">Investigations</h3>
          {investigations.data && investigations.data.length === 0 && (
            <EmptyState title="No investigations" detail="Trigger a batch investigate from AI Investigation." />
          )}
          {investigations.data && investigations.data.length > 0 && (
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {investigations.data.map((inv) => (
                <button
                  key={inv.id}
                  type="button"
                  onClick={() => setFocusInv(inv.id)}
                  className="w-full text-left rounded-xl border px-3 py-2"
                  style={{
                    borderColor: inv.id === activeInvId ? "var(--accent-ai)" : "var(--border)",
                    background: inv.id === activeInvId ? "var(--accent-ai-soft)" : "transparent",
                  }}
                >
                  <div className="flex justify-between gap-2 text-sm">
                    <span className="font-semibold">#{inv.id}</span>
                    <Badge tone={stageTone(inv.status)}>{inv.status}</Badge>
                  </div>
                  <div className="text-xs mt-1 line-clamp-2" style={{ color: "var(--muted)" }}>
                    {inv.summary || "—"}
                  </div>
                </button>
              ))}
            </div>
          )}
        </GlassPanel>

        <GlassPanel className="p-0 overflow-hidden">
          <div className="px-5 pt-5">
            <h3 className="text-sm font-bold m-0 mb-3">Execution history</h3>
          </div>
          {executions.loading && <LoadingBlock />}
          {executions.error && <ErrorBlock message={executions.error} />}
          {executions.data && executions.data.length === 0 && (
            <div className="px-5 pb-5">
              <EmptyState title="No agent executions" detail="Runs appear after an investigation workflow is triggered." />
            </div>
          )}
          {executions.data && executions.data.length > 0 && (
            <DataTable
              columns={["ID", "Agent", "Inv", "Status", "Duration", "Time"]}
              rows={executions.data.map((e) => [
                e.id,
                e.agent_name,
                e.investigation_id ?? "—",
                e.status,
                `${e.duration_ms} ms`,
                new Date(e.created_at).toLocaleString(),
              ])}
            />
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
