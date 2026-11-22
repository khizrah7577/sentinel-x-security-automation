import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import AppLayout from "./layouts/AppLayout";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import MonitoringPage from "./pages/MonitoringPage";
import TopologyPage from "./pages/TopologyPage";
import DetectionsPage from "./pages/DetectionsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import IntelligencePage from "./pages/IntelligencePage";
import InvestigationsPage from "./pages/InvestigationsPage";
import ResponsePage from "./pages/ResponsePage";
import IncidentsPage from "./pages/IncidentsPage";
import PcapPage from "./pages/PcapPage";
import DatasetsPage from "./pages/DatasetsPage";
import ModelsPage from "./pages/ModelsPage";
import AgentsPage from "./pages/AgentsPage";
import ReportsPage from "./pages/ReportsPage";
import UsersPage from "./pages/UsersPage";
import SettingsPage from "./pages/SettingsPage";
import AutomationOverviewPage from "./pages/automation/AutomationOverviewPage";
import WorkflowBuilderPage from "./pages/automation/WorkflowBuilderPage";
import ActiveWorkflowsPage from "./pages/automation/ActiveWorkflowsPage";
import AgentSchedulerPage from "./pages/automation/AgentSchedulerPage";
import ResponseAutomationPage from "./pages/automation/ResponseAutomationPage";
import NotificationRulesPage from "./pages/automation/NotificationRulesPage";
import AutomationHistoryPage from "./pages/automation/AutomationHistoryPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center nexus-grid-bg" style={{ color: "var(--muted)" }}>
        Initializing SENTINEL X…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppLayout />
          </Protected>
        }
      >
        <Route index element={<OverviewPage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
        <Route path="topology" element={<TopologyPage />} />
        <Route path="detections" element={<DetectionsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="intelligence" element={<IntelligencePage />} />
        <Route path="investigations" element={<InvestigationsPage />} />
        <Route path="response" element={<ResponsePage />} />
        <Route path="incidents" element={<IncidentsPage />} />
        <Route path="pcap" element={<PcapPage />} />
        <Route path="datasets" element={<DatasetsPage />} />
        <Route path="models" element={<ModelsPage />} />
        <Route path="agents" element={<AgentsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="automation" element={<AutomationOverviewPage />} />
        <Route path="automation/workflows" element={<WorkflowBuilderPage />} />
        <Route path="automation/active" element={<ActiveWorkflowsPage />} />
        <Route path="automation/scheduler" element={<AgentSchedulerPage />} />
        <Route path="automation/response" element={<ResponseAutomationPage />} />
        <Route path="automation/notifications" element={<NotificationRulesPage />} />
        <Route path="automation/history" element={<AutomationHistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
