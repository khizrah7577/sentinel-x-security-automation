import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  CircularGauge,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
  PageHeader,
} from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

type Prediction = {
  id: number;
  predicted_label: string;
  attack_category: string;
  confidence: number;
  anomaly_score: number | null;
  severity: string;
  model_id: number | null;
  network_event_id: number | null;
  traffic_record_id: number | null;
  evidence_json: string;
  created_at: string;
};

type MlStatus = {
  models_count: number;
  active_model: string | null;
  predictions_count: number;
  message: string;
};

function severityTone(s: string): "neutral" | "ok" | "warn" | "danger" | "info" {
  if (s === "critical" || s === "high") return "danger";
  if (s === "medium") return "warn";
  if (s === "low") return "info";
  return "neutral";
}

function severityColor(s: string) {
  if (s === "critical" || s === "high") return "var(--critical)";
  if (s === "medium") return "var(--warning)";
  return "var(--accent)";
}

function parseEvidence(raw: string) {
  try {
    return JSON.parse(raw || "{}") as Record<string, unknown>;
  } catch {
    return {};
  }
}

export default function DetectionsPage() {
  const { user } = useAuth();
  const [severity, setSeverity] = useState("");
  const [tick, setTick] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const path = useMemo(
    () => `/ml/predictions?limit=100${severity ? `&severity=${severity}` : ""}&_=${tick}`,
    [severity, tick],
  );
  const preds = useApi<Prediction[]>(path, [severity, tick]);
  const status = useApi<MlStatus>(`/ml/status?_=${tick}`, [tick]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selected = preds.data?.find((p) => p.id === selectedId) || preds.data?.[0] || null;
  const evidence = selected ? parseEvidence(selected.evidence_json) : {};

  const runPredict = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const out = await api<{ predictions: number; attacks: number; model_name: string }>(
        "/ml/predict",
        { method: "POST", body: JSON.stringify({ limit: 500 }) },
      );
      setMessage(`Ran ${out.predictions} predictions via ${out.model_name}; attacks=${out.attacks}`);
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Predict failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Network Security"
        title="Threat Intelligence Center"
        description="ML detections with clear separation between confidence scores and threat severity. Evidence is bound to stored prediction fields."
        actions={
          <div className="flex gap-2 items-center flex-wrap">
            <select
              className="rounded-xl border px-3 py-2 text-sm bg-transparent"
              style={{ borderColor: "var(--border)" }}
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="">All severities</option>
              <option value="informational">Informational</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            {user && (
              <Button disabled={busy} onClick={() => void runPredict()}>
                {busy ? "Running…" : "Run ML on flows"}
              </Button>
            )}
          </div>
        }
      />

      {status.data && (
        <GlassPanel>
          <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
            {status.data.message} · Predictions stored: {status.data.predictions_count} · Active:{" "}
            {status.data.active_model || "none"}
          </p>
        </GlassPanel>
      )}
      {message && (
        <p className="text-sm m-0" style={{ color: "var(--accent)" }}>
          {message}
        </p>
      )}
      {error && <ErrorBlock message={error} />}

      {preds.loading && <LoadingBlock />}
      {preds.error && <ErrorBlock message={preds.error} />}
      {preds.data && preds.data.length === 0 && (
        <EmptyState
          title="No detections yet"
          detail="Train a model, process a PCAP, then run ML predictions. Charts and gauges stay empty until real rows exist."
        />
      )}

      {preds.data && preds.data.length > 0 && selected && (
        <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
          <GlassPanel
            className="flex flex-col items-center gap-4"
            glow={selected.severity === "critical" || selected.severity === "high" ? "critical" : undefined}
          >
            <div className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              Selected threat #{selected.id}
            </div>
            <CircularGauge
              value={Math.round(selected.confidence * 100)}
              label="ML confidence"
              color="var(--accent-secondary)"
              sublabel="Model score — not severity"
            />
            <CircularGauge
              value={
                selected.severity === "critical"
                  ? 95
                  : selected.severity === "high"
                    ? 80
                    : selected.severity === "medium"
                      ? 55
                      : selected.severity === "low"
                        ? 30
                        : 10
              }
              label="Severity level"
              color={severityColor(selected.severity)}
              sublabel={`Mapped from stored severity: ${selected.severity}`}
            />
            <div className="w-full space-y-2 text-sm">
              <div>
                <span style={{ color: "var(--muted)" }}>Classification · </span>
                {selected.attack_category || selected.predicted_label}
              </div>
              <div>
                <span style={{ color: "var(--muted)" }}>Source → Dest · </span>
                <span className="font-mono text-xs">
                  {String(evidence.source_ip || "—")} → {String(evidence.dest_ip || "—")}
                </span>
              </div>
              <div>
                <span style={{ color: "var(--muted)" }}>Service / ports · </span>
                <span className="font-mono text-xs">
                  {String(evidence.protocol || "—")} {String(evidence.source_port || "")}:
                  {String(evidence.dest_port || "")}
                </span>
              </div>
              <div className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                {new Date(selected.created_at).toLocaleString()}
              </div>
            </div>
          </GlassPanel>

          <div className="space-y-4">
            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-2">Evidence panel</h3>
              <pre
                className="text-xs font-mono overflow-auto max-h-48 m-0 p-3 rounded-xl border"
                style={{ borderColor: "var(--border)", background: "var(--bg)" }}
              >
                {JSON.stringify(evidence, null, 2)}
              </pre>
            </GlassPanel>

            <GlassPanel className="p-0 overflow-hidden">
              <DataTable
                columns={["ID", "Label", "Category", "Confidence", "Severity", "Time"]}
                rows={preds.data.map((p) => [
                  <button
                    key={p.id}
                    type="button"
                    className="font-mono text-xs"
                    style={{ color: "var(--accent-secondary)" }}
                    onClick={() => setSelectedId(p.id)}
                  >
                    #{p.id}
                  </button>,
                  p.predicted_label === "attack" ? (
                    <Badge tone="danger">{p.predicted_label}</Badge>
                  ) : (
                    <Badge tone="ok">{p.predicted_label}</Badge>
                  ),
                  p.attack_category || "—",
                  `${(p.confidence * 100).toFixed(1)}%`,
                  <Badge tone={severityTone(p.severity)}>{p.severity}</Badge>,
                  new Date(p.created_at).toLocaleString(),
                ])}
              />
            </GlassPanel>
          </div>
        </div>
      )}
    </div>
  );
}
