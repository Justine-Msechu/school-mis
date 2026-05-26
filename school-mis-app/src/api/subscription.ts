import api from "./client";

export interface SubscriptionInfo {
  plan:        string;
  plan_label:  string;
  plan_color:  string;
  status:      string;
  trial_ends:  string | null;
  days_left:   number | null;
  is_active:   boolean;
  max_users:   number;
  warning:     string | null;
  school_name: string;
}

export const getSubscriptionStatus = () =>
  api.get<SubscriptionInfo>("/subscription/status").then((r) => r.data);

export const activateSubscription = (plan: string, school_id?: number, trial_ends?: string) =>
  api.post("/subscription/activate", { plan, school_id, trial_ends }).then((r) => r.data);
