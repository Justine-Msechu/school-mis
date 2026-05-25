import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "@/pages/LoginPage";
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
import TimetablePage from "@/pages/TimetablePage";
import ReportCardsPage from "@/pages/ReportCardsPage";
import ForceChangePassword from "@/components/ui/ForceChangePassword";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuthStore();
  return isLoggedIn ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const { isLoggedIn } = useAuthStore();

  return (
    <BrowserRouter>
      <ForceChangePassword />
      <Routes>
        <Route path="/login" element={isLoggedIn ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <AppShell>
                <Routes>
                  <Route path="/"           element={<DashboardPage />} />
                  <Route path="/grades/*"   element={<GradesPage />} />
                  <Route path="/students"   element={<StudentsPage />} />
                  <Route path="/teachers"   element={<TeachersPage />} />
                  <Route path="/classes"    element={<ClassesPage />} />
                  <Route path="/attendance" element={<AttendancePage />} />
                  <Route path="/library"    element={<LibraryPage />} />
                  <Route path="/finance"    element={<FinancePage />} />
                  <Route path="/accounting" element={<AccountingPage />} />
                  <Route path="/transport"  element={<TransportPage />} />
                  <Route path="/inventory"  element={<InventoryPage />} />
                  <Route path="/health"     element={<HealthPage />} />
                  <Route path="/welfare"    element={<WelfarePage />} />
                  <Route path="/promotion"  element={<PromotionPage />} />
                  <Route path="/reports"    element={<ReportsPage />} />
                  <Route path="/settings"   element={<SettingsPage />} />
                  <Route path="/audit"        element={<AuditLogPage />} />
                  <Route path="/enrollment"  element={<EnrollmentPage />} />
                  <Route path="/guardians"   element={<GuardiansPage />} />
                  <Route path="/timetable"   element={<TimetablePage />} />
                  <Route path="/report-cards" element={<ReportCardsPage />} />
                </Routes>
              </AppShell>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
