import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
  PageHeader,
} from "../components/nexus/primitives";
import { ChartCard, ConfusionMatrix, ModelPerfChart } from "../components/charts/ChartKit";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

type Model = {
  id: number;
  name: string;
  model_type: string;
  version: string;
  is_active: boolean;
  metrics_json: string;
  description: string;
  created_at: string;
};

type Run = {
  id: number;
  model_type: string;
  status: string;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1_score: number | null;
  duration_seconds: number | null;
  confusion_matrix_json: string;
  created_at: string;
};

type Status = {
  models_count: number;
  datasets_count: number;
  predictions_count: number;
  active_model: string | null;
  message: string;
};

function parseMetrics(raw: string) {
  try {
    return JSON.parse(raw || "{}") as Record<string, unknown>;
  } catch {
    return {};
  }
}

function parseMatrix(raw: string): number[][] | null {
  try {
    const v = JSON.parse(raw || "null");
    if (Array.isArray(v) && Array.isArray(v[0])) return v as number[][];
    if (v && Array.isArray(v.matrix)) return v.matrix as number[][];
    return null;
  } catch {
    return null;
  }
}

export default function ModelsPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const status = useApi<Status>(`/ml/status?_=${tick}`, [tick]);
  const models = useApi<Model[]>(`/ml/models?_=${tick}`, [tick]);
  const runs = useApi<Run[]>(`/ml/training-runs?_=${tick}`, [tick]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [matrixRunId, setMatrixRunId] = useState<number | null>(null);

  const refresh = () => setTick((t) => t + 1);

  const chartData = useMemo(() => {
    return (models.data || [])
      .map((m) => {
        const metrics = parseMetrics(m.metrics_json);
        return {
          name: m.model_type.replace(/_/g, " "),
          accuracy: typeof metrics.accuracy === "number" ? metrics.accuracy : 0,
          precision: typeof metrics.precision === "number" ? metrics.precision : 0,
          recall: typeof metrics.recall === "number" ? metrics.recall : 0,
          f1: typeof metrics.f1_score === "number" ? metrics.f1_score : 0,
          has: typeof metrics.f1_score === "number" || typeof metrics.accuracy === "number",
        };
      })
      .filter((r) => r.has);
  }, [models.data]);

  const selectedRun =
    runs.data?.find((r) => r.id === matrixRunId) ||
    runs.data?.find((r) => parseMatrix(r.confusion_matrix_json)) ||
    null;
  const matrix = selectedRun ? parseMatrix(selectedRun.confusion_matrix_json) : null;

  const trainOne = async (model_type: string) => {
    setBusy(model_type);
    setError(null);
    setMessage(null);
    try {
      const out = await api<{
        metrics: { accuracy: number; precision: number; recall: number; f1_score: number };
        model: Model;
      }>("/ml/train", {
        method: "POST",
        body: JSON.stringify({ model_type, activate: true }),
      });
      setMessage(
        `Trained ${out.model.name}: F1=${out.metrics.f1_score.toFixed(3)}, accuracy=${out.metrics.accuracy.toFixed(3)}`,
      );
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Training failed");
    } finally {
      setBusy(null);
    }
  };

  const trainAll = async () => {
    setBusy("all");
    setError(null);
    setMessage(null);
    try {
      const out = await api<{
        activated_model_name: string | null;
        results: { model_type: string; metrics?: { f1_score: number }; error?: string }[];
      }>("/ml/train-all", { method: "POST" });
      const lines = out.results
        .map((r) =>
          r.error
            ? `${r.model_type}: ERROR ${r.error}`
            : `${r.model_type}: F1=${(r.metrics?.f1_score ?? 0).toFixed(3)}`,
        )
        .join(" · ");
      setMessage(`Trained all. Activated: ${out.activated_model_name || "none"}. ${lines}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Training failed");
    } finally {
      setBusy(null);
    }
  };

  const activate = async (id: number) => {
    setBusy(`activate-${id}`);
    setError(null);
    try {
      await api(`/ml/models/${id}/activate`, { method: "POST" });
      setMessage(`Activated model #${id}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Activate failed");
    } finally {
      setBusy(null);
    }
  };

  const predict = async () => {
    setBusy("predict");
    setError(null);
    try {
      const out = await api<{ predictions: number; attacks: number; model_name: string }>(
        "/ml/predict",
        { method: "POST", body: JSON.stringify({ limit: 500 }) },
      );
      setMessage(`Predicted ${out.predictions} flows with ${out.model_name}: ${out.attacks} labelled attack`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Predict failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Intelligence"
        title="ML Model Management"
        description="Random Forest, SVM, and Isolation Forest — metrics from real training runs only. ROC and feature importance are unavailable until the training pipeline produces them."
      />

      {status.data && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ["Models", status.data.models_count],
            ["Datasets", status.data.datasets_count],
            ["Predictions", status.data.predictions_count],
            ["Active", status.data.active_model || "None"],
          ].map(([label, value]) => (
            <GlassPanel key={String(label)} className="py-4">
              <div className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
                {label}
              </div>
              <div className="text-xl font-bold mt-1 truncate">{value}</div>
            </GlassPanel>
          ))}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard title="Model comparison" subtitle="Accuracy / precision / recall / F1" empty={!chartData.length}>
          <ModelPerfChart data={chartData} />
        </ChartCard>
        <GlassPanel>
          <h3 className="text-sm font-bold m-0 mb-2">Confusion matrix</h3>
          {!matrix ? (
            <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
              No confusion matrix stored yet. Train a model to populate evaluation matrices.
            </p>
          ) : (
            <>
              <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
                From training run #{selectedRun?.id} ({selectedRun?.model_type})
              </p>
              <ConfusionMatrix matrix={matrix} />
            </>
          )}
          <GlassPanel className="mt-4 p-3" style={{ background: "var(--bg)" }}>
            <div className="text-xs font-semibold mb-1">Not available in current pipeline</div>
            <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
              ROC curves and feature-importance charts are intentionally empty — those artifacts are not computed or stored by the trainer today.
            </p>
          </GlassPanel>
        </GlassPanel>
      </div>

      {user?.role === "admin" ? (
        <GlassPanel className="space-y-3">
          <h2 className="text-base font-semibold m-0">Training controls</h2>
          <div className="flex flex-wrap gap-2">
            {["random_forest", "svm", "isolation_forest"].map((t) => (
              <Button key={t} variant="secondary" disabled={busy !== null} onClick={() => void trainOne(t)}>
                {busy === t ? "Training…" : `Train ${t}`}
              </Button>
            ))}
            <Button disabled={busy !== null} onClick={() => void trainAll()}>
              {busy === "all" ? "Training all…" : "Train all + activate best F1"}
            </Button>
            <Button variant="secondary" disabled={busy !== null} onClick={() => void predict()}>
              {busy === "predict" ? "Predicting…" : "Run predictions on flows"}
            </Button>
          </div>
          {message && (
            <p className="text-sm m-0" style={{ color: "var(--accent)" }}>
              {message}
            </p>
          )}
          {error && <ErrorBlock message={error} />}
        </GlassPanel>
      ) : (
        <GlassPanel>
          <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
            Analysts can view models. Admin role is required to train or activate.
          </p>
        </GlassPanel>
      )}

      <h2 className="text-base font-semibold m-0">Saved models</h2>
      {models.loading && <LoadingBlock />}
      {models.error && <ErrorBlock message={models.error} />}
      {models.data && models.data.length === 0 && (
        <EmptyState title="No models trained" detail="Admin: train RF, SVM, and Isolation Forest to create artifacts on D:." />
      )}
      {models.data && models.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Type", "F1", "Accuracy", "Active", "Actions"]}
          rows={models.data.map((m) => {
            const metrics = parseMetrics(m.metrics_json);
            return [
              m.id,
              m.name,
              m.model_type,
              typeof metrics.f1_score === "number" ? metrics.f1_score.toFixed(3) : "—",
              typeof metrics.accuracy === "number" ? metrics.accuracy.toFixed(3) : "—",
              m.is_active ? <Badge tone="ok">Active</Badge> : <Badge>Inactive</Badge>,
              user?.role === "admin" && !m.is_active ? (
                <Button variant="secondary" disabled={busy !== null} onClick={() => void activate(m.id)}>
                  Activate
                </Button>
              ) : (
                "—"
              ),
            ];
          })}
        />
      )}

      <h2 className="text-base font-semibold m-0">Training run history</h2>
      {runs.data && runs.data.length === 0 && (
        <EmptyState title="No training runs" detail="Metrics appear after a successful train job." />
      )}
      {runs.data && runs.data.length > 0 && (
        <DataTable
          columns={["ID", "Type", "Status", "Accuracy", "Precision", "Recall", "F1", "Matrix"]}
          rows={runs.data.map((r) => [
            r.id,
            r.model_type,
            r.status,
            r.accuracy?.toFixed(3) ?? "—",
            r.precision?.toFixed(3) ?? "—",
            r.recall?.toFixed(3) ?? "—",
            r.f1_score?.toFixed(3) ?? "—",
            parseMatrix(r.confusion_matrix_json) ? (
              <button
                type="button"
                className="text-xs font-semibold"
                style={{ color: "var(--accent-secondary)" }}
                onClick={() => setMatrixRunId(r.id)}
              >
                View
              </button>
            ) : (
              "—"
            ),
          ])}
        />
      )}
    </div>
  );
}
