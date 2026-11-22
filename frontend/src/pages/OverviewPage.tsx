import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  Crosshair,
  Network,
  ShieldAlert,
} from "lucide-react";
import {
  AnalyticsApi,
  DashboardApi,
  type AnalyticsOverview,
  type DashboardStats,
} from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import {
  ErrorBlock,
  MetricCard,
  PageHeader,
  RangeFilter,
  Skeleton,
} from "../components/nexus/primitives";
import {
  ActivityHeatmap,
  ChartCard,
  CompareBarChart,
  DonutChart,
  HBarChart,
  ModelPerfChart,
  TrafficAreaChart,
} from "../components/charts/ChartKit";
import { GlassPanel, Badge } from "../components/nexus/primitives";

export default function OverviewPage() {
  const { user } = useAuth();
  const [range, setRange] = useState("24h");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, a] = await Promise.all([DashboardApi.stats(), AnalyticsApi.overview(range)]);
        if (!cancelled) {
          setStats(s);
          setAnalytics(a);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [range]);

  const spark = useMemo(
    () => (analytics?.time_series || []).map((b) => b.events),
    [analytics],
  );
  const attackSpark = useMemo(
    () => (analytics?.time_series || []).map((b) => b.malicious),
    [analytics],
  );

  const compareData = useMemo(() => {
    if (!analytics?.time_series?.length) return [];
    const normal = analytics.time_series.reduce((a, b) => a + b.normal, 0);
    const malicious = analytics.time_series.reduce((a, b) => a + b.malicious, 0);
    return [{ name: "Selected range", normal, malicious }];
  }, [analytics]);

  const modelChart = useMemo(
    () =>
      (analytics?.model_performance || [])
        .filter((m) => m.accuracy != null || m.f1_score != null)
        .slice(0, 6)
        .map((m) => ({
          name: m.model_type.replace(/_/g, " "),
          accuracy: m.accuracy ?? 0,
          precision: m.precision ?? 0,
          recall: m.recall ?? 0,
          f1: m.f1_score ?? 0,
        })),
    [analytics],
  );

  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="SENTINEL X Operations"
        title={`${greet}, ${user?.full_name?.split(" ")[0] || "Operator"}`}
        description="Live intelligence from PostgreSQL — PCAP ingest, ML detections, agent investigations, and response posture."
        actions={<RangeFilter value={range} onChange={setRange} />}
      />

      {error && <ErrorBlock message={error} />}
      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      )}

      {stats && analytics && !loading && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MetricCard
              label="Total Network Events"
              value={stats.total_network_events}
              icon={<Network className="w-5 h-5" />}
              accent="var(--accent-secondary)"
              sparkline={spark}
              hint={`${analytics.counts.events} in selected range`}
            />
            <MetricCard
              label="Normal Traffic"
              value={stats.normal_traffic}
              icon={<Activity className="w-5 h-5" />}
              accent="var(--accent)"
              sparkline={(analytics.time_series || []).map((b) => b.normal)}
            />
            <MetricCard
              label="Detected Attacks"
              value={stats.detected_attacks}
              icon={<Crosshair className="w-5 h-5" />}
              accent="var(--critical)"
              sparkline={attackSpark}
              hint={`${analytics.counts.attack_predictions} attack predictions in range`}
            />
            <MetricCard
              label="Critical Threats"
              value={stats.critical_incidents}
              icon={<ShieldAlert className="w-5 h-5" />}
              accent="var(--critical)"
            />
            <MetricCard
              label="Pending Responses"
              value={stats.pending_approvals}
              icon={<AlertTriangle className="w-5 h-5" />}
              accent="var(--warning)"
              hint={`${analytics.counts.pending_responses} awaiting approval`}
            />
            <MetricCard
              label="Active Investigations"
              value={analytics.counts.investigations_running}
              icon={<Bot className="w-5 h-5" />}
              accent="var(--accent-ai)"
              hint={`${analytics.counts.investigations_total} total investigations`}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartCard
              title="Network Traffic Over Time"
              subtitle="Bucketed from real events and flows"
              empty={!analytics.has_time_series}
            >
              <TrafficAreaChart data={analytics.time_series} />
            </ChartCard>
            <ChartCard title="Normal vs Malicious Traffic" empty={!compareData.length}>
              <CompareBarChart data={compareData} />
            </ChartCard>
            <ChartCard
              title="Attack Distribution"
              subtitle="Attack categories from ML predictions"
              empty={!analytics.attack_categories.length}
            >
              <DonutChart data={analytics.attack_categories} />
            </ChartCard>
            <ChartCard title="Threat Severity Distribution" empty={!analytics.severity_distribution.length}>
              <HBarChart data={analytics.severity_distribution} />
            </ChartCard>
            <ChartCard title="Protocol Distribution" empty={!analytics.protocol_distribution.length}>
              <DonutChart data={analytics.protocol_distribution} />
            </ChartCard>
            <ChartCard
              title="ML Model Performance"
              subtitle="Accuracy / precision / recall / F1 from training results"
              empty={!modelChart.length}
            >
              <ModelPerfChart data={modelChart} />
            </ChartCard>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ChartCard
              title="Network Activity Heatmap"
              subtitle="Day × hour intensity from observed timestamps"
              empty={!analytics.has_heatmap_data}
            >
              <ActivityHeatmap cells={analytics.heatmap} />
            </ChartCard>
            <GlassPanel>
              <h3 className="text-sm font-bold m-0 mb-3">Detection Timeline</h3>
              {analytics.detection_timeline.length === 0 ? (
                <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
                  No detections in this range.
                </p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {analytics.detection_timeline.map((d) => (
                    <div
                      key={d.id}
                      className="flex items-start justify-between gap-3 rounded-xl border px-3 py-2"
                      style={{ borderColor: "var(--border)" }}
                    >
                      <div>
                        <div className="text-sm font-semibold">{d.category || d.label}</div>
                        <div className="text-xs font-mono mt-0.5" style={{ color: "var(--muted)" }}>
                          {new Date(d.t).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge
                          tone={
                            d.severity === "critical" || d.severity === "high"
                              ? "danger"
                              : d.severity === "medium"
                                ? "warn"
                                : "info"
                          }
                        >
                          {d.severity}
                        </Badge>
                        <span className="text-xs font-mono">{(d.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </GlassPanel>
          </div>
        </>
      )}
    </div>
  );
}
