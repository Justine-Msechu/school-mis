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

export const recordPayment = (body: { student_id: number; amount: number; payment_date: string; method?: string; reference?: string; notes?: string }) =>
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
