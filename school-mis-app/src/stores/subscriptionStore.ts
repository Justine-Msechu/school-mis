import { create } from "zustand";

interface SubscriptionState {
  plan:               string;   // "trial" | "basic" | "standard" | "premium" | "none"
  status:             string;   // "trial" | "active" | "trialing" | "expired" | "inactive" | "pending"
  isActive:           boolean;
  warning:            string | null;
  needsPlanSelection: boolean;
  fetch: () => Promise<void>;
}

export const useSubscriptionStore = create<SubscriptionState>()((set) => ({
  plan:               "trial",
  status:             "trial",
  isActive:           true,
  warning:            null,
  needsPlanSelection: false,

  async fetch() {
    try {
      const { default: api } = await import("@/api/client");
      const res = await api.get<{
        plan_name: string;
        status:    string;
        is_active: boolean;
        warning?:  string | null;
      }>("/subscriptions/status");
      const { plan_name, status, is_active, warning } = res.data;
      set({
        plan:               plan_name ?? "trial",
        status:             status    ?? "trial",
        isActive:           is_active ?? true,
        warning:            warning   ?? null,
        needsPlanSelection: status === "pending" && !is_active,
      });
    } catch {
      // silently ignore — don't lock out users due to a failed status check
    }
  },
}));
