import { motion, useReducedMotion } from "framer-motion";
import type { CSSProperties, ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
      <div>
        {eyebrow && (
          <div
            className="text-[11px] font-semibold tracking-[0.16em] uppercase mb-1"
            style={{ color: "var(--accent)" }}
          >
            {eyebrow}
          </div>
        )}
        <h1 className="text-2xl md:text-[1.75rem] font-bold m-0 tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm mt-1.5 mb-0 max-w-2xl leading-relaxed" style={{ color: "var(--muted)" }}>
            {description}
          </p>
        )}
      </div>
      {actions}
    </div>
  );
}

export function GlassPanel({
  children,
  className = "",
  glow,
  style,
}: {
  children: ReactNode;
  className?: string;
  glow?: "critical" | "accent";
  style?: CSSProperties;
}) {
  return (
    <div
      className={`rounded-[var(--radius)] border p-5 nexus-glass ${glow === "critical" ? "nexus-critical-glow" : ""} ${className}`}
      style={{
        borderColor: "var(--border)",
        boxShadow: glow === "accent" ? "var(--glow-accent)" : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/** Alias for existing pages */
export const Card = GlassPanel;

export function MetricCard({
  label,
  value,
  icon,
  accent = "var(--accent)",
  sparkline,
  hint,
}: {
  label: string;
  value: string | number;
  icon: ReactNode;
  accent?: string;
  sparkline?: number[];
  hint?: string;
}) {
  const reduce = useReducedMotion();
  const max = sparkline && sparkline.length ? Math.max(...sparkline, 1) : 1;
  return (
    <motion.div
      whileHover={reduce ? undefined : { y: -3 }}
      transition={{ type: "spring", stiffness: 380, damping: 28 }}
      className="rounded-[var(--radius)] border p-4 relative overflow-hidden"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
      }}
    >
      <div
        className="absolute inset-y-0 left-0 w-1"
        style={{ background: accent }}
      />
      <div className="flex items-start justify-between gap-3 pl-2">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--muted)" }}>
            {label}
          </div>
          <div className="text-2xl font-bold mt-1.5 tabular-nums tracking-tight">{value}</div>
          {hint && (
            <div className="text-[11px] mt-1" style={{ color: "var(--muted)" }}>
              {hint}
            </div>
          )}
        </div>
        <div
          className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
          style={{ background: "color-mix(in srgb, " + accent + " 16%, transparent)", color: accent }}
        >
          {icon}
        </div>
      </div>
      {sparkline && sparkline.length > 1 && (
        <svg viewBox={`0 0 ${sparkline.length * 8} 28`} className="w-full h-7 mt-3 pl-2" preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={accent}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={sparkline.map((v, i) => `${i * 8},${28 - (v / max) * 24}`).join(" ")}
          />
        </svg>
      )}
    </motion.div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "info" | "ai";
}) {
  const colors: Record<string, string> = {
    neutral: "var(--muted)",
    ok: "var(--ok)",
    warn: "var(--warning)",
    danger: "var(--critical)",
    info: "var(--info)",
    ai: "var(--accent-ai)",
  };
  const c = colors[tone];
  return (
    <span
      className="inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border"
      style={{
        color: c,
        borderColor: "color-mix(in srgb, " + c + " 45%, var(--border))",
        background: "color-mix(in srgb, " + c + " 12%, transparent)",
      }}
    >
      {children}
    </span>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <GlassPanel>
      <h3 className="text-sm font-semibold m-0">{title}</h3>
      <p className="text-sm mt-2 mb-0" style={{ color: "var(--muted)" }}>
        {detail}
      </p>
    </GlassPanel>
  );
}

export function Skeleton({ className = "h-24" }: { className?: string }) {
  return (
    <div
      className={`rounded-[var(--radius)] animate-pulse ${className}`}
      style={{ background: "color-mix(in srgb, var(--border) 55%, var(--surface))" }}
    />
  );
}

export function ErrorBlock({ message }: { message: string }) {
  return (
    <p className="text-sm m-0" style={{ color: "var(--critical)" }}>
      {message}
    </p>
  );
}

export function LoadingBlock({ label = "Loading…" }: { label?: string }) {
  return (
    <p className="text-sm" style={{ color: "var(--muted)" }}>
      {label}
    </p>
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger" | "ghost" | "ai";
  type?: "button" | "submit";
  className?: string;
}) {
  const styles: Record<string, CSSProperties> = {
    primary: { background: "var(--accent)", color: "#041016" },
    secondary: {
      background: "transparent",
      color: "var(--text)",
      border: "1px solid var(--border)",
    },
    danger: { background: "var(--critical)", color: "#fff" },
    ghost: { background: "transparent", color: "var(--muted)" },
    ai: { background: "var(--accent-ai)", color: "#fff" },
  };
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-semibold disabled:opacity-50 transition-opacity ${className}`}
      style={styles[variant]}
    >
      {children}
    </button>
  );
}

export function ConfirmModal({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  danger,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" style={{ background: "rgba(0,0,0,0.55)" }}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md rounded-[var(--radius)] border p-6"
        style={{ background: "var(--elevated)", borderColor: "var(--border)" }}
      >
        <h3 className="text-lg font-bold m-0">{title}</h3>
        <p className="text-sm mt-2 mb-5" style={{ color: "var(--muted)" }}>
          {body}
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </motion.div>
    </div>
  );
}

export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: ReactNode[][];
}) {
  if (rows.length === 0) return null;
  return (
    <div className="overflow-x-auto rounded-[var(--radius)] border" style={{ borderColor: "var(--border)" }}>
      <table className="w-full text-sm">
        <thead style={{ background: "var(--bg-secondary)" }}>
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                className="text-left font-semibold px-4 py-3 border-b text-xs uppercase tracking-wide"
                style={{ borderColor: "var(--border)", color: "var(--muted)" }}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              style={{ background: i % 2 ? "color-mix(in srgb, var(--surface) 70%, var(--bg))" : "var(--surface)" }}
            >
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 border-b align-top" style={{ borderColor: "var(--border)" }}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusDot({ tone }: { tone: "ok" | "warn" | "danger" | "muted" | "ai" }) {
  const map = {
    ok: "var(--ok)",
    warn: "var(--warning)",
    danger: "var(--critical)",
    muted: "var(--muted)",
    ai: "var(--accent-ai)",
  };
  return (
    <span
      className="inline-block w-2 h-2 rounded-full"
      style={{ background: map[tone], boxShadow: `0 0 8px ${map[tone]}` }}
    />
  );
}

export function CircularGauge({
  value,
  max = 100,
  label,
  color = "var(--accent)",
  sublabel,
}: {
  value: number;
  max?: number;
  label: string;
  color?: string;
  sublabel?: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <div className="flex flex-col items-center">
      <svg width="112" height="112" viewBox="0 0 112 112">
        <circle cx="56" cy="56" r={r} fill="none" stroke="var(--border)" strokeWidth="10" />
        <circle
          cx="56"
          cy="56"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform="rotate(-90 56 56)"
        />
        <text x="56" y="52" textAnchor="middle" className="fill-current text-lg font-bold" style={{ fill: "var(--text)" }}>
          {Number.isFinite(value) ? (max === 100 ? `${Math.round(pct)}%` : value) : "—"}
        </text>
        <text x="56" y="70" textAnchor="middle" style={{ fill: "var(--muted)", fontSize: 10 }}>
          {label}
        </text>
      </svg>
      {sublabel && (
        <div className="text-[11px] mt-1 text-center" style={{ color: "var(--muted)" }}>
          {sublabel}
        </div>
      )}
    </div>
  );
}

export function RangeFilter({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const opts = [
    { id: "15m", label: "15m" },
    { id: "1h", label: "1h" },
    { id: "24h", label: "24h" },
    { id: "7d", label: "7d" },
  ];
  return (
    <div className="inline-flex rounded-lg border p-0.5" style={{ borderColor: "var(--border)" }}>
      {opts.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => onChange(o.id)}
          className="px-2.5 py-1.5 text-xs font-semibold rounded-md"
          style={{
            background: value === o.id ? "var(--accent-soft)" : "transparent",
            color: value === o.id ? "var(--accent)" : "var(--muted)",
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
