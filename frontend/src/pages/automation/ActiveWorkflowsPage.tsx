import { useApi } from "../../hooks/useApi";
import { DataTable, EmptyState, ErrorBlock, LoadingBlock } from "../../components/nexus/primitives";
import { AutomationShell, StatusBadge } from "./AutomationShared";

type Workflow = {
  id: number;
  name: string;
  trigger: string;
  enabled: boolean;
  last_status: string;
  run_count: number;
  last_run_at?: string;
  description: string;
};

export default function ActiveWorkflowsPage() {
  const list = useApi<Workflow[]>("/automation/active");
  return (
    <AutomationShell
      title="Active Workflows"
      description="Enabled automation rules currently evaluated by the engine."
    >
      {list.loading && <LoadingBlock />}
      {list.error && <ErrorBlock message={list.error} />}
      {list.data && list.data.length === 0 && (
        <EmptyState title="No active workflows" detail="Enable workflows in the Workflow Builder." />
      )}
      {list.data && list.data.length > 0 && (
        <DataTable
          columns={["ID", "Name", "Trigger", "Runs", "Last status", "Last run", "Description"]}
          rows={list.data.map((w) => [
            w.id,
            w.name,
            w.trigger,
            w.run_count,
            <StatusBadge key={w.id} status={w.last_status || "—"} />,
            w.last_run_at ? new Date(w.last_run_at).toLocaleString() : "—",
            (w.description || "—").slice(0, 80),
          ])}
        />
      )}
    </AutomationShell>
  );
}
