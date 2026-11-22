import { useState } from "react";
import { Card, ErrorBlock, LoadingBlock, PageHeader } from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";

type Summary = {
  generated_at: string;
  network_events: number;
  incidents: number;
  predictions: number;
  ml_models: number;
  note: string;
  product?: string;
};

export default function ReportsPage() {
  const summary = useApi<Summary>("/reports/summary");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const download = async (kind: "csv" | "json") => {
    setBusy(kind);
    setError(null);
    try {
      const token = localStorage.getItem("csfyp_token");
      const res = await fetch(`/api/v1/reports/incidents.${kind}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentinel_x_incidents_report.${kind}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        eyebrow="SENTINEL X"
        title="Reports"
        description="Export real database content. Empty exports are valid when no incidents exist."
      />

      {summary.loading && <LoadingBlock />}
      {summary.error && <ErrorBlock message={summary.error} />}
      {summary.data && (
        <Card>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>Network events: <strong>{summary.data.network_events}</strong></div>
            <div>Incidents: <strong>{summary.data.incidents}</strong></div>
            <div>Predictions: <strong>{summary.data.predictions}</strong></div>
            <div>ML models: <strong>{summary.data.ml_models}</strong></div>
          </div>
          <p className="text-sm mt-3 mb-0" style={{ color: "var(--muted)" }}>
            {summary.data.note}
          </p>
          <p className="text-xs mt-2 mb-0" style={{ color: "var(--muted)" }}>
            Generated at {new Date(summary.data.generated_at).toLocaleString()}
          </p>
        </Card>
      )}

      <Card className="space-y-3">
        <h2 className="text-base font-semibold m-0">Incident export</h2>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md px-4 py-2 text-sm text-white"
            style={{ background: "var(--accent)" }}
            disabled={busy !== null}
            onClick={() => void download("csv")}
          >
            {busy === "csv" ? "Preparing…" : "Download CSV"}
          </button>
          <button
            type="button"
            className="rounded-md border px-4 py-2 text-sm"
            style={{ borderColor: "var(--border)" }}
            disabled={busy !== null}
            onClick={() => void download("json")}
          >
            {busy === "json" ? "Preparing…" : "Download JSON"}
          </button>
        </div>
        {error && <ErrorBlock message={error} />}
        <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
          PDF pack is added with Phase 8/9 reporting polish; CSV/JSON already use live DB rows.
        </p>
      </Card>
    </div>
  );
}
