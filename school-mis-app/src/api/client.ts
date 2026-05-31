import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Last X-Request-ID seen — included in error reports so backend & frontend logs correlate.
let _lastRequestId: string | null = null;
export const getLastRequestId = (): string | null => _lastRequestId;

function makeRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

// Attach token + X-Request-ID on every request
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

  const rid = makeRequestId();
  config.headers["X-Request-ID"] = rid;
  _lastRequestId = rid;

  return config;
});

// Handle 401 and 402; capture X-Request-ID from failed responses
api.interceptors.response.use(
  (r) => r,
  (err) => {
    // Keep the request ID from the failed response so error reports can include it
    const rid =
      err.response?.headers?.["x-request-id"] ||
      err.config?.headers?.["X-Request-ID"];
    if (rid) _lastRequestId = rid;

    if (err.response?.status === 401) {
      // Don't logout if we JUST logged in — the session INSERT on the backend
      // can lag behind the first auth check by a few hundred ms, producing a
      // spurious 401 that should not end the session.
      const loginAt = Number(sessionStorage.getItem("mis_login_at") || 0);
      const msSinceLogin = Date.now() - loginAt;
      if (msSinceLogin > 8_000) {
        import("@/stores/authStore").then(({ useAuthStore }) => {
          useAuthStore.getState().logout();
        });
      }
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
