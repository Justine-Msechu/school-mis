import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach token on every request — check both stores (sessionStorage for current tab, localStorage for persisted)
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("mis_token") || localStorage.getItem("mis_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      sessionStorage.removeItem("mis_token");
      localStorage.removeItem("mis_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;
