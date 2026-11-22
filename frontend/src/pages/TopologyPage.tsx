import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  MarkerType,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import { NetworkApi, type LabTopology } from "../services/api";
import {
  Badge,
  ErrorBlock,
  GlassPanel,
  PageHeader,
  Skeleton,
} from "../components/nexus/primitives";

function LabNode({ data, selected }: NodeProps) {
  const d = data as {
    label: string;
    role: string;
    ips: string[];
    observed: boolean;
    flow_count: number;
    suspicious_count: number;
  };
  const accent =
    d.role === "attacker"
      ? "var(--critical)"
      : d.role === "monitor"
        ? "var(--accent-ai)"
        : d.role === "server"
          ? "var(--accent-secondary)"
          : "var(--accent)";
  return (
    <div
      className="rounded-2xl border min-w-[160px] px-3 py-2.5 shadow-sm"
      style={{
        background: "var(--elevated)",
        borderColor: selected ? accent : "var(--border)",
        boxShadow: d.suspicious_count > 0 ? "var(--glow-critical)" : selected ? "var(--glow-accent)" : undefined,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: accent }} />
      <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: accent }}>
        {d.role}
      </div>
      <div className="text-sm font-bold mt-0.5">{d.label}</div>
      <div className="text-[11px] font-mono mt-1" style={{ color: "var(--muted)" }}>
        {d.ips.join(", ")}
      </div>
      <div className="flex gap-1 mt-2">
        <Badge tone={d.observed ? "ok" : "neutral"}>{d.observed ? "Observed" : "Reference"}</Badge>
        {d.suspicious_count > 0 && <Badge tone="danger">{d.suspicious_count} sus</Badge>}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: accent }} />
    </div>
  );
}

const nodeTypes = { lab: LabNode };

const LAYOUT: Record<string, { x: number; y: number }> = {
  kali: { x: 40, y: 80 },
  client: { x: 40, y: 280 },
  dns: { x: 320, y: 40 },
  server: { x: 560, y: 200 },
  monitor: { x: 320, y: 360 },
};

export default function TopologyPage() {
  const [data, setData] = useState<LabTopology | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await NetworkApi.labTopology());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load topology");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const nodes: Node[] = useMemo(() => {
    if (!data) return [];
    return data.nodes.map((n) => ({
      id: n.id,
      type: "lab",
      position: LAYOUT[n.id] || { x: 100, y: 100 },
      data: n,
    }));
  }, [data]);

  const edges: Edge[] = useMemo(() => {
    if (!data) return [];
    return data.edges.map((e, i) => ({
      id: `e-${e.source}-${e.target}-${i}`,
      source: e.source,
      target: e.target,
      animated: e.suspicious_count > 0,
      label: `${e.count}${e.top_protocol ? ` · ${e.top_protocol}` : ""}`,
      style: {
        stroke: e.suspicious_count > 0 ? "var(--critical)" : "var(--accent-secondary)",
        strokeWidth: Math.min(1.5 + e.count / 8, 5),
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: e.suspicious_count > 0 ? "#FF4D6D" : "#35C6F4" },
      labelStyle: { fill: "var(--muted)", fontSize: 10 },
    }));
  }, [data]);

  const selectedNode = data?.nodes.find((n) => n.id === selected) || null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Network Security"
        title="Network Topology"
        description="Simulated lab reference map with observed traffic overlays from PostgreSQL. Not a live GNS3 discovery feed."
        actions={
          <button
            type="button"
            className="rounded-xl border px-3 py-2 text-sm font-semibold"
            style={{ borderColor: "var(--border)" }}
            onClick={() => void load()}
          >
            Refresh
          </button>
        }
      />

      {error && <ErrorBlock message={error} />}
      {loading && <Skeleton className="h-[520px]" />}

      {data && !loading && (
        <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
          <GlassPanel className="p-0 overflow-hidden" style={{ height: 560 }}>
            <div className="px-4 py-2 border-b text-xs flex flex-wrap gap-2 items-center" style={{ borderColor: "var(--border)" }}>
              <Badge tone="info">{data.mode}</Badge>
              <span style={{ color: "var(--muted)" }}>
                Observed edges: {data.observed_edge_count} · Flows: {data.total_traffic_records} · Events:{" "}
                {data.total_network_events}
              </span>
            </div>
            <div style={{ height: 500 }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                fitView
                onNodeClick={(_, n) => setSelected(n.id)}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={18} color="var(--border)" />
                <Controls />
                <MiniMap
                  nodeColor={() => "var(--accent)"}
                  maskColor="color-mix(in srgb, var(--bg) 70%, transparent)"
                />
              </ReactFlow>
            </div>
          </GlassPanel>

          <GlassPanel>
            <h3 className="text-sm font-bold m-0">Node Intelligence</h3>
            <p className="text-xs mt-1 mb-4" style={{ color: "var(--muted)" }}>
              {data.disclaimer}
            </p>
            {selectedNode ? (
              <div className="space-y-3 text-sm">
                <div className="font-bold text-lg">{selectedNode.label}</div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Role · </span>
                  {selectedNode.role}
                </div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Reference IPs · </span>
                  <span className="font-mono text-xs">{selectedNode.ips.join(", ")}</span>
                </div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Observed flows · </span>
                  {selectedNode.flow_count}
                </div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Suspicious · </span>
                  {selectedNode.suspicious_count}
                </div>
                <div>
                  <span style={{ color: "var(--muted)" }}>Last seen · </span>
                  {selectedNode.last_seen ? new Date(selectedNode.last_seen).toLocaleString() : "—"}
                </div>
                <p className="text-xs leading-relaxed m-0" style={{ color: "var(--muted)" }}>
                  {selectedNode.description}
                </p>
              </div>
            ) : (
              <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
                Select a node to inspect observed activity. Unobserved nodes remain reference-only.
              </p>
            )}
          </GlassPanel>
        </div>
      )}
    </div>
  );
}
