import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";

// ── Always-eager: tiny shells needed on every page ───────────────────────────
import AppShell         from "@/components/layout/AppShell";
import SuperAdminShell  from "@/components/layout/SuperAdminShell";
import ForceChangePassword from "@/components/ui/ForceChangePassword";
import { getSetupStatus } from "@/api/setup";
import { useImpersonationStore } from "@/stores/impersonationStore";

// ── Lazy pages — each becomes its own JS chunk ────────────────────────────────
const LoginPage                 = lazy(() => import("@/pages/LoginPage"));
const SetupPage                 = lazy(() => import("@/pages/SetupPage"));
const LandingPage               = lazy(() => import("@/pages/LandingPage"));
const RegisterPage              = lazy(() => import("@/pages/RegisterPage"));
const DashboardPage             = lazy(() => import("@/pages/DashboardPage"));
const GradesPage                = lazy(() => import("@/pages/grades/GradesPage"));
const StudentsPage              = lazy(() => import("@/pages/StudentsPage"));
const TeachersPage              = lazy(() => import("@/pages/TeachersPage"));
const ClassesPage               = lazy(() => import("@/pages/ClassesPage"));
const AttendancePage            = lazy(() => import("@/pages/AttendancePage"));
const FinancePage               = lazy(() => import("@/pages/FinancePage"));
const LibraryPage               = lazy(() => import("@/pages/LibraryPage"));
const AccountingPage            = lazy(() => import("@/pages/AccountingPage"));
const TransportPage             = lazy(() => import("@/pages/TransportPage"));
const InventoryPage             = lazy(() => import("@/pages/InventoryPage"));
const HealthPage                = lazy(() => import("@/pages/HealthPage"));
const WelfarePage               = lazy(() => import("@/pages/WelfarePage"));
const PromotionPage             = lazy(() => import("@/pages/PromotionPage"));
const ReportsPage               = lazy(() => import("@/pages/ReportsPage"));
const SettingsPage              = lazy(() => import("@/pages/SettingsPage"));
const AuditLogPage              = lazy(() => import("@/pages/AuditLogPage"));
const EnrollmentPage            = lazy(() => import("@/pages/EnrollmentPage"));
const GuardiansPage             = lazy(() => import("@/pages/GuardiansPage"));
const ReportCardsPage           = lazy(() => import("@/pages/ReportCardsPage"));
const RbacPage                  = lazy(() => import("@/pages/RbacPage"));
const PayrollPage               = lazy(() => import("@/pages/PayrollPage"));
const NGOPage                   = lazy(() => import("@/pages/NGOPage"));
const SubscriptionPage          = lazy(() => import("@/pages/SubscriptionPage"));
const TimetablePage             = lazy(() => import("@/pages/TimetablePage"));
const SuperAdminPage            = lazy(() => import("@/pages/SuperAdminPage"));
const PlatformDashboard         = lazy(() => import("@/pages/platform/PlatformDashboard"));
const PlatformSettingsPage      = lazy(() => import("@/pages/platform/PlatformSettingsPage"));
const PlatformFeaturesPage      = lazy(() => import("@/pages/platform/PlatformFeaturesPage"));
const PlatformAnnouncementsPage = lazy(() => import("@/pages/platform/PlatformAnnouncementsPage"));
const ErrorLogsPage             = lazy(() => import("@/pages/platform/ErrorLogsPage"));
const PlatformMediaPage         = lazy(() => import("@/pages/platform/PlatformMediaPage"));
const PlatformRbacPage          = lazy(() => import("@/pages/platform/PlatformRbacPage"));

// ── Shared page-level loading fallback ───────────────────────────────────────
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

// ── Lazy setup check — only runs when user navigates to /setup ────────────────
function SetupRoute() {
  const [state, setState] = useState<"loading" | "needed" | "done">("loading");

  useEffect(() => {
    getSetupStatus()
      .then((s) => setState(s.needs_setup ? "needed" : "done"))
      .catch(() => setState("done"));
  }, []);

  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  return state === "needed" ? <SetupPage /> : <Navigate to="/login" replace />;
}

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

  if (user?.role === "superadmin" && !isImpersonating) {
    return (
      <SuperAdminShell>
        <Routes>
          <Route path="/platform"               element={<PlatformDashboard />} />
          <Route path="/platform/schools"       element={<SuperAdminPage />} />
          <Route path="/platform/features"      element={<PlatformFeaturesPage />} />
          <Route path="/platform/announcements" element={<PlatformAnnouncementsPage />} />
          <Route path="/platform/audit"         element={<AuditLogPage />} />
          <Route path="/platform/errors"        element={<ErrorLogsPage />} />
          <Route path="/platform/media"         element={<PlatformMediaPage />} />
          <Route path="/platform/rbac"          element={<PlatformRbacPage />} />
          <Route path="/platform/settings"      element={<PlatformSettingsPage />} />
          <Route path="/*"                      element={<Navigate to="/platform" replace />} />
        </Routes>
      </SuperAdminShell>
    );
  }

  return (
    <AppShell>
      <Routes>
        <Route path="/"             element={<DashboardPage />} />
        <Route path="/grades/*"     element={<PermRoute perm="grades.view"><GradesPage /></PermRoute>} />
        <Route path="/students"     element={<PermRoute perm="student.view"><StudentsPage /></PermRoute>} />
        <Route path="/teachers"     element={<PermRoute perm="teachers.view"><TeachersPage /></PermRoute>} />
        <Route path="/classes"      element={<PermRoute perm="classes.view"><ClassesPage /></PermRoute>} />
        <Route path="/attendance"   element={<PermRoute perm="attendance.view"><AttendancePage /></PermRoute>} />
        <Route path="/library"      element={<PermRoute perm="library.view"><LibraryPage /></PermRoute>} />
        <Route path="/finance"      element={<PermRoute perm="finance.view"><FinancePage /></PermRoute>} />
        <Route path="/accounting"   element={<PermRoute perm="accounting.view"><AccountingPage /></PermRoute>} />
        <Route path="/transport"    element={<PermRoute perm="transport.view"><TransportPage /></PermRoute>} />
        <Route path="/inventory"    element={<PermRoute perm="inventory.view"><InventoryPage /></PermRoute>} />
        <Route path="/health"       element={<PermRoute perm="health.view"><HealthPage /></PermRoute>} />
        <Route path="/welfare"      element={<PermRoute perm="welfare.view"><WelfarePage /></PermRoute>} />
        <Route path="/promotion"    element={<PermRoute perm="student.promote"><PromotionPage /></PermRoute>} />
        <Route path="/reports"      element={<PermRoute perm="reports.view"><ReportsPage /></PermRoute>} />
        <Route path="/settings"     element={<PermRoute perm="settings.view"><SettingsPage /></PermRoute>} />
        <Route path="/audit"        element={<PermRoute perm="audit.view"><AuditLogPage /></PermRoute>} />
        <Route path="/enrollment"   element={<PermRoute perm="enrollment.view"><EnrollmentPage /></PermRoute>} />
        <Route path="/guardians"    element={<PermRoute perm="guardian.view"><GuardiansPage /></PermRoute>} />
        <Route path="/report-cards" element={<PermRoute perm="report_cards.view"><ReportCardsPage /></PermRoute>} />
        <Route path="/rbac"         element={<AdminRoute><RbacPage /></AdminRoute>} />
        <Route path="/payroll"      element={<PermRoute perm="payroll.view"><PayrollPage /></PermRoute>} />
        <Route path="/ngo"          element={<PermRoute perm="ngo.view"><NGOPage /></PermRoute>} />
        <Route path="/timetable"    element={<PermRoute perm="timetable.view"><TimetablePage /></PermRoute>} />
        <Route path="/subscription" element={<AdminRoute><SubscriptionPage /></AdminRoute>} />
      </Routes>
    </AppShell>
  );
}

export default function App() {
  const { isLoggedIn, user } = useAuthStore();
  const home = user?.role === "superadmin" ? "/platform" : "/";

  return (
    <BrowserRouter>
      <ForceChangePassword />
      <ErrorBoundary>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/landing"  element={<LandingPage />} />
            <Route path="/register" element={
              // Superadmin can always access the registration page (testing / onboarding).
              // All other logged-in users are redirected home.
              isLoggedIn && user?.role !== "superadmin"
                ? <Navigate to={home} replace />
                : <RegisterPage />
            } />
            <Route path="/setup"    element={<SetupRoute />} />
            <Route path="/login"    element={isLoggedIn ? <Navigate to={home} replace /> : <LoginPage />} />
            <Route path="/*"        element={
              !isLoggedIn
                ? <LandingPage />
                : <PrivateRoute><AuthenticatedApp /></PrivateRoute>
            } />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
