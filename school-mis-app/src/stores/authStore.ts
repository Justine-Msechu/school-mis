import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/api/auth";

// sessionStorage key for non-rememberMe sessions (survives page refresh, not new tab)
const _SESSION_KEY = "mis-auth-session";

// Read persisted auth synchronously before React's first render.
// Checks localStorage first (rememberMe=true), then sessionStorage (rememberMe=false).
const _readPersisted = (): { isLoggedIn: boolean; user: User | null; token: string | null; mustChangePw: boolean; rememberMe: boolean } => {
  try {
    // 1. localStorage — only if user explicitly chose "Remember me"
    const raw = localStorage.getItem("mis-auth");
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { user?: User; token?: string; mustChangePw?: boolean; rememberMe?: boolean } };
      const { user, token, mustChangePw, rememberMe } = parsed?.state ?? {};
      if (rememberMe && token && user) {
        sessionStorage.setItem("mis_token", token);
        return { isLoggedIn: true, user, token, mustChangePw: mustChangePw ?? false, rememberMe: true };
      }
    }
    // 2. sessionStorage — non-rememberMe sessions (page refresh safe, not cross-tab)
    const session = sessionStorage.getItem(_SESSION_KEY);
    if (session) {
      const { user, token, mustChangePw } = JSON.parse(session) as { user?: User; token?: string; mustChangePw?: boolean };
      if (token && user) {
        sessionStorage.setItem("mis_token", token);
        return { isLoggedIn: true, user, token, mustChangePw: mustChangePw ?? false, rememberMe: false };
      }
    }
  } catch { /* storage unavailable or corrupt */ }
  return { isLoggedIn: false, user: null, token: null, mustChangePw: false, rememberMe: false };
};

const _initial = _readPersisted();

interface AuthState {
  isLoggedIn:   boolean;
  user:         User | null;
  token:        string | null;
  mustChangePw: boolean;
  rememberMe:   boolean;
  login:        (user: User, token: string, mustChangePw?: boolean, rememberMe?: boolean) => void;
  logout:       () => void;
  setMustChangePw: (v: boolean) => void;
  can:          (permission: string) => boolean;
  refreshPermissions: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isLoggedIn:   _initial.isLoggedIn,
      user:         _initial.user,
      token:        _initial.token,
      mustChangePw: _initial.mustChangePw,
      rememberMe:   _initial.rememberMe,

      login(user, token, mustChangePw = false, rememberMe = false) {
        sessionStorage.setItem("mis_token", token);
        // Record login time so the 401 interceptor can ignore transient errors
        // that fire in the first few seconds after login (e.g. refreshPermissions
        // racing with the session INSERT completing on the backend).
        sessionStorage.setItem("mis_login_at", String(Date.now()));
        if (rememberMe) {
          // Persist to localStorage so new tabs / browser restarts restore the session.
          // (Zustand's persist middleware writes this automatically via partialize.)
          sessionStorage.removeItem(_SESSION_KEY);
        } else {
          // Store full session in sessionStorage so page refresh doesn't log the user out.
          // sessionStorage is tab-scoped — closing the tab clears it automatically.
          sessionStorage.setItem(_SESSION_KEY, JSON.stringify({ user, token, mustChangePw }));
          localStorage.removeItem("mis-auth");
        }
        set({ isLoggedIn: true, user, token, mustChangePw, rememberMe });
      },

      logout() {
        sessionStorage.removeItem("mis_token");
        sessionStorage.removeItem(_SESSION_KEY);
        localStorage.removeItem("mis-auth");
        set({ isLoggedIn: false, user: null, token: null, mustChangePw: false, rememberMe: false });
      },

      setMustChangePw(v: boolean) {
        set({ mustChangePw: v });
      },

      can(permission: string) {
        const user = get().user;
        if (!user) return false;
        if (user.role === "superadmin") return true;
        if (user.permissions.includes("*")) return true;
        return user.permissions.includes(permission);
      },

      async refreshPermissions() {
        const { token, isLoggedIn } = get();
        if (!isLoggedIn || !token) return;
        try {
          const { default: api } = await import("@/api/client");
          const res = await api.get<User & { must_change_pw: boolean }>("/auth/me");
          const fresh = res.data;
          set((s) => ({
            user: s.user ? { ...s.user, permissions: fresh.permissions } : s.user,
            mustChangePw: fresh.must_change_pw,
          }));
        } catch (err: unknown) {
          // Only force-logout on 401 (token genuinely invalid).
          // Network errors or 5xx on startup must NOT log the user out.
          const status = (err as { response?: { status?: number } })?.response?.status;
          if (status === 401) get().logout();
        }
      },
    }),
    {
      name: "mis-auth",
      // Only persist the full session when the user opted in via "Remember me".
      // When rememberMe is false we store nothing useful so the next browser
      // open finds an empty / token-less record and shows the login page.
      partialize: (s) => s.rememberMe
        ? { user: s.user, token: s.token, mustChangePw: s.mustChangePw, rememberMe: true }
        : { rememberMe: false },
      // We already pre-read localStorage synchronously via _readPersisted() above,
      // so skip Zustand's own async hydration pass which would cause a second render.
      skipHydration: true,
    }
  )
);
