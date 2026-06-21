import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./lib/auth";
import Login from "./pages/Login";
import PortalLayout from "./pages/PortalLayout";
import FolderView from "./pages/FolderView";
import DashboardView from "./pages/DashboardView";
import WorkspacePage from "./pages/WorkspacePage";
import ApprovalsPage from "./pages/ApprovalsPage";
import Welcome from "./pages/Welcome";

export default function App() {
  const { me, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  if (!me) return <Login />;

  return (
    <Routes>
      <Route element={<PortalLayout />}>
        <Route index element={<Welcome />} />
        <Route path="folders/:slug" element={<FolderView />} />
        <Route path="reports/:reportId" element={<DashboardView />} />
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
