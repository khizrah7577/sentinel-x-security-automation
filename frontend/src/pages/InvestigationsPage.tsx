import { useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card, DataTable, EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";

type Profiles = {
  ai_configured: boolean;
  ai_status: string;
  message: string | null;
  agents: { name: string; title: string; status: string }[];
};

type Investigation = {
  id: number;
  incident_id: number;
  status: string;
  severity: string;
  summary: string;
  explanation: string;
  recommended_action: string;
  used_openai: boolean;
  error_message: string;
  created_at: string;
};

type Execution = {
  id: number;
  agent_name: string;
  status: string;
  duration_ms: number;
  output_json: string;
  created_at: string;
};

export default function InvestigationsPage() {
  const [tick, setTick] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const profiles = useApi<Profiles>(`/agents/profiles?_=${tick}`, [tick]);
  const items = useApi<Investigation[]>(`/agents/investigations?_=${tick}`, [tick]);
  const executions = useApi<Execution[]>(
    selectedId ? `/agents/investigations/${selectedId}/executions` : null,
    [selectedId, tick],
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<Investigation | null>(null);

  const runBatch = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const out = await api<{ count: number; results: { investigation_id?: number; error?: string; message?: string }[] }>(
        "/agents/investigate/batch",
        { method: "POST", body: JSON.stringify({ limit: 5 }) },
      );
      const errors = out.results.filter((r) => r.error).length;
      setMessage(
        `Completed ${out.count} investigation attempt(s); errors=${errors}. ` +
          (out.results[0]?.message || ""),
      );
      if (out.results[0]?.investigation_id) {
        setSelectedId(out.results[0].investigation_id);
      }
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Investigation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Investigation"
        description="LangGraph workflow: Monitoring → Investigation → Decision → Response prep → Explanation. Evidence-bound; no invented network facts."
        actions={
          <button
            type="button"
            className="rounded-md px-4 py-2 text-sm text-white"
            style={{ background: "var(--accent)" }}
            disabled={busy}
            onClick={() => void runBatch()}
          >
            {busy ? "Investigating…" : "Investigate top ML attacks"}
          </button>
        }
      />

      {profiles.loading && <LoadingBlock />}
      {profiles.error && <ErrorBlock message={profiles.error} />}
      {profiles.data && !profiles.data.ai_configured && (
        <Card>
          <p className="text-sm m-0">
            OpenAI API key is not configured. Please visit{" "}
            <Link to="/settings" style={{ color: "var(--accent)" }}>
              Settings → AI Configuration
            </Link>{" "}
            to enable AI-powered investigations. Rule-based agents still run using confirmed evidence.
          </p>
        </Card>
      )}
      {message && <p className="text-sm m-0" style={{ color: "var(--accent)" }}>{message}</p>}
      {error && <ErrorBlock message={error} />}

      {profiles.data && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          {profiles.data.agents.map((a) => (
            <Card key={a.name}>
              <div className="text-sm font-semibold">{a.title}</div>
              <div className="mt-2">
                <Badge tone={a.status === "ready" ? "ok" : "warn"}>{a.status}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}

      <h2 className="text-base font-semibold m-0">Investigation history</h2>
      {items.loading && <LoadingBlock />}
      {items.error && <ErrorBlock message={items.error} />}
      {items.data && items.data.length === 0 && (
        <EmptyState
          title="No investigations yet"
          detail="Run ML predictions first, then click Investigate top ML attacks."
        />
      )}
      {items.data && items.data.length > 0 && (
        <DataTable
          columns={["ID", "Incident", "Status", "Severity", "Action", "AI", "Summary", "Open"]}
          rows={items.data.map((i) => [
            i.id,
            i.incident_id,
            i.status,
            <Badge tone={i.severity === "critical" || i.severity === "high" ? "danger" : "warn"}>
              {i.severity}
            </Badge>,
            i.recommended_action || "—",
            i.used_openai ? <Badge tone="ok">Yes</Badge> : <Badge>Rules</Badge>,
            (i.summary || "").slice(0, 80) || "—",
            <button
              type="button"
              className="rounded-md border px-2 py-1 text-xs"
              style={{ borderColor: "var(--border)" }}
              onClick={() => {
                setSelectedId(i.id);
                setDetail(i);
              }}
            >
              Timeline
            </button>,
          ])}
        />
      )}

      {detail && (
        <Card className="space-y-2">
          <h3 className="text-sm font-semibold m-0">Investigation #{detail.id}</h3>
          <p className="text-sm m-0">{detail.explanation || detail.summary}</p>
          {detail.error_message && (
            <p className="text-sm m-0" style={{ color: "var(--warning)" }}>
              {detail.error_message}
            </p>
          )}
        </Card>
      )}

      <h2 className="text-base font-semibold m-0">
        Agent timeline {selectedId ? `(#${selectedId})` : ""}
      </h2>
      {!selectedId && (
        <EmptyState title="Select an investigation" detail="Click Timeline on a row to view agent steps." />
      )}
      {selectedId && executions.loading && <LoadingBlock />}
      {executions.data && executions.data.length > 0 && (
        <DataTable
          columns={["Order", "Agent", "Status", "Duration", "Output preview"]}
          rows={executions.data.map((e, idx) => [
            idx + 1,
            e.agent_name,
            e.status,
            `${e.duration_ms} ms`,
            <span className="text-xs" title={e.output_json}>
              {(e.output_json || "").slice(0, 100)}
              {(e.output_json || "").length > 100 ? "…" : ""}
            </span>,
          ])}
        />
      )}
    </div>
  );
}
