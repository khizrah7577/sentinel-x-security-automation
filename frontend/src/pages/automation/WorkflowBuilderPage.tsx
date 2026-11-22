import { useMemo, useState } from "react";
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
import { AutomationShell, CatalogNote, StatusBadge } from "./AutomationShared";

type Overview = {
  catalog: { triggers: string[]; condition_fields: string[]; actions: string[] };
};

type Workflow = {
  id: number;
  name: string;
  description: string;
  enabled: boolean;
  trigger: string;
  conditions_json: string;
  actions_json: string;
  last_status: string;
  run_count: number;
};

export default function WorkflowBuilderPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const catalog = useApi<Overview>("/automation/overview", []);
  const list = useApi<Workflow[]>(`/automation/workflows?_=${tick}`, [tick]);
  const [name, setName] = useState("New workflow");
  const [description, setDescription] = useState("");
  const [trigger, setTrigger] = useState("ml_attack_prediction");
  const [condField, setCondField] = useState("severity");
  const [condOp, setCondOp] = useState("gte");
  const [condValue, setCondValue] = useState("high");
  const [actionType, setActionType] = useState("send_notification");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);

  const triggers = catalog.data?.catalog.triggers || ["ml_attack_prediction"];
  const fields = catalog.data?.catalog.condition_fields || ["severity"];
  const actions = catalog.data?.catalog.actions || ["send_notification"];

  const refresh = () => setTick((t) => t + 1);

  const loadIntoForm = (w: Workflow) => {
    setEditId(w.id);
    setName(w.name);
    setDescription(w.description);
    setTrigger(w.trigger);
    try {
      const conds = JSON.parse(w.conditions_json || "[]");
      if (conds[0]) {
        setCondField(conds[0].field || "severity");
        setCondOp(conds[0].op || "eq");
        setCondValue(String(conds[0].value ?? ""));
      }
      const acts = JSON.parse(w.actions_json || "[]");
      if (acts[0]) setActionType(acts[0].type || "send_notification");
    } catch {
      /* ignore */
    }
  };

  const save = async () => {
    if (user?.role !== "admin") return;
    setBusy(true);
    setError(null);
    setMessage(null);
    const body = {
      name,
      description,
      enabled: true,
      trigger,
      conditions: [{ field: condField, op: condOp, value: condValue }],
      actions: [
        actionType === "send_notification"
          ? {
              type: "send_notification",
              title: "Workflow notification",
              body: description || name,
              severity: "warning",
              link: "/intelligence",
            }
          : { type: actionType },
      ],
    };
    try {
      if (editId) {
        await api(`/automation/workflows/${editId}`, { method: "PUT", body: JSON.stringify(body) });
        setMessage(`Updated workflow #${editId}`);
      } else {
        const row = await api<Workflow>("/automation/workflows", {
          method: "POST",
          body: JSON.stringify(body),
        });
        setMessage(`Created workflow #${row.id}`);
      }
      setEditId(null);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (id: number) => {
    await api(`/automation/workflows/${id}/toggle`, { method: "POST" });
    refresh();
  };

  const test = async (id: number) => {
    setBusy(true);
    try {
      const out = await api<{ results: { status: string }[] }>(`/automation/workflows/${id}/test`, {
        method: "POST",
      });
      setMessage(`Test result: ${out.results?.[0]?.status || "done"}`);
      refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Test failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this workflow?")) return;
    await api(`/automation/workflows/${id}`, { method: "DELETE" });
    refresh();
  };

  const preview = useMemo(
    () => ({
      TRIGGER: trigger,
      CONDITION: { field: condField, op: condOp, value: condValue },
      ACTION: actionType,
    }),
    [trigger, condField, condOp, condValue, actionType],
  );

  return (
    <AutomationShell
      title="Workflow Builder"
      description="Configure TRIGGER → CONDITION → ACTION rules. Stored in PostgreSQL and executed by the automation engine."
      actions={
        user?.role === "admin" ? (
          <Button disabled={busy} onClick={() => void save()}>
            {editId ? `Update #${editId}` : "Create workflow"}
          </Button>
        ) : undefined
      }
    >
      <CatalogNote />
      {message && (
        <p className="text-sm m-0" style={{ color: "var(--accent)" }}>
          {message}
        </p>
      )}
      {error && <ErrorBlock message={error} />}

      {user?.role === "admin" && (
        <div className="grid gap-4 xl:grid-cols-2">
          <GlassPanel className="space-y-3">
            <h3 className="text-sm font-bold m-0">Rule editor</h3>
            <label className="block text-xs space-y-1">
              <span style={{ color: "var(--muted)" }}>Name</span>
              <input
                className="w-full rounded-lg border px-3 py-2 bg-transparent text-sm"
                style={{ borderColor: "var(--border)" }}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label className="block text-xs space-y-1">
              <span style={{ color: "var(--muted)" }}>Description</span>
              <textarea
                className="w-full rounded-lg border px-3 py-2 bg-transparent text-sm"
                style={{ borderColor: "var(--border)" }}
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <div className="grid sm:grid-cols-3 gap-2">
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--accent)" }}>TRIGGER</span>
                <select
                  className="w-full rounded-lg border px-2 py-2 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={trigger}
                  onChange={(e) => setTrigger(e.target.value)}
                >
                  {triggers.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--accent-secondary)" }}>CONDITION</span>
                <select
                  className="w-full rounded-lg border px-2 py-2 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={condField}
                  onChange={(e) => setCondField(e.target.value)}
                >
                  {fields.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-xs space-y-1">
                <span style={{ color: "var(--accent-ai)" }}>ACTION</span>
                <select
                  className="w-full rounded-lg border px-2 py-2 bg-transparent text-sm"
                  style={{ borderColor: "var(--border)" }}
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                >
                  {actions.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <select
                className="rounded-lg border px-2 py-2 bg-transparent text-sm"
                style={{ borderColor: "var(--border)" }}
                value={condOp}
                onChange={(e) => setCondOp(e.target.value)}
              >
                <option value="eq">equals</option>
                <option value="gte">gte</option>
                <option value="lte">lte</option>
              </select>
              <input
                className="rounded-lg border px-2 py-2 bg-transparent text-sm"
                style={{ borderColor: "var(--border)" }}
                value={condValue}
                onChange={(e) => setCondValue(e.target.value)}
                placeholder="value"
              />
            </div>
            {editId && (
              <Button variant="ghost" onClick={() => setEditId(null)}>
                Cancel edit
              </Button>
            )}
          </GlassPanel>
          <GlassPanel>
            <h3 className="text-sm font-bold m-0 mb-2">Preview</h3>
            <pre
              className="text-xs font-mono overflow-auto m-0 p-3 rounded-xl border"
              style={{ borderColor: "var(--border)", background: "var(--bg)" }}
            >
              {JSON.stringify(preview, null, 2)}
            </pre>
          </GlassPanel>
        </div>
      )}

      <h2 className="text-base font-semibold m-0">Saved workflows</h2>
      {list.loading && <LoadingBlock />}
      {list.error && <ErrorBlock message={list.error} />}
      {list.data && list.data.length === 0 && (
        <EmptyState title="No workflows yet" detail="Admins can create TRIGGER → CONDITION → ACTION rules above." />
      )}
      {list.data && list.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Trigger", "Enabled", "Runs", "Last", "Controls"]}
          rows={list.data.map((w) => [
            w.id,
            w.name,
            w.trigger,
            w.enabled ? "Yes" : "No",
            w.run_count,
            <StatusBadge key={w.id} status={w.last_status || "—"} />,
            user?.role === "admin" ? (
              <div className="flex flex-wrap gap-1">
                <Button variant="secondary" onClick={() => loadIntoForm(w)}>
                  Edit
                </Button>
                <Button variant="secondary" onClick={() => void toggle(w.id)}>
                  {w.enabled ? "Disable" : "Enable"}
                </Button>
                <Button variant="ghost" onClick={() => void test(w.id)}>
                  Test
                </Button>
                <Button variant="danger" onClick={() => void remove(w.id)}>
                  Delete
                </Button>
              </div>
            ) : (
              "Admin only"
            ),
          ])}
        />
      )}
    </AutomationShell>
  );
}
