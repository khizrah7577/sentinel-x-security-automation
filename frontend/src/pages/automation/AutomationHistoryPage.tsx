import { useApi } from "../../hooks/useApi";
import { DataTable, EmptyState, ErrorBlock, LoadingBlock } from "../../components/nexus/primitives";
import { AutomationShell, StatusBadge } from "./AutomationShared";

type Row = {
  id: number;
  workflow_id: number | null;
  trigger: string;
  status: string;
  error_message: string;
  duration_ms: number;
  created_at: string;
  result_json: string;
};

export default function AutomationHistoryPage() {
  const hist = useApi<Row[]>("/automation/history?limit=100");
  return (
    <AutomationShell
      title="Automation History"
      description="Execution log for workflow evaluations — successes, skips, and failures with messages."
    >
      {hist.loading && <LoadingBlock />}
      {hist.error && <ErrorBlock message={hist.error} />}
      {hist.data && hist.data.length === 0 && (
        <EmptyState title="No executions yet" detail="History appears after workflows evaluate real events." />
      )}
      {hist.data && hist.data.length > 0 && (
        <DataTable
          columns={["ID", "Workflow", "Trigger", "Status", "Duration", "Error", "Time"]}
          rows={hist.data.map((r) => [
            r.id,
            r.workflow_id ?? "—",
            r.trigger,
            <StatusBadge key={r.id} status={r.status} />,
            `${r.duration_ms} ms`,
            r.error_message || "—",
            r.created_at ? new Date(r.created_at).toLocaleString() : "—",
          ])}
        />
      )}
    </AutomationShell>
  );
}
