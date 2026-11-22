import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
  MetricCard,
  PageHeader,
  RangeFilter,
  Skeleton,
  StatusDot,
} from "../components/nexus/primitives";
import { ChartCard, DonutChart, HBarChart } from "../components/charts/ChartKit";
import { AnalyticsApi, api, ApiError, type AnalyticsOverview } from "../services/api";
import { Bot, Crosshair, ShieldAlert, Search } from "lucide-react";

type Overview = {
  totals: {
    investigations: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    awaiting: number;
    confirmed: number;
    failed: number;
    unconfirmed: number;
  };
  severity_distribution: { name: string; value: number }[];
  status_distribution: { name: string; value: number }[];
  category_distribution: { name: string; value: number }[];
  agent_latest: {
    agent_name: string;
    status: string;
    error_message?: string;
    duration_ms?: number;
    investigation_id?: number | null;
    created_at?: string | null;
    output_preview?: string;
  }[];
  recent: {
    id: number;
    incident_id: number;
    status: string;
    severity: string;
    summary: string;
    used_openai: boolean;
    created_at: string | null;
  }[];
  ai_configured: boolean;
  ai_message: string | null;
};

type InvestigationRow = {
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

type Detail = {
  investigation: {
    id: number;
    incident_id: number;
    status: string;
    severity: string;
    summary: string;
    explanation: string;
    recommended_action: string;
    used_openai: boolean;
    error_message: string;
    uncertainty_notes: unknown[];
    evidence: Record<string, unknown>;
    created_at: string | null;
    completed_at: string | null;
  };
  incident: {
    id: number;
    title: string;
    description: string;
    severity: string;
    status: string;
    source_ip: string;
    dest_ip: string;
    attack_category: string;
    prediction_id: number | null;
    network_event_id: number | null;
  } | null;
  prediction: {
    id: number;
    predicted_label: string;
    attack_category: string;
    confidence: number;
    severity: string;
    evidence: Record<string, unknown>;
    created_at: string | null;
  } | null;
  network_event: Record<string, unknown> | null;
  traffic_record: Record<string, unknown> | null;
  agent_executions: {
    id: number;
    agent_name: string;
    status: string;
    error_message: string;
    duration_ms: number;
    output_json: string;
    created_at: string | null;
  }[];
  recommendations: {
    id: number;
    action_type: string;
    rationale: string;
    approval_status: string;
    created_at: string | null;
  }[];
  ai_configured: boolean;
  ai_message: string | null;
};

const AGENT_TITLES: Record<string, string> = {
  monitoring: "Monitoring Agent",
  investigation: "Threat Investigation Agent",
  decision: "Decision-Making Agent",
  response: "Response Agent",
  explanation: "Explanation and Reporting Agent",
};

function sevTone(s: string) {
  if (s === "critical" || s === "high") return "danger" as const;
  if (s === "medium") return "warn" as const;
  return "info" as const;
}

export default function IntelligencePage() {
  const [range, setRange] = useState("24h");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [rows, setRows] = useState<InvestigationRow[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [sourceIp, setSourceIp] = useState("");
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [execIndex, setExecIndex] = useState<Record<number, string[]>>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, invs, an, execs] = await Promise.all([
        api<Overview>("/agents/intelligence/overview"),
        api<InvestigationRow[]>("/agents/investigations?limit=100"),
        AnalyticsApi.overview(range),
        api<{ id: number; investigation_id: number | null; agent_name: string }[]>(
          "/agents/executions?limit=200",
        ),
      ]);
      setOverview(ov);
      setRows(invs);
      setAnalytics(an);
      const idx: Record<number, string[]> = {};
      for (const e of execs) {
        if (!e.investigation_id) continue;
        if (!idx[e.investigation_id]) idx[e.investigation_id] = [];
        if (!idx[e.investigation_id].includes(e.agent_name)) idx[e.investigation_id].push(e.agent_name);
      }
      setExecIndex(idx);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Intelligence");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [range]);

  useEffect(() => {
    if (!detailId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDetailLoading(true);
      try {
        const d = await api<Detail>(`/agents/investigations/${detailId}/detail`);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load detail");
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [detailId]);

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (severity && r.severity !== severity) return false;
      if (status && r.status !== status) return false;
      if (category) {
        const hay = `${r.summary} ${r.explanation} ${r.recommended_action}`.toLowerCase();
        if (!hay.includes(category.toLowerCase())) return false;
      }
      if (sourceIp) {
        const hay = `${r.summary} ${r.explanation}`.toLowerCase();
        if (!hay.includes(sourceIp.toLowerCase())) return false;
      }
      if (agentFilter) {
        const agents = execIndex[r.id] || [];
        if (!agents.includes(agentFilter)) return false;
      }
      return true;
    });
  }, [rows, severity, status, category, sourceIp, agentFilter, execIndex]);

  const agentFilteredRows = filtered;

  const categories = useMemo(() => {
    const set = new Set<string>();
    (overview?.category_distribution || []).forEach((c) => set.add(c.name));
    return Array.from(set).sort();
  }, [overview]);

  const runBatch = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const out = await api<{ count: number; results: { investigation_id?: number; error?: string }[] }>(
        "/agents/investigate/batch",
        { method: "POST", body: JSON.stringify({ limit: 5 }) },
      );
      const errors = out.results.filter((r) => r.error).length;
      setMessage(`Completed ${out.count} investigation attempt(s); errors=${errors}.`);
      if (out.results[0]?.investigation_id) setDetailId(out.results[0].investigation_id);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Investigation failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Intelligence"
        title="Threat Intelligence"
        description="Investigations, agent activity, and evidence-bound analysis from PostgreSQL. Works with rule-based agents when no OpenAI key is configured."
        actions={
          <div className="flex flex-wrap gap-2 items-center">
            <RangeFilter value={range} onChange={setRange} />
            <Button disabled={busy} onClick={() => void runBatch()} variant="ai">
              {busy ? "Investigating…" : "Investigate top ML attacks"}
            </Button>
          </div>
        }
      />

      {overview?.ai_message && (
        <GlassPanel style={{ borderColor: "color-mix(in srgb, var(--accent-ai) 40%, var(--border))" }}>
          <p className="text-sm m-0">
            <Badge tone="ai">AI key missing</Badge>{" "}
            <span style={{ color: "var(--muted)" }}>{overview.ai_message}</span>{" "}
            <Link to="/settings" style={{ color: "var(--accent-ai)", fontWeight: 600 }}>
              Open Settings → AI Configuration
            </Link>
          </p>
        </GlassPanel>
      )}

      {error && <ErrorBlock message={error} />}
      {message && (
        <p className="text-sm m-0" style={{ color: "var(--accent)" }}>
          {message}
        </p>
      )}

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      )}

      {overview && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Threats investigated"
              value={overview.totals.investigations}
              icon={<Search className="w-5 h-5" />}
              accent="var(--accent)"
            />
            <MetricCard
              label="Critical / High"
              value={overview.totals.critical + overview.totals.high}
              icon={<ShieldAlert className="w-5 h-5" />}
              accent="var(--critical)"
              hint={`Critical ${overview.totals.critical} · High ${overview.totals.high}`}
            />
            <MetricCard
              label="Awaiting investigation"
              value={overview.totals.awaiting}
              icon={<Bot className="w-5 h-5" />}
              accent="var(--accent-ai)"
            />
            <MetricCard
              label="Confirmed / Failed"
              value={`${overview.totals.confirmed} / ${overview.totals.failed}`}
              icon={<Crosshair className="w-5 h-5" />}
              accent="var(--accent-secondary)"
              hint={`Unconfirmed ${overview.totals.unconfirmed} · Med ${overview.totals.medium} · Low ${overview.totals.low}`}
            />
          </div>

          <GlassPanel>
            <h3 className="text-sm font-bold m-0 mb-3">AI Agent Activity</h3>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {(overview.agent_latest || []).map((a) => (
                <div
                  key={a.agent_name}
                  className="rounded-xl border p-3"
                  style={{ borderColor: "var(--border)", background: "var(--elevated)" }}
                >
                  <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--accent-ai)" }}>
                    {a.agent_name}
                  </div>
                  <div className="text-sm font-bold mt-1">{AGENT_TITLES[a.agent_name] || a.agent_name}</div>
                  <div className="flex items-center gap-1.5 mt-2 text-xs font-semibold">
                    <StatusDot
                      tone={
                        a.status === "completed" || a.status === "ready"
                          ? "ok"
                          : a.status === "failed"
                            ? "danger"
                            : a.status === "running"
                              ? "ai"
                              : "muted"
                      }
                    />
                    {a.status || "idle"}
                  </div>
                  <div className="text-[11px] mt-2" style={{ color: "var(--muted)" }}>
                    {a.created_at ? new Date(a.created_at).toLocaleString() : "No executions yet"}
                    {a.duration_ms != null ? ` · ${a.duration_ms} ms` : ""}
                  </div>
                  {a.error_message ? (
                    <p className="text-[11px] mt-1 mb-0" style={{ color: "var(--critical)" }}>
                      {a.error_message}
                    </p>
                  ) : (
                    <p className="text-[11px] mt-1 mb-0 line-clamp-2" style={{ color: "var(--muted)" }}>
                      {a.output_preview || "—"}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </GlassPanel>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartCard title="Threat severity distribution" empty={!overview.severity_distribution.length}>
              <HBarChart data={overview.severity_distribution} />
            </ChartCard>
            <ChartCard title="Attack category distribution" empty={!overview.category_distribution.length}>
              <DonutChart data={overview.category_distribution} />
            </ChartCard>
            <ChartCard
              title="Threat detection timeline"
              subtitle="Attack predictions in selected analytics range"
              empty={!analytics?.detection_timeline?.length}
            >
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {(analytics?.detection_timeline || []).map((d) => (
                  <div
                    key={d.id}
                    className="flex justify-between gap-2 rounded-lg border px-3 py-2 text-sm"
                    style={{ borderColor: "var(--border)" }}
                  >
                    <div>
                      <div className="font-semibold">{d.category || d.label}</div>
                      <div className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                        {new Date(d.t).toLocaleString()}
                      </div>
                    </div>
                    <Badge tone={sevTone(d.severity)}>{d.severity}</Badge>
                  </div>
                ))}
              </div>
            </ChartCard>
            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-3">Targets & sources (analytics range)</h3>
              {!analytics?.top_source_ips?.length && !analytics?.top_dest_ports?.length ? (
                <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
                  No talker/port data in this range.
                </p>
              ) : (
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>
                      Suspicious source IPs
                    </div>
                    <DataTable
                      columns={["IP", "Count"]}
                      rows={(analytics?.top_source_ips || []).map((r) => [
                        <span key={r.ip} className="font-mono text-xs">
                          {r.ip}
                        </span>,
                        r.count,
                      ])}
                    />
                  </div>
                  <div>
                    <div className="text-xs font-semibold mb-2" style={{ color: "var(--muted)" }}>
                      Most targeted ports
                    </div>
                    <DataTable
                      columns={["Port", "Count"]}
                      rows={(analytics?.top_dest_ports || []).map((r) => [r.port, r.count])}
                    />
                  </div>
                </div>
              )}
              <div className="mt-4 text-xs" style={{ color: "var(--muted)" }}>
                Investigation success: {overview.totals.confirmed} completed · {overview.totals.failed} failed
              </div>
            </GlassPanel>
          </div>

          <GlassPanel className="space-y-3">
            <div className="flex flex-wrap items-end gap-3">
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--muted)" }}>Severity</span>
                <select
                  className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value)}
                >
                  <option value="">All</option>
                  {["critical", "high", "medium", "low", "informational"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--muted)" }}>Status</span>
                <select
                  className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <option value="">All</option>
                  {["pending", "running", "completed", "failed", "skipped_no_ai"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--muted)" }}>Category</span>
                <select
                  className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  <option value="">All</option>
                  {categories.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--muted)" }}>Agent</span>
                <select
                  className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={agentFilter}
                  onChange={(e) => setAgentFilter(e.target.value)}
                >
                  <option value="">All</option>
                  {Object.keys(AGENT_TITLES).map((a) => (
                    <option key={a} value={a}>
                      {AGENT_TITLES[a]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1 flex-1 min-w-[140px]">
                <span style={{ color: "var(--muted)" }}>Source IP</span>
                <input
                  className="block w-full rounded-lg border px-2 py-1.5 bg-transparent text-sm font-mono"
                  style={{ borderColor: "var(--border)" }}
                  value={sourceIp}
                  onChange={(e) => setSourceIp(e.target.value)}
                  placeholder="e.g. 10.0.0.66"
                />
              </label>
            </div>
          </GlassPanel>

          <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
            <GlassPanel className="p-0 overflow-hidden">
              <div className="px-5 pt-5 pb-2">
                <h3 className="text-sm font-bold m-0">AI Investigation Center</h3>
              </div>
              {rows.length === 0 ? (
                <div className="px-5 pb-5">
                  <EmptyState
                    title="No investigations available yet"
                    detail="Run ML predictions on PCAP flows, then investigate top attacks. Start from PCAP Analysis or Network Monitoring."
                  />
                  <div className="flex gap-2 mt-3">
                    <Link to="/pcap">
                      <Button variant="secondary">PCAP Analysis</Button>
                    </Link>
                    <Link to="/monitoring">
                      <Button variant="ghost">Network Monitoring</Button>
                    </Link>
                  </div>
                </div>
              ) : (
                <DataTable
                  columns={["ID", "Incident", "Severity", "Status", "AI", "Summary", "Opened"]}
                  rows={agentFilteredRows.map((r) => [
                    <button
                      key={r.id}
                      type="button"
                      className="font-mono text-xs font-semibold"
                      style={{ color: "var(--accent)" }}
                      onClick={() => setDetailId(r.id)}
                    >
                      #{r.id}
                    </button>,
                    r.incident_id,
                    <Badge tone={sevTone(r.severity)}>{r.severity}</Badge>,
                    r.status,
                    r.used_openai ? <Badge tone="ai">LLM</Badge> : <Badge tone="neutral">Rules</Badge>,
                    (r.summary || "—").slice(0, 72),
                    r.created_at ? new Date(r.created_at).toLocaleString() : "—",
                  ])}
                />
              )}
            </GlassPanel>

            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-3">Investigation details</h3>
              {!detailId && (
                <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
                  Select an investigation ID to inspect evidence, ML prediction, agent findings, and approval status.
                </p>
              )}
              {detailLoading && <LoadingBlock label="Loading investigation detail…" />}
              {detail && !detailLoading && (
                <div className="space-y-3 text-sm max-h-[640px] overflow-y-auto pr-1">
                  {detail.ai_message && (
                    <p className="text-xs m-0" style={{ color: "var(--accent-ai)" }}>
                      {detail.ai_message}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <Badge tone="ai">#{detail.investigation.id}</Badge>
                    <Badge tone={sevTone(detail.investigation.severity)}>{detail.investigation.severity}</Badge>
                    <Badge tone="neutral">{detail.investigation.status}</Badge>
                    {detail.investigation.used_openai ? (
                      <Badge tone="ai">OpenAI used</Badge>
                    ) : (
                      <Badge>Rule-based</Badge>
                    )}
                  </div>
                  <div>
                    <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                      Timeline
                    </div>
                    <div className="font-mono text-xs">
                      Start: {detail.investigation.created_at ? new Date(detail.investigation.created_at).toLocaleString() : "—"}
                      <br />
                      Complete:{" "}
                      {detail.investigation.completed_at
                        ? new Date(detail.investigation.completed_at).toLocaleString()
                        : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                      Related attack / IPs
                    </div>
                    <div>
                      {detail.incident?.attack_category || detail.prediction?.attack_category || "—"}
                    </div>
                    <div className="font-mono text-xs">
                      {(detail.incident?.source_ip ||
                        String(detail.investigation.evidence.source_ip || "—")) +
                        " → " +
                        (detail.incident?.dest_ip || String(detail.investigation.evidence.dest_ip || "—"))}
                    </div>
                  </div>
                  {detail.prediction && (
                    <div>
                      <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                        ML prediction
                      </div>
                      <div>
                        {detail.prediction.predicted_label} · confidence{" "}
                        {(detail.prediction.confidence * 100).toFixed(1)}% · severity{" "}
                        {detail.prediction.severity}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                      AI / rule explanation (evidence-bound)
                    </div>
                    <p className="m-0 leading-relaxed">{detail.investigation.explanation || detail.investigation.summary || "—"}</p>
                  </div>
                  <div>
                    <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                      Risk & recommended action
                    </div>
                    <p className="m-0">{detail.investigation.recommended_action || "—"}</p>
                  </div>
                  {detail.investigation.uncertainty_notes?.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                        Hypotheses / uncertainty
                      </div>
                      <ul className="m-0 pl-4">
                        {detail.investigation.uncertainty_notes.map((u, i) => (
                          <li key={i}>{String(u)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {detail.network_event && (
                    <div>
                      <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                        Network event
                      </div>
                      <pre className="text-[11px] font-mono overflow-auto m-0 p-2 rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                        {JSON.stringify(detail.network_event, null, 2)}
                      </pre>
                    </div>
                  )}
                  {detail.traffic_record && (
                    <div>
                      <div className="text-xs font-semibold" style={{ color: "var(--muted)" }}>
                        PCAP / flow evidence
                      </div>
                      <pre className="text-[11px] font-mono overflow-auto m-0 p-2 rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                        {JSON.stringify(detail.traffic_record, null, 2)}
                      </pre>
                    </div>
                  )}
                  <div>
                    <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>
                      Agent executions
                    </div>
                    {(detail.agent_executions || [])
                      .filter((e) => !agentFilter || e.agent_name === agentFilter)
                      .map((e) => (
                        <div key={e.id} className="rounded-lg border px-2 py-1.5 mb-1.5" style={{ borderColor: "var(--border)" }}>
                          <div className="flex justify-between gap-2 text-xs">
                            <span className="font-semibold">{AGENT_TITLES[e.agent_name] || e.agent_name}</span>
                            <span>{e.status} · {e.duration_ms} ms</span>
                          </div>
                          {e.error_message && (
                            <div className="text-[11px]" style={{ color: "var(--critical)" }}>
                              {e.error_message}
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                  <div>
                    <div className="text-xs font-semibold mb-1" style={{ color: "var(--muted)" }}>
                      Approval status
                    </div>
                    {(detail.recommendations || []).length === 0 && (
                      <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
                        No recommendations linked.
                      </p>
                    )}
                    {detail.recommendations.map((r) => (
                      <div key={r.id} className="text-xs mb-1">
                        #{r.id} {r.action_type} · <Badge tone={r.approval_status === "pending" ? "warn" : r.approval_status === "rejected" ? "danger" : "ok"}>{r.approval_status}</Badge>
                      </div>
                    ))}
                    <Link to="/response" className="text-xs font-semibold" style={{ color: "var(--accent)" }}>
                      Open Response Center →
                    </Link>
                  </div>
                  {detail.investigation.error_message && (
                    <p className="text-xs m-0" style={{ color: "var(--warning)" }}>
                      {detail.investigation.error_message}
                    </p>
                  )}
                </div>
              )}
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
}
