import { Fragment, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState, GlassPanel, Skeleton } from "../nexus/primitives";

const TOOLTIP_STYLE = {
  background: "var(--elevated)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--text)",
  fontSize: 12,
};

const PALETTE = [
  "var(--accent)",
  "var(--accent-secondary)",
  "var(--accent-ai)",
  "var(--warning)",
  "var(--critical)",
  "var(--muted)",
];

export function ChartCard({
  title,
  subtitle,
  loading,
  empty,
  emptyDetail = "No data in the selected range. Charts only show real database values.",
  children,
  actions,
}: {
  title: string;
  subtitle?: string;
  loading?: boolean;
  empty?: boolean;
  emptyDetail?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <GlassPanel className="h-full flex flex-col">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="text-sm font-bold m-0">{title}</h3>
          {subtitle && (
            <p className="text-xs mt-1 mb-0" style={{ color: "var(--muted)" }}>
              {subtitle}
            </p>
          )}
        </div>
        {actions}
      </div>
      {loading ? <Skeleton className="h-56" /> : empty ? <EmptyState title="No data yet" detail={emptyDetail} /> : children}
    </GlassPanel>
  );
}

export function TrafficAreaChart({
  data,
}: {
  data: { t: string; events: number; normal: number; malicious: number }[];
}) {
  const rows = data.map((d) => ({
    ...d,
    label: new Date(d.t).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
  }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows}>
          <defs>
            <linearGradient id="gEvents" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-secondary)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--accent-secondary)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gMal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--critical)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--critical)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 10 }} minTickGap={28} />
          <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend />
          <Area type="monotone" dataKey="events" name="Events" stroke="var(--accent-secondary)" fill="url(#gEvents)" />
          <Area type="monotone" dataKey="malicious" name="Malicious" stroke="var(--critical)" fill="url(#gMal)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CompareBarChart({
  data,
}: {
  data: { name: string; normal: number; malicious: number }[];
}) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend />
          <Bar dataKey="normal" name="Normal" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="malicious" name="Malicious" fill="var(--critical)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DonutChart({ data, nameKey = "name" }: { data: { name: string; value: number }[]; nameKey?: string }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey={nameKey} innerRadius={58} outerRadius={88} paddingAngle={2}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HBarChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis type="number" allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={88} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey="value" fill="var(--warning)" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ModelPerfChart({
  data,
}: {
  data: { name: string; accuracy: number; precision: number; recall: number; f1: number }[];
}) {
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 10 }} />
          <YAxis domain={[0, 1]} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Legend />
          <Bar dataKey="accuracy" fill="var(--accent)" />
          <Bar dataKey="precision" fill="var(--accent-secondary)" />
          <Bar dataKey="recall" fill="var(--accent-ai)" />
          <Bar dataKey="f1" name="F1" fill="var(--warning)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SimpleLineChart({ data, dataKey = "count" }: { data: { t: string; count: number }[]; dataKey?: string }) {
  const rows = data.map((d) => ({
    ...d,
    label: new Date(d.t).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" }),
  }));
  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
          <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 10 }} minTickGap={24} />
          <YAxis allowDecimals={false} tick={{ fill: "var(--muted)", fontSize: 11 }} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Line type="monotone" dataKey={dataKey} stroke="var(--accent-ai)" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ActivityHeatmap({
  cells,
}: {
  cells: { day: number; hour: number; count: number }[];
}) {
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const max = Math.max(...cells.map((c) => c.count), 1);
  const map = new Map(cells.map((c) => [`${c.day}-${c.hour}`, c.count]));
  return (
    <div className="overflow-x-auto">
      <div className="inline-grid gap-1" style={{ gridTemplateColumns: `48px repeat(24, 14px)` }}>
        <div />
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="text-[9px] text-center" style={{ color: "var(--muted)" }}>
            {h % 3 === 0 ? h : ""}
          </div>
        ))}
        {days.map((d, di) => (
          <Fragment key={`day-${di}`}>
            <div className="text-[10px] flex items-center" style={{ color: "var(--muted)" }}>
              {d}
            </div>
            {Array.from({ length: 24 }, (_, h) => {
              const v = map.get(`${di}-${h}`) || 0;
              const a = v / max;
              return (
                <div
                  key={`${di}-${h}`}
                  title={`${d} ${h}:00 — ${v}`}
                  className="rounded-sm"
                  style={{
                    width: 14,
                    height: 14,
                    background:
                      v === 0
                        ? "var(--border)"
                        : `color-mix(in srgb, var(--accent) ${Math.round(20 + a * 80)}%, var(--surface))`,
                  }}
                />
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}

export function ConfusionMatrix({ matrix }: { matrix: number[][] }) {
  if (!matrix?.length) return null;
  const flat = matrix.flat();
  const max = Math.max(...flat, 1);
  const labels = ["Normal", "Attack"];
  return (
    <div className="inline-grid gap-2" style={{ gridTemplateColumns: `64px repeat(${matrix[0].length}, 72px)` }}>
      <div />
      {labels.slice(0, matrix[0].length).map((l) => (
        <div key={l} className="text-[11px] text-center font-semibold" style={{ color: "var(--muted)" }}>
          Pred {l}
        </div>
      ))}
      {matrix.map((row, i) => (
        <Fragment key={`row-${i}`}>
          <div className="text-[11px] flex items-center font-semibold" style={{ color: "var(--muted)" }}>
            True {labels[i] || i}
          </div>
          {row.map((v, j) => (
            <div
              key={`${i}-${j}`}
              className="h-14 rounded-lg grid place-items-center text-sm font-bold border"
              style={{
                borderColor: "var(--border)",
                background: `color-mix(in srgb, var(--accent-secondary) ${Math.round((v / max) * 70)}%, var(--surface))`,
              }}
            >
              {v}
            </div>
          ))}
        </Fragment>
      ))}
    </div>
  );
}
