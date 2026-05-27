import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach token on every request
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("mis_token") || localStorage.getItem("mis_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;

  // Superadmin impersonation: scope requests to the chosen school
  try {
    const auth = JSON.parse(localStorage.getItem("mis-auth") || "{}");
    if (auth?.state?.user?.role === "superadmin") {
      const imp = JSON.parse(localStorage.getItem("mis-impersonation") || "{}");
      if (imp?.state?.active && imp?.state?.schoolId) {
        config.headers["X-School-Id"] = String(imp.state.schoolId);
      }
    }
  } catch { /* ignore */ }

  return config;
});

// Handle 401 and 402
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      // Clear auth state properly so the next render shows the landing page —
      // no hard page reload, which would restart the flicker loop.
      // Dynamic import avoids a circular-module reference at init time.
      import("@/stores/authStore").then(({ useAuthStore }) => {
        useAuthStore.getState().logout();
      });
    }
    if (err.response?.status === 402) {
      const detail = err.response.data?.detail ?? {};
      if (detail.code === "plan_restricted") {
        window.dispatchEvent(new CustomEvent("plan:restricted", { detail }));
      } else {
        window.dispatchEvent(new CustomEvent("subscription:expired", { detail }));
      }
    }
    return Promise.reject(err);
  }
);

export default api;
