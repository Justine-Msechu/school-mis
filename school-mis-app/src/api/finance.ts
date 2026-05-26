import api from "./client";

export interface FeeStructure {
  id: number;
  fee_type_id: number;
  fee_type_name: string;
  amount: number;
  term: number | null;
  year_label: string;
  academic_year_id: number;
  class_id: number | null;
  class_name: string | null;
  student_id: number | null;
  student_name: string | null;
  student_admission_no: string | null;
  student_type: string | null;
  due_date: string | null;
}

export interface WaiverRecord {
  id: number;
  student_id: number;
  bill_id: number | null;
  waiver_type: string;
  discount_percent: number;
  reason: string | null;
  created_at: string;
  approved_by_name: string | null;
  fee_type_name: string | null;
}

export interface StudentBill {
  student_id: number;
  bills: { id: number; amount_due: number; amount_paid: number; discount_amount: number; fee_type_name: string; due_date: string; status: string }[];
  payments: { id: number; amount_paid: number; payment_date: string; method: string; reference: string }[];
  waivers: WaiverRecord[];
  total_billed: number;
  total_discount: number;
  total_paid: number;
  balance: number;
}

export const getWaivers = (student_id?: number) =>
  api.get<WaiverRecord[]>("/finance/waivers", { params: { student_id } }).then((r) => r.data);

export const createWaiver = (body: { student_id: number; bill_id?: number | null; academic_year_id?: number | null; waiver_type: string; discount_percent: number; reason?: string }) =>
  api.post("/finance/waivers", body).then((r) => r.data);

export const deleteWaiver = (id: number) =>
  api.delete(`/finance/waivers/${id}`).then((r) => r.data);

// Carry-forward
export const carryForward = (body: { from_year_id: number; to_year_id: number; term?: number | null }) =>
  api.post<{ created: number; skipped: number }>("/finance/carry-forward", body).then((r) => r.data);

// Locked periods
export interface LockedPeriod { id: number; academic_year_id: number; year_label: string; term: number | null; locked_by_name: string; locked_at: string; note: string | null }
export const getLockedPeriods = () => api.get<LockedPeriod[]>("/finance/locked-periods").then((r) => r.data);
export const lockPeriod = (body: { academic_year_id: number; term?: number | null; note?: string }) => api.post("/finance/lock-period", body).then((r) => r.data);
export const unlockPeriod = (id: number) => api.delete(`/finance/locked-periods/${id}`).then((r) => r.data);

// Late fee rules
export interface LateFeeRule { id: number; fee_type_id: number | null; fee_type_name: string | null; days_after_due: number; charge_type: string; charge_amount: number; max_charge: number | null; is_active: number }
export const getLateFeeRules = () => api.get<LateFeeRule[]>("/finance/late-fee-rules").then((r) => r.data);
export const createLateFeeRule = (body: { fee_type_id?: number | null; days_after_due: number; charge_type: string; charge_amount: number; max_charge?: number | null }) => api.post("/finance/late-fee-rules", body).then((r) => r.data);
export const deleteLateFeeRule = (id: number) => api.delete(`/finance/late-fee-rules/${id}`).then((r) => r.data);
export const applyLateFees = (academic_year_id?: number, dry_run = false) => api.post<{ applied: number; dry_run: boolean }>("/finance/apply-late-fees", null, { params: { academic_year_id, dry_run } }).then((r) => r.data);

// Installments
export interface InstallmentRow { id: number; bill_id: number; installment_no: number; due_date: string; amount_due: number; amount_paid: number; status: string; fee_type_name: string }
export const getInstallments = (params: { student_id?: number; bill_id?: number }) => api.get<InstallmentRow[]>("/finance/installments", { params }).then((r) => r.data);
export const createInstallmentPlan = (body: { bill_id: number; installments: { due_date: string; amount: number }[] }) => api.post("/finance/installments", body).then((r) => r.data);

// Pending approvals
export interface PendingApproval { id: number; action_type: string; description: string; requester_name: string; created_at: string; status: string }
export const getPendingApprovals = () => api.get<PendingApproval[]>("/finance/pending-approvals").then((r) => r.data);
export const approveAction = (id: number, note?: string) => api.post(`/finance/pending-approvals/${id}/approve`, { note }).then((r) => r.data);
export const rejectAction = (id: number, note?: string) => api.post(`/finance/pending-approvals/${id}/reject`, { note }).then((r) => r.data);
export const requestReversal = (payment_id: number, reason: string) => api.post("/finance/request-reversal", null, { params: { payment_id, reason } }).then((r) => r.data);

// Mobile money
export const confirmMobilePayment = (payment_id: number) => api.post(`/finance/payment/${payment_id}/confirm`).then((r) => r.data);

// Parent balance
export interface ChildBalance { student_id: number; student_name: string; admission_no: string; relation: string; total_billed: number; total_discount: number; total_paid: number; balance: number; bills: any[] }
export const getParentBalance = (academic_year_id?: number) => api.get<ChildBalance[]>("/finance/parent-balance", { params: { academic_year_id } }).then((r) => r.data);

export interface Payment {
  id: number;
  student_id: number;
  student_name: string;
  admission_no: string;
  amount: number;
  payment_date: string;
  method: string;
  reference: string;
}

export interface FinanceSummary {
  total_billed: number;
  total_collected: number;
  balance: number;
  recent_payments: Payment[];
}

export const getFeeStructures = () =>
  api.get<FeeStructure[]>("/finance/fee-structures").then((r) => r.data);

export const getStudentBill = (student_id?: number, admission_no?: string) =>
  api.get<StudentBill>("/finance/student-bill", { params: { student_id, admission_no } }).then((r) => r.data);

export const getPayments = (limit = 50) =>
  api.get<Payment[]>("/finance/payments", { params: { limit } }).then((r) => r.data);

export const recordPayment = (body: { student_id: number; amount: number; payment_date: string; method?: string; reference_no?: string; notes?: string }) =>
  api.post("/finance/payment", body).then((r) => r.data);

export const getFinanceSummary = () =>
  api.get<FinanceSummary>("/finance/summary").then((r) => r.data);

export interface DebtorRow {
  student_id: number;
  student_name: string;
  admission_no: string;
  class_name: string | null;
  total_billed: number;
  total_paid: number;
  balance: number;
}

export const getOutstandingDebtors = (params?: { academic_year_id?: number; class_id?: number }) =>
  api.get<DebtorRow[]>("/finance/outstanding", { params }).then((r) => r.data);
