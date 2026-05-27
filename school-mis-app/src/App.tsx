import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "@/pages/LoginPage";
import SetupPage from "@/pages/SetupPage";
import DashboardPage from "@/pages/DashboardPage";
import GradesPage from "@/pages/grades/GradesPage";
import StudentsPage from "@/pages/StudentsPage";
import TeachersPage from "@/pages/TeachersPage";
import ClassesPage from "@/pages/ClassesPage";
import AttendancePage from "@/pages/AttendancePage";
import FinancePage from "@/pages/FinancePage";
import LibraryPage from "@/pages/LibraryPage";
import AccountingPage from "@/pages/AccountingPage";
import TransportPage from "@/pages/TransportPage";
import InventoryPage from "@/pages/InventoryPage";
import HealthPage from "@/pages/HealthPage";
import WelfarePage from "@/pages/WelfarePage";
import PromotionPage from "@/pages/PromotionPage";
import ReportsPage from "@/pages/ReportsPage";
import SettingsPage from "@/pages/SettingsPage";
import AuditLogPage from "@/pages/AuditLogPage";
import EnrollmentPage from "@/pages/EnrollmentPage";
import GuardiansPage from "@/pages/GuardiansPage";
import ReportCardsPage from "@/pages/ReportCardsPage";
import ForceChangePassword from "@/components/ui/ForceChangePassword";
import RbacPage from "@/pages/RbacPage";
import PayrollPage from "@/pages/PayrollPage";
import NGOPage from "@/pages/NGOPage";
import SubscriptionPage from "@/pages/SubscriptionPage";
import LandingPage from "@/pages/LandingPage";
import RegisterPage from "@/pages/RegisterPage";
import SuperAdminPage from "@/pages/SuperAdminPage";
import SuperAdminShell from "@/components/layout/SuperAdminShell";
import PlatformDashboard from "@/pages/platform/PlatformDashboard";
import PlatformSettingsPage from "@/pages/platform/PlatformSettingsPage";
import { getSetupStatus } from "@/api/setup";
import { useImpersonationStore } from "@/stores/impersonationStore";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuthStore();
  return isLoggedIn ? <>{children}</> : <Navigate to="/login" replace />;
}

function PermRoute({ perm, children }: { perm: string; children: React.ReactNode }) {
  const { can } = useAuthStore();
  return can(perm) ? <>{children}</> : <Navigate to="/" replace />;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuthStore();
  return user?.role === "admin" || user?.role === "superadmin" ? <>{children}</> : <Navigate to="/" replace />;
}


function AuthenticatedApp() {
  const { user } = useAuthStore();
  const { active: isImpersonating } = useImpersonationStore();

  // Superadmin not currently impersonating a school → platform shell
  if (user?.role === "superadmin" && !isImpersonating) {
    return (
      <SuperAdminShell>
        <Routes>
          <Route path="/platform"          element={<PlatformDashboard />} />
          <Route path="/platform/schools"  element={<SuperAdminPage />} />
          <Route path="/platform/audit"    element={<AuditLogPage />} />
          <Route path="/platform/settings" element={<PlatformSettingsPage />} />
          <Route path="/*"                 element={<Navigate to="/platform" replace />} />
        </Routes>
      </SuperAdminShell>
    );
  }

  // Regular school staff OR superadmin impersonating a school
  return (
    <AppShell>
      <Routes>
        <Route path="/"            element={<DashboardPage />} />
        <Route path="/grades/*"    element={<PermRoute perm="grades.view"><GradesPage /></PermRoute>} />
        <Route path="/students"    element={<PermRoute perm="student.view"><StudentsPage /></PermRoute>} />
        <Route path="/teachers"    element={<PermRoute perm="teachers.view"><TeachersPage /></PermRoute>} />
        <Route path="/classes"     element={<PermRoute perm="classes.view"><ClassesPage /></PermRoute>} />
        <Route path="/attendance"  element={<PermRoute perm="attendance.view"><AttendancePage /></PermRoute>} />
        <Route path="/library"     element={<PermRoute perm="library.view"><LibraryPage /></PermRoute>} />
        <Route path="/finance"     element={<PermRoute perm="finance.view"><FinancePage /></PermRoute>} />
        <Route path="/accounting"  element={<PermRoute perm="accounting.view"><AccountingPage /></PermRoute>} />
        <Route path="/transport"   element={<PermRoute perm="transport.view"><TransportPage /></PermRoute>} />
        <Route path="/inventory"   element={<PermRoute perm="inventory.view"><InventoryPage /></PermRoute>} />
        <Route path="/health"      element={<PermRoute perm="health.view"><HealthPage /></PermRoute>} />
        <Route path="/welfare"     element={<PermRoute perm="welfare.view"><WelfarePage /></PermRoute>} />
        <Route path="/promotion"   element={<PermRoute perm="student.promote"><PromotionPage /></PermRoute>} />
        <Route path="/reports"     element={<PermRoute perm="reports.view"><ReportsPage /></PermRoute>} />
        <Route path="/settings"    element={<PermRoute perm="settings.view"><SettingsPage /></PermRoute>} />
        <Route path="/audit"       element={<PermRoute perm="audit.view"><AuditLogPage /></PermRoute>} />
        <Route path="/enrollment"  element={<PermRoute perm="enrollment.view"><EnrollmentPage /></PermRoute>} />
        <Route path="/guardians"   element={<PermRoute perm="guardian.view"><GuardiansPage /></PermRoute>} />
        <Route path="/report-cards" element={<PermRoute perm="report_cards.view"><ReportCardsPage /></PermRoute>} />
        <Route path="/rbac"         element={<AdminRoute><RbacPage /></AdminRoute>} />
        <Route path="/payroll"      element={<PermRoute perm="payroll.view"><PayrollPage /></PermRoute>} />
        <Route path="/ngo"          element={<PermRoute perm="ngo.view"><NGOPage /></PermRoute>} />
        <Route path="/subscription" element={<AdminRoute><SubscriptionPage /></AdminRoute>} />
      </Routes>
    </AppShell>
  );
}

export default function App() {
  const { isLoggedIn } = useAuthStore();
  const [needsSetup, setNeedsSetup] = useState<boolean | null>(null);

  useEffect(() => {
    getSetupStatus()
      .then((s) => setNeedsSetup(s.needs_setup))
      .catch(() => setNeedsSetup(false));
  }, []);

  if (needsSetup === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <ForceChangePassword />
      <Routes>
        {/* Public pages */}
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/register" element={isLoggedIn ? <Navigate to="/" replace /> : <RegisterPage />} />

        {/* Setup wizard */}
        <Route path="/setup" element={needsSetup ? <SetupPage /> : <Navigate to="/login" replace />} />

        {/* Login */}
        <Route path="/login" element={
          needsSetup ? <Navigate to="/setup" replace /> :
          isLoggedIn ? <Navigate to="/" replace /> :
          <LoginPage />
        } />

        {/* Authenticated area */}
        <Route
          path="/*"
          element={
            needsSetup ? <Navigate to="/setup" replace /> :
            <PrivateRoute>
              <AuthenticatedApp />
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
