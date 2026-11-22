import { Badge, Card, EmptyState, ErrorBlock, LoadingBlock, PageHeader, DataTable } from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";

type Status = {
  monitoring_mode: string;
  zeek_enabled: boolean;
  live_capture_available: boolean;
  message: string;
};

type Event = {
  id: number;
  event_type: string;
  source_ip: string;
  dest_ip: string;
  source_port: number;
  dest_port: number;
  protocol: string;
  summary: string;
  is_suspicious: boolean;
  is_demo: boolean;
  monitoring_mode: string;
  created_at: string;
};

export default function MonitoringPage() {
  const status = useApi<Status>("/network/status");
  const events = useApi<Event[]>("/network/events?limit=50");
  const stats = useApi<{
    traffic_records: number;
    normal: number;
    suspicious: number;
    protocol_distribution: Record<string, number>;
  }>("/network/stats");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Network Monitoring"
        description="Offline/PCAP-first monitoring status and recent network events from the database."
      />

      {status.loading && <LoadingBlock />}
      {status.error && <ErrorBlock message={status.error} />}
      {status.data && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Mode</div>
            <div className="mt-1 font-semibold capitalize">{status.data.monitoring_mode}</div>
          </Card>
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Zeek</div>
            <div className="mt-1">
              <Badge tone={status.data.zeek_enabled ? "ok" : "warn"}>
                {status.data.zeek_enabled ? "Enabled" : "Not configured"}
              </Badge>
            </div>
          </Card>
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Live capture</div>
            <div className="mt-1">
              <Badge tone={status.data.live_capture_available ? "ok" : "neutral"}>
                {status.data.live_capture_available ? "Available" : "Unavailable"}
              </Badge>
            </div>
          </Card>
        </div>
      )}

      {status.data && (
        <Card>
          <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
            {status.data.message}
          </p>
        </Card>
      )}

      {stats.data && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Flows</div>
            <div className="text-xl font-semibold mt-1">{stats.data.traffic_records}</div>
          </Card>
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Normal</div>
            <div className="text-xl font-semibold mt-1">{stats.data.normal}</div>
          </Card>
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Suspicious</div>
            <div className="text-xl font-semibold mt-1">{stats.data.suspicious}</div>
          </Card>
          <Card>
            <div className="text-xs" style={{ color: "var(--muted)" }}>Protocols</div>
            <div className="text-sm mt-2">
              {Object.entries(stats.data.protocol_distribution || {}).length === 0
                ? "—"
                : Object.entries(stats.data.protocol_distribution)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ")}
            </div>
          </Card>
        </div>
      )}

      <div>
        <h2 className="text-base font-semibold mb-3">Recent events</h2>
        {events.loading && <LoadingBlock />}
        {events.error && <ErrorBlock message={events.error} />}
        {events.data && events.data.length === 0 && (
          <EmptyState
            title="No network events yet"
            detail="Upload a PCAP under PCAP Analysis or ingest offline traffic. This panel does not invent live traffic."
          />
        )}
        {events.data && events.data.length > 0 && (
          <DataTable
            columns={["ID", "Source", "Destination", "Protocol", "Flags", "Mode", "Summary"]}
            rows={events.data.map((e) => [
              e.id,
              `${e.source_ip}:${e.source_port}`,
              `${e.dest_ip}:${e.dest_port}`,
              e.protocol || "—",
              e.is_suspicious ? <Badge tone="danger">Suspicious</Badge> : <Badge tone="ok">Normal</Badge>,
              e.monitoring_mode,
              e.summary || e.event_type,
            ])}
          />
        )}
      </div>
    </div>
  );
}
