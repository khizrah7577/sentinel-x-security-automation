import { useMemo, useState } from "react";
import { useApi } from "../hooks/useApi";
import { Badge, DataTable, EmptyState, ErrorBlock, GlassPanel, LoadingBlock, PageHeader } from "../components/nexus/primitives";

type Incident = {
  id: number;
  title: string;
  description: string;
  severity: string;
  status: string;
  source_ip: string;
  dest_ip: string;
  attack_category: string;
  created_at: string;
};

function tone(sev: string) {
  if (sev === "critical" || sev === "high") return "danger" as const;
  if (sev === "medium") return "warn" as const;
  if (sev === "low") return "info" as const;
  return "neutral" as const;
}

export default function IncidentsPage() {
  const [tick, setTick] = useState(0);
  const incidents = useApi<Incident[]>(`/incidents?_=${tick}`, [tick]);
  const selectedId = useMemo(() => incidents.data?.[0]?.id ?? null, [incidents.data]);
  const [focus, setFocus] = useState<number | null>(null);
  const activeId = focus ?? selectedId;
  const active = incidents.data?.find((i) => i.id === activeId) || null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Response"
        title="Incident Management"
        description="Security incidents persisted in PostgreSQL from detection and investigation workflows."
        actions={
          <button
            type="button"
            className="rounded-xl border px-3 py-2 text-sm font-semibold"
            style={{ borderColor: "var(--border)" }}
            onClick={() => setTick((t) => t + 1)}
          >
            Refresh
          </button>
        }
      />

      {incidents.loading && <LoadingBlock label="Loading incidents…" />}
      {incidents.error && <ErrorBlock message={incidents.error} />}

      {incidents.data && incidents.data.length === 0 && (
        <EmptyState
          title="No incidents yet"
          detail="Incidents appear after ML detections are investigated or attack-labelled traffic is escalated."
        />
      )}

      {incidents.data && incidents.data.length > 0 && (
        <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
          <GlassPanel className="p-0 overflow-hidden">
            <DataTable
              columns={["ID", "Title", "Severity", "Status", "Category", "Created"]}
              rows={incidents.data.map((i) => [
                <button
                  key={i.id}
                  type="button"
                  className="font-mono text-xs underline-offset-2 hover:underline"
                  style={{ color: "var(--accent-secondary)" }}
                  onClick={() => setFocus(i.id)}
                >
                  #{i.id}
                </button>,
                i.title,
                <Badge key={`s${i.id}`} tone={tone(i.severity)}>
                  {i.severity}
                </Badge>,
                i.status,
                i.attack_category || "—",
                new Date(i.created_at).toLocaleString(),
              ])}
            />
          </GlassPanel>

          <GlassPanel>
            <h3 className="text-sm font-bold m-0 mb-3">Incident Detail</h3>
            {!active ? (
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Select an incident.
              </p>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="text-lg font-bold">{active.title}</div>
                <div className="flex gap-2">
                  <Badge tone={tone(active.severity)}>{active.severity}</Badge>
                  <Badge tone="neutral">{active.status}</Badge>
                </div>
                <p className="leading-relaxed" style={{ color: "var(--muted)" }}>
                  {active.description || "No description."}
                </p>
                <div>
                  <span style={{ color: "var(--muted)" }}>Source → Dest · </span>
                  <span className="font-mono text-xs">
                    {active.source_ip || "—"} → {active.dest_ip || "—"}
                  </span>
                </div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Category · </span>
                  {active.attack_category || "—"}
                </div>
                <div className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                  {new Date(active.created_at).toLocaleString()}
                </div>
              </div>
            )}
          </GlassPanel>
        </div>
      )}
    </div>
  );
}
