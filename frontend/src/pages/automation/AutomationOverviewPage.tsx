import { Link } from "react-router-dom";
import { useApi } from "../../hooks/useApi";
import { Button, ErrorBlock, GlassPanel, LoadingBlock, MetricCard } from "../../components/nexus/primitives";
import { AutomationShell, CatalogNote } from "./AutomationShared";
import { Activity, Bell, Bot, History, Shield, Workflow } from "lucide-react";

type Overview = {
  workflows_total: number;
  workflows_enabled: number;
  scheduled_tasks: number;
  scheduled_enabled: number;
  executions_24h: number;
  unread_notifications: number;
  policies: number;
  notification_rules: number;
  catalog: {
    triggers: string[];
    condition_fields: string[];
    actions: string[];
  };
};

const links = [
  { to: "/automation/workflows", label: "Workflow Builder", icon: Workflow },
  { to: "/automation/active", label: "Active Workflows", icon: Activity },
  { to: "/automation/scheduler", label: "Agent Scheduler", icon: Bot },
  { to: "/automation/response", label: "Response Automation", icon: Shield },
  { to: "/automation/notifications", label: "Notification Rules", icon: Bell },
  { to: "/automation/history", label: "Automation History", icon: History },
];

export default function AutomationOverviewPage() {
  const ov = useApi<Overview>("/automation/overview");

  return (
    <AutomationShell
      title="Automation Overview"
      description="Event-driven detection, LangGraph investigations, scheduled jobs, and allowlisted response automation."
    >
      <CatalogNote />
      {ov.loading && <LoadingBlock />}
      {ov.error && <ErrorBlock message={ov.error} />}
      {ov.data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Enabled workflows"
              value={`${ov.data.workflows_enabled}/${ov.data.workflows_total}`}
              icon={<Workflow className="w-5 h-5" />}
              accent="var(--accent)"
            />
            <MetricCard
              label="Scheduled tasks"
              value={`${ov.data.scheduled_enabled}/${ov.data.scheduled_tasks}`}
              icon={<Bot className="w-5 h-5" />}
              accent="var(--accent-ai)"
            />
            <MetricCard
              label="Workflow executions"
              value={ov.data.executions_24h}
              icon={<History className="w-5 h-5" />}
              accent="var(--accent-secondary)"
            />
            <MetricCard
              label="Unread notifications"
              value={ov.data.unread_notifications}
              icon={<Bell className="w-5 h-5" />}
              accent="var(--critical)"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {links.map((l) => (
              <Link key={l.to} to={l.to} className="no-underline">
                <GlassPanel className="hover:border-[var(--accent)] transition-colors h-full">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-xl grid place-items-center"
                      style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
                    >
                      <l.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-bold text-sm" style={{ color: "var(--text)" }}>
                        {l.label}
                      </div>
                      <div className="text-xs" style={{ color: "var(--muted)" }}>
                        Open module
                      </div>
                    </div>
                  </div>
                </GlassPanel>
              </Link>
            ))}
          </div>

          <GlassPanel>
            <h3 className="text-sm font-bold m-0 mb-2">Supported catalog</h3>
            <div className="grid md:grid-cols-3 gap-4 text-xs">
              <div>
                <div className="font-semibold mb-1" style={{ color: "var(--muted)" }}>
                  Triggers
                </div>
                <ul className="m-0 pl-4">
                  {ov.data.catalog.triggers.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="font-semibold mb-1" style={{ color: "var(--muted)" }}>
                  Conditions
                </div>
                <ul className="m-0 pl-4">
                  {ov.data.catalog.condition_fields.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="font-semibold mb-1" style={{ color: "var(--muted)" }}>
                  Actions
                </div>
                <ul className="m-0 pl-4">
                  {ov.data.catalog.actions.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="mt-4">
              <Link to="/pcap">
                <Button variant="secondary">Process PCAP to feed automation</Button>
              </Link>
            </div>
          </GlassPanel>
        </>
      )}
    </AutomationShell>
  );
}
