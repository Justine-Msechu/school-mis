import { create } from "zustand";

interface SubscriptionState {
  plan: string;          // "basic" | "standard" | "premium" | "trial"
  isActive: boolean;
  fetch: () => Promise<void>;
}

export const useSubscriptionStore = create<SubscriptionState>()((set) => ({
  plan:     "trial",
  isActive: true,

  async fetch() {
    try {
      const { default: api } = await import("@/api/client");
      const res = await api.get<{ plan_name: string; is_active: boolean }>("/subscriptions/status");
      set({ plan: res.data.plan_name ?? "trial", isActive: res.data.is_active ?? true });
    } catch {
      // silently ignore — restrictions just won't show in sidebar
    }
  },
}));
