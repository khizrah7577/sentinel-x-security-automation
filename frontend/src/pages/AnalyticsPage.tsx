import { useEffect, useState } from "react";
import { AnalyticsApi, type AnalyticsOverview } from "../services/api";
import {
  DataTable,
  ErrorBlock,
  GlassPanel,
  PageHeader,
  RangeFilter,
  Skeleton,
} from "../components/nexus/primitives";
import {
  ActivityHeatmap,
  ChartCard,
  DonutChart,
  HBarChart,
  SimpleLineChart,
  TrafficAreaChart,
} from "../components/charts/ChartKit";

export default function AnalyticsPage() {
  const [range, setRange] = useState("24h");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const useCustom = range === "custom" && customStart && customEnd;
        const a = await AnalyticsApi.overview(
          useCustom ? "custom" : range === "custom" ? "24h" : range,
          useCustom ? new Date(customStart).toISOString() : undefined,
          useCustom ? new Date(customEnd).toISOString() : undefined,
        );
        if (!cancelled) setData(a);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Analytics failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [range, customStart, customEnd]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Network Security"
        title="Threat Analytics"
        description="Attack frequency, categories, heatmap, talkers, and ports — aggregated from stored traffic and ML predictions."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <RangeFilter
              value={range === "custom" ? "24h" : range}
              onChange={(v) => setRange(v)}
            />
            <button
              type="button"
              className="rounded-lg border px-2.5 py-1.5 text-xs font-semibold"
              style={{
                borderColor: "var(--border)",
                color: range === "custom" ? "var(--accent)" : "var(--muted)",
                background: range === "custom" ? "var(--accent-soft)" : "transparent",
              }}
              onClick={() => setRange("custom")}
            >
              Custom
            </button>
          </div>
        }
      />

      {range === "custom" && (
        <GlassPanel className="flex flex-wrap gap-3 items-end">
          <label className="text-xs space-y-1">
            <span style={{ color: "var(--muted)" }}>Start</span>
            <input
              type="datetime-local"
              className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
            />
          </label>
          <label className="text-xs space-y-1">
            <span style={{ color: "var(--muted)" }}>End</span>
            <input
              type="datetime-local"
              className="block rounded-lg border px-2 py-1.5 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
            />
          </label>
        </GlassPanel>
      )}

      {error && <ErrorBlock message={error} />}
      {loading && <Skeleton className="h-64" />}

      {data && !loading && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Attack predictions", data.counts.attack_predictions],
              ["Incidents", data.counts.incidents],
              ["Traffic flows", data.counts.traffic_flows],
              ["Events", data.counts.events],
            ].map(([label, value]) => (
              <GlassPanel key={String(label)} className="py-4">
                <div className="text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
                  {label}
                </div>
                <div className="text-2xl font-bold mt-1 tabular-nums">{value as number}</div>
              </GlassPanel>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartCard title="Attack Frequency" empty={!data.has_time_series}>
              <TrafficAreaChart data={data.time_series} />
            </ChartCard>
            <ChartCard title="Attack Category Distribution" empty={!data.attack_categories.length}>
              <DonutChart data={data.attack_categories} />
            </ChartCard>
            <ChartCard title="Attack Heatmap" empty={!data.has_heatmap_data}>
              <ActivityHeatmap cells={data.heatmap} />
            </ChartCard>
            <ChartCard title="Incident Frequency" empty={!data.incident_series.length}>
              <SimpleLineChart data={data.incident_series} />
            </ChartCard>
            <ChartCard title="Protocol Analysis" empty={!data.protocol_distribution.length}>
              <DonutChart data={data.protocol_distribution} />
            </ChartCard>
            <ChartCard title="Severity" empty={!data.severity_distribution.length}>
              <HBarChart data={data.severity_distribution} />
            </ChartCard>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-3">Top Source IPs</h3>
              {data.top_source_ips.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  No source IP data in range.
                </p>
              ) : (
                <DataTable
                  columns={["Source IP", "Count"]}
                  rows={data.top_source_ips.map((r) => [
                    <span key={r.ip} className="font-mono text-xs">
                      {r.ip}
                    </span>,
                    r.count,
                  ])}
                />
              )}
            </GlassPanel>
            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-3">Most Targeted Ports</h3>
              {data.top_dest_ports.length === 0 ? (
                <p className="text-sm" style={{ color: "var(--muted)" }}>
                  No destination port data in range.
                </p>
              ) : (
                <DataTable
                  columns={["Port", "Count"]}
                  rows={data.top_dest_ports.map((r) => [r.port, r.count])}
                />
              )}
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
}
