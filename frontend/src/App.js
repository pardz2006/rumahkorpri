import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, useAuth, ROLE_HOME } from "./context/AuthContext";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import ProjectDetail from "./pages/ProjectDetail";
import ConsumerPortal from "./pages/ConsumerPortal";
import KorpriDashboard from "./pages/KorpriDashboard";
import DeveloperDashboard from "./pages/DeveloperDashboard";
import BtnDashboard from "./pages/BtnDashboard";
import Architecture from "./pages/Architecture";
import PublicSimulation from "./pages/PublicSimulation";
import "./App.css";

function Protected({ roles, children }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="min-h-screen grid place-items-center text-slate-400">Memuat...</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role]} replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/proyek/:id" element={<ProjectDetail />} />
          <Route path="/arsitektur" element={<Architecture />} />
          <Route path="/s/:token" element={<PublicSimulation />} />
          <Route path="/portal" element={<Protected roles={["consumer"]}><ConsumerPortal /></Protected>} />
          <Route path="/crm" element={<Protected roles={["admin_korpri"]}><KorpriDashboard /></Protected>} />
          <Route path="/developer" element={<Protected roles={["admin_developer", "admin_korpri"]}><DeveloperDashboard /></Protected>} />
          <Route path="/btn" element={<Protected roles={["btn_evaluator"]}><BtnDashboard /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
