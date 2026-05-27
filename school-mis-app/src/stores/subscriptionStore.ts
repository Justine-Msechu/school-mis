import { create } from "zustand";

interface SubscriptionState {
  plan:               string;
  status:             string;
  isActive:           boolean;
  warning:            string | null;
  daysLeft:           number | null;
  needsPlanSelection: boolean;
  fetch: () => Promise<void>;
}

export const useSubscriptionStore = create<SubscriptionState>()((set) => ({
  plan:               "trial",
  status:             "trial",
  isActive:           true,
  warning:            null,
  daysLeft:           null,
  needsPlanSelection: false,

  async fetch() {
    try {
      const { default: api } = await import("@/api/client");
      const res = await api.get<{
        plan_name:  string;
        status:     string;
        is_active:  boolean;
        warning?:   string | null;
        days_left?: number | null;
      }>("/subscriptions/status");
      const { plan_name, status, is_active, warning, days_left } = res.data;
      set({
        plan:               plan_name ?? "trial",
        status:             status    ?? "trial",
        isActive:           is_active ?? true,
        warning:            warning   ?? null,
        daysLeft:           days_left ?? null,
        needsPlanSelection: status === "pending" && !is_active,
      });
    } catch {
      // silently ignore — don't lock out users due to a failed status check
    }
  },
}));
