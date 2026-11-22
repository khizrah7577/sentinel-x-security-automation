import { useRef, useState } from "react";
import { Badge, DataTable, EmptyState, ErrorBlock, LoadingBlock, PageHeader, Card } from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

type Dataset = {
  id: number;
  name: string;
  source: string;
  row_count: number;
  column_count: number;
  status: string;
  missing_values: number;
  duplicate_records: number;
  label_distribution_json: string;
  notes: string;
  created_at: string;
};

export default function DatasetsPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const datasets = useApi<Dataset[]>(`/ml/datasets?_=${tick}`, [tick]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ensureBaseline = async () => {
    setBusy(true);
    setError(null);
    try {
      const ds = await api<Dataset>("/ml/datasets/baseline", { method: "POST" });
      setMessage(`Baseline ready: ${ds.name} (${ds.row_count} rows)`);
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  };

  const uploadCsv = async (file: File) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const ds = await api<Dataset>("/ml/datasets/import", {
        method: "POST",
        body,
      });
      setMessage(`Imported ${ds.name}: ${ds.row_count} rows`);
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dataset Management"
        description="Local synthetic baseline for training. Optional CSV import (CICIDS-compatible columns). Large CICIDS download is not automatic."
      />

      {user?.role === "admin" && (
        <Card className="space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <button
              type="button"
              className="rounded-md px-4 py-2 text-sm text-white"
              style={{ background: "var(--accent)" }}
              disabled={busy}
              onClick={() => void ensureBaseline()}
            >
              {busy ? "Working…" : "Ensure synthetic baseline dataset"}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              disabled={busy}
              className="text-sm"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void uploadCsv(f);
              }}
            />
          </div>
          {message && <p className="text-sm m-0" style={{ color: "var(--accent)" }}>{message}</p>}
          {error && <ErrorBlock message={error} />}
          <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
            Datasets are stored under D:\CyberSecurity_FYP\ml\datasets
          </p>
        </Card>
      )}

      {datasets.loading && <LoadingBlock />}
      {datasets.error && <ErrorBlock message={datasets.error} />}
      {datasets.data && datasets.data.length === 0 && (
        <EmptyState
          title="No datasets imported"
          detail="Admin: create the synthetic baseline, or upload a labelled CSV. CICIDS2017 is optional and must be provided manually."
        />
      )}
      {datasets.data && datasets.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Source", "Rows", "Missing", "Duplicates", "Labels", "Status"]}
          rows={datasets.data.map((d) => [
            d.id,
            d.name,
            d.source,
            d.row_count,
            d.missing_values,
            d.duplicate_records,
            d.label_distribution_json,
            <Badge>{d.status}</Badge>,
          ])}
        />
      )}
    </div>
  );
}
