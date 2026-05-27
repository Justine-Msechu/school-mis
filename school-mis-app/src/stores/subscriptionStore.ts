import { create } from "zustand";

interface SubscriptionState {
  plan:     string;   // "trial" | "basic" | "standard" | "premium" | "none"
  status:   string;   // "trial" | "active" | "pending" | "expired" | "inactive"
  isActive: boolean;
  needsPlanSelection: boolean;
  fetch: () => Promise<void>;
}

export const useSubscriptionStore = create<SubscriptionState>()((set) => ({
  plan:               "trial",
  status:             "trial",
  isActive:           true,
  needsPlanSelection: false,

  async fetch() {
    try {
      const { default: api } = await import("@/api/client");
      const res = await api.get<{ plan_name: string; status: string; is_active: boolean }>("/subscriptions/status");
      const { plan_name, status, is_active } = res.data;
      set({
        plan:               plan_name ?? "trial",
        status:             status ?? "trial",
        isActive:           is_active ?? true,
        needsPlanSelection: status === "pending",
      });
    } catch {
      // silently ignore
    }
  },
}));
