import { useRef, useState } from "react";
import { Link } from "react-router-dom";
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
import { ChartCard, DonutChart } from "../components/charts/ChartKit";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";

type Pcap = {
  id: number;
  original_filename: string;
  file_size_bytes: number;
  sha256: string;
  status: string;
  is_demo: boolean;
  error_message: string;
  created_at: string;
};

type Traffic = {
  id: number;
  source_ip: string;
  dest_ip: string;
  source_port: number;
  dest_port: number;
  protocol: string;
  duration: number;
  packet_count: number;
  bytes_transferred: number;
  connection_state: string;
  label: string;
};

type ProcessResult = {
  pcap_id: number;
  status: string;
  flows: number;
  suspicious_flows: number;
  extractor: string;
  zeek: { used?: boolean; message?: string; available?: boolean };
  is_demo: boolean;
  monitoring_mode: string;
};

type NetStatus = {
  monitoring_mode: string;
  zeek_available: boolean;
  extractor_primary: string;
  max_upload_bytes: number;
  message: string;
};

type Stats = {
  traffic_records: number;
  normal: number;
  suspicious: number;
  attack: number;
  protocol_distribution: Record<string, number>;
  pcap_files: number;
  network_events: number;
};

const PIPELINE = [
  "Upload",
  "Validation",
  "Zeek / Scapy",
  "Feature Extraction",
  "ML Detection",
  "AI Investigation",
  "Report",
] as const;

export default function PcapPage() {
  const [tick, setTick] = useState(0);
  const pcaps = useApi<Pcap[]>(`/network/pcaps?_=${tick}`, [tick]);
  const status = useApi<NetStatus>("/network/status");
  const stats = useApi<Stats>(`/network/stats?_=${tick}`, [tick]);
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [processInfo, setProcessInfo] = useState<ProcessResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const traffic = useApi<Traffic[]>(
    selectedId ? `/network/pcaps/${selectedId}/traffic?limit=200` : null,
    [selectedId, tick],
  );

  const selected = pcaps.data?.find((p) => p.id === selectedId) || null;

  const stageIndex = (() => {
    if (!selected) return -1;
    if (selected.status === "uploaded") return 1;
    if (selected.status === "processing") return 3;
    if (selected.status === "failed") return 1;
    if (selected.status === "processed") return processInfo ? 4 : 3;
    return 0;
  })();

  const refresh = () => setTick((t) => t + 1);

  const upload = async (file: File) => {
    setBusy("upload");
    setError(null);
    setMessage(null);
    try {
      const token = localStorage.getItem("csfyp_token");
      const body = new FormData();
      body.append("file", file);
      const res = await fetch("/api/v1/network/pcaps/upload", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Upload failed (${res.status})`);
      }
      const row = (await res.json()) as Pcap;
      setMessage(`Uploaded ${row.original_filename} (id ${row.id}). Click Process to extract flows.`);
      setSelectedId(row.id);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const createDemo = async () => {
    setBusy("demo");
    setError(null);
    setMessage(null);
    try {
      const row = await api<Pcap>("/network/pcaps/demo", { method: "POST" });
      setMessage(`Demo PCAP ready (id ${row.id}). Clearly labelled is_demo=true.`);
      setSelectedId(row.id);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Demo creation failed");
    } finally {
      setBusy(null);
    }
  };

  const process = async (id: number) => {
    setBusy(`process-${id}`);
    setError(null);
    setMessage(null);
    try {
      const result = await api<ProcessResult>(`/network/pcaps/${id}/process`, { method: "POST" });
      setProcessInfo(result);
      setSelectedId(id);
      setMessage(
        `Processed PCAP #${id}: ${result.flows} flows, ${result.suspicious_flows} suspicious (extractor: ${result.extractor}).`,
      );
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Processing failed");
    } finally {
      setBusy(null);
    }
  };

  const protocolData = Object.entries(stats.data?.protocol_distribution || {}).map(([name, value]) => ({
    name,
    value: Number(value),
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Network Security"
        title="PCAP Analysis"
        description="Offline capture pipeline: upload → validate → extract → detect → investigate → report."
      />

      <GlassPanel>
        <div className="flex flex-wrap gap-2">
          {PIPELINE.map((step, i) => {
            const active = i <= stageIndex;
            return (
              <div key={step} className="flex items-center gap-2">
                <div
                  className="rounded-full px-3 py-1 text-[11px] font-bold border"
                  style={{
                    borderColor: active ? "var(--accent)" : "var(--border)",
                    background: active ? "var(--accent-soft)" : "transparent",
                    color: active ? "var(--accent)" : "var(--muted)",
                  }}
                >
                  {i + 1}. {step}
                </div>
                {i < PIPELINE.length - 1 && (
                  <div className="w-4 h-px hidden sm:block" style={{ background: "var(--border)" }} />
                )}
              </div>
            );
          })}
        </div>
        <p className="text-xs mt-3 mb-0" style={{ color: "var(--muted)" }}>
          Stages advance from real PCAP status and process results. Later stages (ML / AI / Report) are linked actions — not auto-faked.
        </p>
      </GlassPanel>

      {status.data && (
        <GlassPanel>
          <div className="grid gap-2 text-sm md:grid-cols-2">
            <div>
              Mode: <strong>{status.data.monitoring_mode}</strong>
            </div>
            <div>
              Primary extractor: <strong>{status.data.extractor_primary}</strong>
            </div>
            <div>
              Zeek:{" "}
              <Badge tone={status.data.zeek_available ? "ok" : "warn"}>
                {status.data.zeek_available ? "Available" : "Not installed — Scapy fallback"}
              </Badge>
            </div>
            <div>Max upload: {(status.data.max_upload_bytes / (1024 * 1024)).toFixed(0)} MB</div>
          </div>
        </GlassPanel>
      )}

      <div
        className="rounded-[var(--radius)] border-2 border-dashed p-8 text-center transition-colors"
        style={{
          borderColor: dragOver ? "var(--accent)" : "var(--border)",
          background: dragOver ? "var(--accent-soft)" : "var(--surface)",
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) void upload(f);
        }}
      >
        <div className="text-lg font-bold">Drop PCAP here</div>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          .pcap / .pcapng / .cap — or choose a file / create labelled demo
        </p>
        <div className="flex flex-wrap gap-2 justify-center mt-4">
          <input
            ref={fileRef}
            type="file"
            accept=".pcap,.pcapng,.cap"
            className="text-sm"
            disabled={busy !== null}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void upload(f);
            }}
          />
          <Button variant="secondary" disabled={busy !== null} onClick={() => void createDemo()}>
            {busy === "demo" ? "Creating…" : "Create labelled demo PCAP"}
          </Button>
        </div>
        {message && (
          <p className="text-sm mt-3 mb-0" style={{ color: "var(--accent)" }}>
            {message}
          </p>
        )}
        {error && <ErrorBlock message={error} />}
      </div>

      {stats.data && (
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["PCAPs", stats.data.pcap_files],
              ["Flows", stats.data.traffic_records],
              ["Suspicious", stats.data.suspicious],
              ["Events", stats.data.network_events],
            ].map(([label, value]) => (
              <GlassPanel key={String(label)} className="py-4">
                <div className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
                  {label}
                </div>
                <div className="text-2xl font-bold mt-1">{value}</div>
              </GlassPanel>
            ))}
          </div>
          <ChartCard title="Protocol distribution" empty={!protocolData.length}>
            <DonutChart data={protocolData} />
          </ChartCard>
        </div>
      )}

      {processInfo && (
        <GlassPanel>
          <h3 className="text-sm font-semibold m-0 mb-2">Last process result</h3>
          <p className="text-sm m-0">
            Flows: {processInfo.flows} · Suspicious: {processInfo.suspicious_flows} · Extractor:{" "}
            {processInfo.extractor}
            {processInfo.is_demo ? " · Demo capture" : ""}
          </p>
          <p className="text-sm mt-2 mb-3" style={{ color: "var(--muted)" }}>
            Zeek: {processInfo.zeek?.message || "n/a"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Link to="/detections">
              <Button variant="secondary">Open ML detections</Button>
            </Link>
            <Link to="/investigations">
              <Button variant="ai">AI investigation</Button>
            </Link>
            <Link to="/reports">
              <Button variant="ghost">Reports</Button>
            </Link>
          </div>
        </GlassPanel>
      )}

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">Stored captures</h2>
        {pcaps.loading && <LoadingBlock />}
        {pcaps.error && <ErrorBlock message={pcaps.error} />}
        {pcaps.data && pcaps.data.length === 0 && (
          <EmptyState
            title="No PCAP files stored"
            detail="Upload a capture or create the labelled demo. Files live on D:\\CyberSecurity_FYP\\data\\pcaps."
          />
        )}
        {pcaps.data && pcaps.data.length > 0 && (
          <DataTable
            columns={["ID", "Filename", "Size", "Status", "Demo", "Actions", "Uploaded"]}
            rows={pcaps.data.map((p) => [
              p.id,
              <button
                key={p.id}
                type="button"
                className="underline text-left"
                style={{ color: "var(--accent)" }}
                onClick={() => setSelectedId(p.id)}
              >
                {p.original_filename}
              </button>,
              `${(p.file_size_bytes / 1024).toFixed(1)} KB`,
              <Badge tone={p.status === "failed" ? "danger" : p.status === "processed" ? "ok" : "info"}>
                {p.status}
              </Badge>,
              p.is_demo ? <Badge tone="warn">Demo</Badge> : "No",
              <Button
                variant="secondary"
                disabled={busy !== null}
                onClick={() => void process(p.id)}
              >
                {busy === `process-${p.id}` ? "Processing…" : "Process"}
              </Button>,
              new Date(p.created_at).toLocaleString(),
            ])}
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">
          Suspicious / extracted flows {selectedId ? `(PCAP #${selectedId})` : ""}
        </h2>
        {!selectedId && (
          <EmptyState title="Select a PCAP" detail="Click a filename or process a capture to inspect flows." />
        )}
        {selectedId && traffic.loading && <LoadingBlock label="Loading flows…" />}
        {selectedId && traffic.error && <ErrorBlock message={traffic.error} />}
        {selectedId && traffic.data && traffic.data.length === 0 && (
          <EmptyState title="No flows yet" detail="Click Process to extract flow features." />
        )}
        {traffic.data && traffic.data.length > 0 && (
          <DataTable
            columns={["Src", "Dst", "Proto", "Pkts", "Bytes", "Duration", "State", "Label"]}
            rows={traffic.data.map((t) => [
              `${t.source_ip}:${t.source_port}`,
              `${t.dest_ip}:${t.dest_port}`,
              t.protocol,
              t.packet_count,
              t.bytes_transferred,
              t.duration.toFixed(3),
              t.connection_state,
              t.label === "suspicious" || t.label === "attack" ? (
                <Badge tone="danger">{t.label}</Badge>
              ) : (
                <Badge tone="ok">{t.label}</Badge>
              ),
            ])}
          />
        )}
      </section>
    </div>
  );
}
