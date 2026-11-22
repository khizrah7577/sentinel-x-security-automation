import type { ReactNode } from "react";
import { Badge, GlassPanel, PageHeader } from "../../components/nexus/primitives";

export function AutomationShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Automation Center" title={title} description={description} actions={actions} />
      {children}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  const tone =
    s.includes("fail") || s.includes("error")
      ? "danger"
      : s.includes("complete") || s === "ok" || s === "success"
        ? "ok"
        : s.includes("skip") || s.includes("condition")
          ? "warn"
          : "neutral";
  return <Badge tone={tone as "danger" | "ok" | "warn" | "neutral"}>{status || "—"}</Badge>;
}

export function CatalogNote() {
  return (
    <GlassPanel>
      <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
        Automation uses allowlisted actions only. Disruptive firewall changes always require administrator approval and
        lab private IPs. Uncertain ML predictions never auto-block.
      </p>
    </GlassPanel>
  );
}
