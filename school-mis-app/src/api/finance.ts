import api from "./client";

export interface FeeStructure {
  id: number;
  fee_type_id: number;
  fee_type_name: string;
  amount: number;
  year_label: string;
  academic_year_id: number;
}

export interface StudentBill {
  student_id: number;
  bills: { id: number; amount: number; fee_type_name: string; due_date: string }[];
  payments: { id: number; amount: number; payment_date: string; method: string; reference: string }[];
  total_billed: number;
  total_paid: number;
  balance: number;
}

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
