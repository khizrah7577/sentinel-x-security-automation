import { useState } from "react";
import { useApi } from "../../hooks/useApi";
import { api, ApiError } from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
import {
  Button,
  DataTable,
  EmptyState,
  ErrorBlock,
  GlassPanel,
  LoadingBlock,
} from "../../components/nexus/primitives";
import { AutomationShell, CatalogNote } from "./AutomationShared";

type Policy = {
  id: number;
  name: string;
  enabled: boolean;
  action_type: string;
  require_approval: boolean;
  allow_auto: boolean;
  min_confidence: number;
  min_severity: string;
  lab_only: boolean;
  notes: string;
};

const LOW_RISK = ["create_alert", "request_further_investigation", "mark_resolved"];

export default function ResponseAutomationPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const list = useApi<Policy[]>(`/automation/response-policies?_=${tick}`, [tick]);
  const [name, setName] = useState("Low-risk alert policy");
  const [actionType, setActionType] = useState("create_alert");
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    setError(null);
    try {
      await api("/automation/response-policies", {
        method: "POST",
        body: JSON.stringify({
          name,
          enabled: true,
          action_type: actionType,
          require_approval: !LOW_RISK.includes(actionType),
          allow_auto: LOW_RISK.includes(actionType),
          min_confidence: 0.9,
          min_severity: "high",
          lab_only: true,
          notes: "Created from Response Automation UI",
        }),
      });
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Create failed");
    }
  };

  const remove = async (id: number) => {
    await api(`/automation/response-policies/${id}`, { method: "DELETE" });
    setTick((t) => t + 1);
  };

  return (
    <AutomationShell
      title="Response Automation"
      description="Configurable response policies. Disruptive lab firewall actions always require admin approval; public IP blocking is rejected."
    >
      <CatalogNote />
      {error && <ErrorBlock message={error} />}
      {user?.role === "admin" && (
        <GlassPanel className="space-y-3">
          <h3 className="text-sm font-bold m-0">New policy</h3>
          <div className="flex flex-wrap gap-2">
            <input
              className="rounded-lg border px-3 py-2 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <select
              className="rounded-lg border px-3 py-2 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
            >
              {[...LOW_RISK, "recommend_block_ip", "apply_temp_firewall_rule"].map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <Button onClick={() => void create()}>Add policy</Button>
          </div>
        </GlassPanel>
      )}
      {list.loading && <LoadingBlock />}
      {list.error && <ErrorBlock message={list.error} />}
      {list.data && list.data.length === 0 && (
        <EmptyState title="No policies" detail="Create an allowlisted response policy to document automation intent." />
      )}
      {list.data && list.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Action", "Approval", "Auto", "Min conf", "Min sev", "Lab", "Controls"]}
          rows={list.data.map((p) => [
            p.id,
            p.name,
            p.action_type,
            p.require_approval ? "Required" : "Optional",
            p.allow_auto ? "Yes" : "No",
            p.min_confidence,
            p.min_severity,
            p.lab_only ? "Yes" : "No",
            user?.role === "admin" ? (
              <Button variant="danger" onClick={() => void remove(p.id)}>
                Delete
              </Button>
            ) : (
              "—"
            ),
          ])}
        />
      )}
    </AutomationShell>
  );
}
