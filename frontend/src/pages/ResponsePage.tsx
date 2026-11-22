import { useState } from "react";
import {
  Badge,
  ConfirmModal,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
  PageHeader,
} from "../components/nexus/primitives";
import { useApi } from "../hooks/useApi";
import { api, ApiError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

type Summary = {
  pending: number;
  approved: number;
  rejected: number;
  executed: number;
  active_firewall_rules: number;
  mode?: string;
};

type Mode = {
  mode: string;
  modes: string[];
  description: Record<string, string>;
  low_risk_actions: string[];
  disruptive_actions: string[];
};

type Recommendation = {
  id: number;
  incident_id: number;
  action_type: string;
  rationale: string;
  approval_status: string;
  rejection_reason?: string;
  created_at: string;
};

type Executed = {
  id: number;
  recommendation_id: number | null;
  action_type: string;
  success: boolean;
  verification_result: string;
  rollback_available: boolean;
  rolled_back: boolean;
  error_message?: string;
  created_at: string;
};

type Firewall = {
  id: number;
  target_ip: string;
  direction: string;
  action: string;
  is_temporary: boolean;
  is_active: boolean;
  lab_only: boolean;
  notes: string;
  created_at: string;
};

type Audit = {
  id: number;
  action: string;
  resource_type: string;
  detail: string;
  success: boolean;
  created_at: string;
};

export default function ResponsePage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const summary = useApi<Summary>(`/response/summary?_=${tick}`, [tick]);
  const mode = useApi<Mode>(`/response/mode?_=${tick}`, [tick]);
  const pending = useApi<Recommendation[]>(`/response/recommendations?status=pending&_=${tick}`, [tick]);
  const allRecs = useApi<Recommendation[]>(`/response/recommendations?limit=30&_=${tick}`, [tick]);
  const executed = useApi<Executed[]>(`/response/executed?_=${tick}`, [tick]);
  const rules = useApi<Firewall[]>(`/response/firewall-rules?_=${tick}`, [tick]);
  const audit = useApi<Audit[]>(`/response/audit?limit=50&_=${tick}`, [tick]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<null | { kind: "approve" | "execute" | "rollback"; id: number }>(null);

  const refresh = () => setTick((t) => t + 1);
  const isAdmin = user?.role === "admin";

  const setMode = async (next: string) => {
    setBusy(`mode-${next}`);
    setError(null);
    try {
      await api("/response/mode", { method: "PUT", body: JSON.stringify({ mode: next }) });
      setMessage(`Response mode set to ${next}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to set mode");
    } finally {
      setBusy(null);
    }
  };

  const approve = async (id: number) => {
    setBusy(`approve-${id}`);
    setError(null);
    try {
      const out = await api<{ executed?: { id: number; verification_result: string } | null }>(
        `/response/recommendations/${id}/approve`,
        { method: "POST", body: JSON.stringify({ execute_now: true }) },
      );
      setMessage(
        out.executed
          ? `Approved #${id} and executed: ${out.executed.verification_result}`
          : `Approved #${id} (manual mode — execute separately)`,
      );
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Approve failed");
    } finally {
      setBusy(null);
    }
  };

  const reject = async (id: number) => {
    const reason = window.prompt("Rejection reason (optional)") || "";
    setBusy(`reject-${id}`);
    setError(null);
    try {
      await api(`/response/recommendations/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
      setMessage(`Rejected recommendation #${id}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Reject failed");
    } finally {
      setBusy(null);
    }
  };

  const execute = async (id: number) => {
    setBusy(`exec-${id}`);
    setError(null);
    try {
      const out = await api<Executed>(`/response/recommendations/${id}/execute`, { method: "POST" });
      setMessage(`Executed #${id}: ${out.verification_result}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Execute failed");
    } finally {
      setBusy(null);
    }
  };

  const rollback = async (id: number) => {
    setBusy(`rollback-${id}`);
    setError(null);
    try {
      const out = await api<Executed>(`/response/executed/${id}/rollback`, { method: "POST" });
      setMessage(`Rolled back #${id}: ${out.verification_result}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Rollback failed");
    } finally {
      setBusy(null);
    }
  };

  const runConfirm = async () => {
    if (!confirm) return;
    const { kind, id } = confirm;
    setConfirm(null);
    if (kind === "approve") await approve(id);
    else if (kind === "execute") await execute(id);
    else await rollback(id);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Response"
        title="Response Center"
        description="Allowlisted lab actions only. No arbitrary shell commands. Public IP blocking is rejected."
      />

      <ConfirmModal
        open={!!confirm}
        title={
          confirm?.kind === "approve"
            ? "Approve and execute?"
            : confirm?.kind === "execute"
              ? "Execute allowlisted action?"
              : "Rollback executed action?"
        }
        body="This affects the simulated lab firewall / response state only. Actions remain allowlisted and IP-validated."
        confirmLabel={confirm?.kind === "rollback" ? "Rollback" : "Confirm"}
        danger={confirm?.kind === "rollback"}
        onCancel={() => setConfirm(null)}
        onConfirm={() => void runConfirm()}
      />

      {mode.data && (
        <GlassPanel className="space-y-3">
          <div className="text-sm">
            Current mode: <strong>{mode.data.mode}</strong>
          </div>
          <p className="text-sm m-0" style={{ color: "var(--muted)" }}>
            {mode.data.description[mode.data.mode]}
          </p>
          {isAdmin && (
            <div className="flex flex-wrap gap-2">
              {mode.data.modes.map((m) => (
                <button
                  key={m}
                  type="button"
                  className="rounded-md border px-3 py-2 text-sm"
                  style={{
                    borderColor: mode.data?.mode === m ? "var(--accent)" : "var(--border)",
                    background: mode.data?.mode === m ? "var(--accent-soft)" : "transparent",
                  }}
                  disabled={busy !== null}
                  onClick={() => void setMode(m)}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
          <p className="text-xs m-0" style={{ color: "var(--muted)" }}>
            Low-risk auto: {(mode.data.low_risk_actions || []).join(", ")} · Disruptive (approval):{" "}
            {(mode.data.disruptive_actions || []).join(", ")}
          </p>
        </GlassPanel>
      )}

      {message && <p className="text-sm m-0" style={{ color: "var(--accent)" }}>{message}</p>}
      {error && <ErrorBlock message={error} />}

      {summary.loading && <LoadingBlock />}
      {summary.error && <ErrorBlock message={summary.error} />}
      {summary.data && (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {[
            ["Pending", summary.data.pending],
            ["Approved", summary.data.approved],
            ["Rejected", summary.data.rejected],
            ["Executed", summary.data.executed],
            ["Active rules", summary.data.active_firewall_rules],
          ].map(([label, value]) => (
            <GlassPanel key={String(label)} className="py-4">
              <div className="text-xs" style={{ color: "var(--muted)" }}>{label}</div>
              <div className="text-xl font-semibold mt-1">{value}</div>
            </GlassPanel>
          ))}
        </div>
      )}

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">Pending approvals</h2>
        {pending.data && pending.data.length === 0 && (
          <EmptyState title="No pending approvals" detail="Run an AI investigation to create recommendations." />
        )}
        {pending.data && pending.data.length > 0 && (
          <DataTable
            columns={["ID", "Incident", "Action", "Rationale", "Controls"]}
            rows={pending.data.map((r) => [
              r.id,
              r.incident_id,
              r.action_type,
              r.rationale || "—",
              isAdmin ? (
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded-md px-2 py-1 text-xs text-white"
                    style={{ background: "var(--accent)" }}
                    disabled={busy !== null}
                    onClick={() => setConfirm({ kind: "approve", id: r.id })}
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    className="rounded-md border px-2 py-1 text-xs"
                    style={{ borderColor: "var(--border)", color: "var(--danger)" }}
                    disabled={busy !== null}
                    onClick={() => void reject(r.id)}
                  >
                    Reject
                  </button>
                </div>
              ) : (
                <Badge tone="warn">Admin only</Badge>
              ),
            ])}
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">All recommendations</h2>
        {allRecs.data && allRecs.data.length > 0 && (
          <DataTable
            columns={["ID", "Incident", "Action", "Status", "Execute"]}
            rows={allRecs.data.map((r) => [
              r.id,
              r.incident_id,
              r.action_type,
              <Badge
                tone={
                  r.approval_status === "approved" || r.approval_status === "auto_executed"
                    ? "ok"
                    : r.approval_status === "rejected"
                      ? "danger"
                      : "warn"
                }
              >
                {r.approval_status}
              </Badge>,
              isAdmin && r.approval_status === "approved" ? (
                <button
                  type="button"
                  className="rounded-md border px-2 py-1 text-xs"
                  style={{ borderColor: "var(--border)" }}
                  disabled={busy !== null}
                  onClick={() => setConfirm({ kind: "execute", id: r.id })}
                >
                  Execute
                </button>
              ) : (
                "—"
              ),
            ])}
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">Executed responses</h2>
        {executed.data && executed.data.length === 0 && (
          <EmptyState title="No executed actions" detail="Approve a pending recommendation to execute an allowlisted action." />
        )}
        {executed.data && executed.data.length > 0 && (
          <DataTable
            columns={["ID", "Action", "Success", "Verification", "Rollback"]}
            rows={executed.data.map((e) => [
              e.id,
              e.action_type,
              e.success ? <Badge tone="ok">Yes</Badge> : <Badge tone="danger">No</Badge>,
              e.verification_result || e.error_message || "—",
              e.rolled_back ? (
                <Badge>Rolled back</Badge>
              ) : e.rollback_available && isAdmin ? (
                <button
                  type="button"
                  className="rounded-md border px-2 py-1 text-xs"
                  style={{ borderColor: "var(--border)" }}
                  disabled={busy !== null}
                  onClick={() => setConfirm({ kind: "rollback", id: e.id })}
                >
                  Rollback
                </button>
              ) : (
                "—"
              ),
            ])}
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">Temporary firewall rules (simulated lab)</h2>
        {rules.data && rules.data.length === 0 && (
          <EmptyState title="No firewall rules" detail="Approve/execute a block/apply rule action against a lab private IP." />
        )}
        {rules.data && rules.data.length > 0 && (
          <DataTable
            columns={["ID", "IP", "Direction", "Action", "Temporary", "Active", "Lab"]}
            rows={rules.data.map((r) => [
              r.id,
              r.target_ip,
              r.direction,
              r.action,
              r.is_temporary ? "Yes" : "No",
              r.is_active ? <Badge tone="ok">Active</Badge> : <Badge>Inactive</Badge>,
              r.lab_only ? "Yes" : "No",
            ])}
          />
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold m-0">Audit log</h2>
        {audit.data && audit.data.length === 0 && (
          <EmptyState title="No audit entries" detail="Approvals and executions are recorded here." />
        )}
        {audit.data && audit.data.length > 0 && (
          <DataTable
            columns={["ID", "Action", "Resource", "Detail", "OK", "Time"]}
            rows={audit.data.map((a) => [
              a.id,
              a.action,
              a.resource_type || "—",
              a.detail || "—",
              a.success ? <Badge tone="ok">Yes</Badge> : <Badge tone="danger">No</Badge>,
              new Date(a.created_at).toLocaleString(),
            ])}
          />
        )}
      </section>
    </div>
  );
}
