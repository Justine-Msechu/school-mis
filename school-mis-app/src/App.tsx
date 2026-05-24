import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import GradesPage from "@/pages/grades/GradesPage";
import StudentsPage from "@/pages/StudentsPage";
import PlaceholderPage from "@/pages/PlaceholderPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuthStore();
  return isLoggedIn ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const { isLoggedIn } = useAuthStore();

  return (
    <BrowserRouter>
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
                  <Route path="/teachers"   element={<PlaceholderPage title="Teachers" />} />
                  <Route path="/classes"    element={<PlaceholderPage title="Classes" />} />
                  <Route path="/attendance" element={<PlaceholderPage title="Attendance" />} />
                  <Route path="/library"    element={<PlaceholderPage title="Library" />} />
                  <Route path="/finance"    element={<PlaceholderPage title="Finance" />} />
                  <Route path="/accounting" element={<PlaceholderPage title="Accounting" />} />
                  <Route path="/transport"  element={<PlaceholderPage title="Transport" />} />
                  <Route path="/inventory"  element={<PlaceholderPage title="Inventory" />} />
                  <Route path="/health"     element={<PlaceholderPage title="Health" />} />
                  <Route path="/welfare"    element={<PlaceholderPage title="Welfare" />} />
                  <Route path="/promotion"  element={<PlaceholderPage title="Promotion" />} />
                  <Route path="/reports"    element={<PlaceholderPage title="Reports" />} />
                  <Route path="/settings"   element={<PlaceholderPage title="Settings" />} />
                </Routes>
              </AppShell>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
