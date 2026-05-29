import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/api/auth";

// Read persisted auth synchronously before React's first render.
// Only restores the session if the user explicitly chose "Remember me".
const _readPersisted = (): { isLoggedIn: boolean; user: User | null; token: string | null; mustChangePw: boolean; rememberMe: boolean } => {
  try {
    const raw = localStorage.getItem("mis-auth");
    if (!raw) return { isLoggedIn: false, user: null, token: null, mustChangePw: false, rememberMe: false };
    const parsed = JSON.parse(raw) as { state?: { user?: User; token?: string; mustChangePw?: boolean; rememberMe?: boolean } };
    const { user, token, mustChangePw, rememberMe } = parsed?.state ?? {};
    // Only restore if rememberMe was true AND we have a valid token
    if (rememberMe && token && user) {
      sessionStorage.setItem("mis_token", token);
      return { isLoggedIn: true, user, token, mustChangePw: mustChangePw ?? false, rememberMe: true };
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
        set({ isLoggedIn: true, user, token, mustChangePw, rememberMe });
        // When "remember me" is off, wipe any previously persisted session
        // so closing the browser doesn't restore this new session either.
        if (!rememberMe) {
          localStorage.removeItem("mis-auth");
        }
      },

      logout() {
        sessionStorage.removeItem("mis_token");
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
