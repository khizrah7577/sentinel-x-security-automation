import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  Bot,
  Brain,
  ChevronLeft,
  ChevronRight,
  Crosshair,
  Database,
  FileSearch,
  FileText,
  LayoutDashboard,
  LogOut,
  Moon,
  Network,
  Settings,
  Shield,
  Sun,
  Users,
  Workflow,
  Hexagon,
  Siren,
  Zap,
  Timer,
  BellRing,
  GitBranch,
  ListChecks,
  History,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import { DashboardApi, HealthApi, type DashboardStats, type Health } from "../services/api";
import { StatusDot } from "../components/nexus/primitives";
import { NotificationBell } from "../components/nexus/NotificationBell";

type NavItem = { to: string; label: string; icon: typeof LayoutDashboard };
type NavGroup = { title: string; items: NavItem[] };

const groups: NavGroup[] = [
  {
    title: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    title: "Network Security",
    items: [
      { to: "/monitoring", label: "Network Monitoring", icon: Network },
      { to: "/topology", label: "Network Topology", icon: Hexagon },
      { to: "/detections", label: "Attack Detection", icon: Crosshair },
      { to: "/analytics", label: "Threat Analytics", icon: Activity },
      { to: "/pcap", label: "PCAP Analysis", icon: FileSearch },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { to: "/intelligence", label: "Intelligence", icon: Bot },
      { to: "/investigations", label: "AI Investigation", icon: Workflow },
      { to: "/agents", label: "Agent Command Center", icon: Activity },
      { to: "/models", label: "ML Model Management", icon: Brain },
      { to: "/datasets", label: "Datasets", icon: Database },
    ],
  },
  {
    title: "Response",
    items: [
      { to: "/response", label: "Response Center", icon: AlertTriangle },
      { to: "/incidents", label: "Incident Management", icon: Siren },
      { to: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    title: "Automation Center",
    items: [
      { to: "/automation", label: "Automation Overview", icon: Zap },
      { to: "/automation/workflows", label: "Workflow Builder", icon: GitBranch },
      { to: "/automation/active", label: "Active Workflows", icon: ListChecks },
      { to: "/automation/scheduler", label: "Agent Scheduler", icon: Timer },
      { to: "/automation/response", label: "Response Automation", icon: Shield },
      { to: "/automation/notifications", label: "Notification Rules", icon: BellRing },
      { to: "/automation/history", label: "Automation History", icon: History },
    ],
  },
  {
    title: "System",
    items: [
      { to: "/users", label: "User Management", icon: Users },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { theme, resolved, setTheme } = useTheme();
  const reduce = useReducedMotion();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [s, h] = await Promise.all([DashboardApi.stats(), HealthApi.get()]);
        if (!cancelled) {
          setStats(s);
          setHealth(h);
        }
      } catch {
        /* header stays partial */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const width = collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-w)";

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)", color: "var(--text)" }}>
      <aside
        className="border-r flex flex-col transition-[width] duration-300 shrink-0 sticky top-0 h-screen z-20"
        style={{
          width,
          background: "var(--bg-secondary)",
          borderColor: "var(--border)",
        }}
      >
        <div className="flex items-center gap-3 px-4 py-5 border-b" style={{ borderColor: "var(--border)" }}>
          <div
            className="w-10 h-10 rounded-xl grid place-items-center shrink-0"
            style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
          >
            <Shield className="w-5 h-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="font-extrabold text-sm tracking-wide truncate">SENTINEL X</div>
              <div className="text-[10px] uppercase tracking-[0.08em] truncate leading-snug" style={{ color: "var(--muted)" }}>
                Intelligent Cybersecurity & Threat Response
              </div>
            </div>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-4">
          {groups.map((g) => (
            <div key={g.title}>
              {!collapsed && (
                <div
                  className="px-3 mb-1.5 text-[10px] font-bold uppercase tracking-[0.16em]"
                  style={{ color: "var(--muted)" }}
                >
                  {g.title}
                </div>
              )}
              <div className="space-y-0.5">
                {g.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    title={item.label}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                        isActive ? "font-semibold" : "font-medium"
                      }`
                    }
                    style={({ isActive }) => ({
                      background: isActive ? "var(--accent-soft)" : "transparent",
                      color: isActive ? "var(--accent)" : "var(--text)",
                    })}
                  >
                    <item.icon className="w-4 h-4 shrink-0" />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <button
          type="button"
          className="m-2 mb-3 inline-flex items-center justify-center gap-2 rounded-xl border px-2 py-2 text-xs font-semibold"
          style={{ borderColor: "var(--border)", color: "var(--muted)" }}
          onClick={() => setCollapsed((c) => !c)}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          {!collapsed && "Collapse"}
        </button>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header
          className="sticky top-0 z-10 border-b px-4 md:px-6 py-3 flex flex-wrap items-center gap-3 justify-between"
          style={{
            background: "color-mix(in srgb, var(--bg-secondary) 92%, transparent)",
            borderColor: "var(--border)",
            backdropFilter: "blur(10px)",
          }}
        >
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <StatusPill
              label="Monitoring"
              value={stats?.monitoring_mode || health?.monitoring_mode || "—"}
              tone={(stats?.monitoring_mode || health?.monitoring_mode) === "live" ? "ok" : "warn"}
            />
            <StatusPill
              label="Network"
              value={health?.database?.status === "connected" ? "DB online" : "DB degraded"}
              tone={health?.database?.status === "connected" ? "ok" : "danger"}
            />
            <StatusPill
              label="AI Agents"
              value={stats?.ai_configured ? "Configured" : "Rule-based"}
              tone={stats?.ai_configured ? "ai" : "muted"}
            />
            <StatusPill
              label="ML Model"
              value={stats?.active_model || "None active"}
              tone={stats?.active_model ? "ok" : "warn"}
            />
            {(stats?.critical_incidents || 0) > 0 && (
              <span
                className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-semibold nexus-critical-glow"
                style={{ background: "color-mix(in srgb, var(--critical) 16%, transparent)", color: "var(--critical)" }}
              >
                <StatusDot tone="danger" />
                {stats?.critical_incidents} critical
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <NotificationBell />
            <button
              type="button"
              className="rounded-xl border p-2"
              style={{ borderColor: "var(--border)" }}
              onClick={() => setTheme(resolved === "dark" ? "light" : "dark")}
              aria-label="Toggle theme"
              title={`Theme: ${theme}`}
            >
              {resolved === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            <div
              className="hidden sm:flex items-center gap-2 rounded-xl border px-3 py-1.5"
              style={{ borderColor: "var(--border)" }}
            >
              <div
                className="w-7 h-7 rounded-lg grid place-items-center text-[11px] font-bold"
                style={{ background: "var(--accent-ai-soft)", color: "var(--accent-ai)" }}
              >
                {(user?.full_name || user?.email || "?").slice(0, 1).toUpperCase()}
              </div>
              <div className="text-xs leading-tight">
                <div className="font-semibold">{user?.full_name || user?.email}</div>
                <div style={{ color: "var(--muted)" }}>{user?.role}</div>
              </div>
            </div>
            <button
              type="button"
              className="rounded-xl border p-2"
              style={{ borderColor: "var(--border)", color: "var(--muted)" }}
              onClick={() => void logout()}
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 nexus-grid-bg">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? undefined : { opacity: 0, y: -6 }}
              transition={{ duration: 0.22 }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function StatusPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "ok" | "warn" | "danger" | "muted" | "ai";
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 max-w-[220px]"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      <StatusDot tone={tone} />
      <span style={{ color: "var(--muted)" }}>{label}</span>
      <span className="font-semibold truncate">{value}</span>
    </span>
  );
}
