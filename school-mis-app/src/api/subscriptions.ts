import api from "./client";

export interface Plan {
  id: string;
  name: string;
  display_name: string;
  billing_interval: "monthly" | "yearly";
  price_amount: number;
  currency: string;
  max_users: number;
  max_students: number;
  features: Record<string, boolean>;
  feature_list: string[];
  color: string;
  description: string;
  is_active: boolean;
  sort_order: number;
}

export interface SubscriptionStatus {
  plan_name:           string;
  display_name:        string;
  billing_interval?:   string;
  status:              string;
  is_active:           boolean;
  current_period_end?: string;
  days_left?:          number | null;
  warning?:            string | null;
  grace_active?:       boolean;
  max_users?:          number;
  max_students?:       number;
  providers:           string[];
  color:               string;
}

export interface Invoice {
  id:                  string;
  status:              string;
  amount_due:          number;
  amount_paid:         number;
  currency:            string;
  invoice_number:      string;
  billing_period_start?: string;
  billing_period_end?:   string;
  paid_at?:            string;
  created_at:          string;
}

export interface HistoryEntry {
  id:          string;
  event_type:  string;
  from_status?: string;
  to_status?:   string;
  plan_display?: string;
  triggered_by: string;
  created_at:   string;
  notes?:       string;
}

export const getPlans            = () => api.get<Plan[]>("/subscriptions/plans").then(r => r.data);
export const getProviders        = () => api.get<{providers: string[]}>("/subscriptions/providers").then(r => r.data);
export const getStatus           = () => api.get<SubscriptionStatus>("/subscriptions/status").then(r => r.data);
export const getHistory          = () => api.get<HistoryEntry[]>("/subscriptions/history").then(r => r.data);
export const getInvoices         = (page = 1) => api.get<{total:number;items:Invoice[]}>("/subscriptions/invoices", {params:{page}}).then(r => r.data);

export const createCheckout = (data: {
  plan_name: string; interval: string; provider: string; redirect_url: string;
}) => api.post<{checkout_url: string; tx_ref: string}>("/subscriptions/create-checkout", data).then(r => r.data);

export const verifyPayment    = (tx_ref: string) => api.post("/subscriptions/verify", null, {params:{tx_ref}}).then(r => r.data);

export const manualActivate   = (data: {plan_name: string; interval: string; days?: number}) =>
  api.post("/subscriptions/activate", data).then(r => r.data);

export const requestPlanUpgrade = (data: {plan_name: string; interval: string}) =>
  api.post("/subscriptions/request-upgrade", data).then(r => r.data);

export const cancelSubscription = (reason = "") =>
  api.post("/subscriptions/cancel", {reason}).then(r => r.data);
