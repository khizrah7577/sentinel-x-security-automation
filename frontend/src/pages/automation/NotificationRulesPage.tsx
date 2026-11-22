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
import { AutomationShell } from "./AutomationShared";

type Rule = {
  id: number;
  name: string;
  enabled: boolean;
  event_type: string;
  min_severity: string;
  notify_admins: boolean;
};

type Notif = {
  id: number;
  title: string;
  body: string;
  category: string;
  severity: string;
  link: string;
  is_read: boolean;
  created_at: string;
};

export default function NotificationRulesPage() {
  const { user } = useAuth();
  const [tick, setTick] = useState(0);
  const rules = useApi<Rule[]>(`/automation/notification-rules?_=${tick}`, [tick]);
  const inbox = useApi<Notif[]>(`/automation/notifications?_=${tick}`, [tick]);
  const [name, setName] = useState("Critical threat alerts");
  const [eventType, setEventType] = useState("critical_threat");
  const [error, setError] = useState<string | null>(null);

  const create = async () => {
    setError(null);
    try {
      await api("/automation/notification-rules", {
        method: "POST",
        body: JSON.stringify({
          name,
          enabled: true,
          event_type: eventType,
          min_severity: "high",
          notify_admins: true,
        }),
      });
      setTick((t) => t + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Create failed");
    }
  };

  const readAll = async () => {
    await api("/automation/notifications/read-all", { method: "POST" });
    setTick((t) => t + 1);
  };

  return (
    <AutomationShell
      title="Notification Rules"
      description="In-app notification rules and inbox for critical threats, investigations, approvals, and scheduler alerts."
      actions={
        <Button variant="secondary" onClick={() => void readAll()}>
          Mark all read
        </Button>
      }
    >
      {error && <ErrorBlock message={error} />}
      {user?.role === "admin" && (
        <GlassPanel className="flex flex-wrap gap-2 items-end">
          <label className="text-xs space-y-1">
            <span style={{ color: "var(--muted)" }}>Rule name</span>
            <input
              className="block rounded-lg border px-3 py-2 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="text-xs space-y-1">
            <span style={{ color: "var(--muted)" }}>Event type</span>
            <select
              className="block rounded-lg border px-3 py-2 bg-transparent text-sm"
              style={{ borderColor: "var(--border)" }}
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
            >
              {["critical_threat", "investigation", "approval", "health", "ml"].map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => void create()}>Add rule</Button>
        </GlassPanel>
      )}

      <h2 className="text-base font-semibold m-0">Rules</h2>
      {rules.loading && <LoadingBlock />}
      {rules.data && rules.data.length === 0 && <EmptyState title="No rules" detail="Create a notification rule." />}
      {rules.data && rules.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Event", "Min severity", "Admins", "Enabled"]}
          rows={rules.data.map((r) => [
            r.id,
            r.name,
            r.event_type,
            r.min_severity,
            r.notify_admins ? "Yes" : "No",
            r.enabled ? "Yes" : "No",
          ])}
        />
      )}

      <h2 className="text-base font-semibold m-0">Inbox</h2>
      {inbox.error && <ErrorBlock message={inbox.error} />}
      {inbox.data && inbox.data.length === 0 && (
        <EmptyState title="No notifications" detail="Alerts appear when automation or detection events fire." />
      )}
      {inbox.data && inbox.data.length > 0 && (
        <DataTable
          columns={["ID", "Title", "Severity", "Category", "Read", "Time"]}
          rows={inbox.data.map((n) => [
            n.id,
            <div key={n.id}>
              <div className="font-semibold">{n.title}</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {(n.body || "").slice(0, 100)}
              </div>
            </div>,
            n.severity,
            n.category,
            n.is_read ? "Yes" : "No",
            n.created_at ? new Date(n.created_at).toLocaleString() : "—",
          ])}
        />
      )}
    </AutomationShell>
  );
}
