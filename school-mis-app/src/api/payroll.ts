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
}

export interface RunItems {
  run: PayrollRun;
  items: PayrollItem[];
}

export const getPayrollStaff = (search = "") =>
  api.get<StaffSalary[]>("/payroll/staff", { params: { search } }).then((r) => r.data);

export const setSalaryConfig = (teacherId: number, body: SalaryConfigPayload) =>
  api.put<StaffSalary>(`/payroll/staff/${teacherId}/salary`, body).then((r) => r.data);

export const getPayrollRuns = () =>
  api.get<PayrollRun[]>("/payroll/runs").then((r) => r.data);

export const createPayrollRun = (month: number, year: number) =>
  api.post<PayrollRun>("/payroll/runs", { month, year }).then((r) => r.data);

export const computeRun = (runId: number) =>
  api.post<{ computed: number }>(`/payroll/runs/${runId}/compute`).then((r) => r.data);

export const finalizeRun = (runId: number) =>
  api.post(`/payroll/runs/${runId}/finalize`).then((r) => r.data);

export const approveRun = (runId: number) =>
  api.post(`/payroll/runs/${runId}/approve`).then((r) => r.data);

export const getRunItems = (runId: number) =>
  api.get<RunItems>(`/payroll/runs/${runId}/items`).then((r) => r.data);
