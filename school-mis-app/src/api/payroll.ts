import api from "./client";

export interface StaffSalary {
  id: number;
  first_name: string;
  last_name: string;
  employee_no: string;
  subject_specialization: string;
  basic_salary: number | null;
  housing_allow: number | null;
  transport_allow: number | null;
  other_allow: number | null;
  loan_deduction: number | null;
  loan_board: number | null;
  notes: string | null;
}

export interface SalaryConfigPayload {
  basic_salary: number;
  housing_allow: number;
  transport_allow: number;
  other_allow: number;
  loan_deduction: number;
  loan_board: boolean;
  notes: string;
}

export interface PayrollRun {
  id: number;
  month: number;
  year: number;
  label: string;
  status: "draft" | "finalized" | "approved";
  created_at: string;
  employee_count: number;
  total_net: number | null;
  total_gross: number | null;
}

export interface PayrollItem {
  id: number;
  run_id: number;
  teacher_id: number;
  first_name: string;
  last_name: string;
  employee_no: string;
  subject_specialization: string;
  basic_salary: number;
  housing_allow: number;
  transport_allow: number;
  other_allow: number;
  gross_pay: number;
  nssf_employee: number;
  nssf_employer: number;
  paye: number;
  loan_deduction: number;
  loan_board: number;
  total_deductions: number;
  net_pay: number;
  prorate_pct: number;
}

export interface RunItems {
  run: PayrollRun;
  items: PayrollItem[];
}

export interface YTDRow {
  teacher_id: number;
  first_name: string;
  last_name: string;
  employee_no: string;
  months_paid: number;
  ytd_gross: number;
  ytd_nssf_employee: number;
  ytd_nssf_employer: number;
  ytd_paye: number;
  ytd_loan: number;
  ytd_loan_board: number;
  ytd_deductions: number;
  ytd_net: number;
}

export interface HistoryItem extends PayrollItem {
  run_label: string;
  run_status: string;
  month: number;
  year: number;
}

export const getPayrollStaff = (search = "") =>
  api.get<StaffSalary[]>("/payroll/staff", { params: { search } }).then((r) => r.data);

export const setSalaryConfig = (teacherId: number, body: SalaryConfigPayload) =>
  api.put<StaffSalary>(`/payroll/staff/${teacherId}/salary`, body).then((r) => r.data);

export const getStaffHistory = (teacherId: number) =>
  api.get<HistoryItem[]>(`/payroll/staff/${teacherId}/history`).then((r) => r.data);

export const getPayrollRuns = () =>
  api.get<PayrollRun[]>("/payroll/runs").then((r) => r.data);

export const createPayrollRun = (month: number, year: number) =>
  api.post<PayrollRun>("/payroll/runs", { month, year }).then((r) => r.data);

export const deletePayrollRun = (runId: number) =>
  api.delete(`/payroll/runs/${runId}`).then((r) => r.data);

export const reopenRun = (runId: number) =>
  api.post(`/payroll/runs/${runId}/reopen`).then((r) => r.data);

export const computeRun = (runId: number) =>
  api.post<{ computed: number }>(`/payroll/runs/${runId}/compute`).then((r) => r.data);

export const finalizeRun = (runId: number) =>
  api.post(`/payroll/runs/${runId}/finalize`).then((r) => r.data);

export const approveRun = (runId: number) =>
  api.post(`/payroll/runs/${runId}/approve`).then((r) => r.data);

export const updateProrate = (runId: number, teacherId: number, prorate_pct: number) =>
  api.patch<PayrollItem>(`/payroll/runs/${runId}/items/${teacherId}`, { prorate_pct }).then((r) => r.data);

export const getRunItems = (runId: number) =>
  api.get<RunItems>(`/payroll/runs/${runId}/items`).then((r) => r.data);

export const getYTD = (year: number) =>
  api.get<YTDRow[]>("/payroll/ytd", { params: { year } }).then((r) => r.data);
