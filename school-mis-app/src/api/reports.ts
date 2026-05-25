import api from "./client";

export interface AttendanceSummaryRow {
  student_name: string;
  admission_no: string;
  total_days: number;
  present: number;
  absent: number;
  rate: number;
}

export interface FeeCollectionRow {
  fee_type: string;
  students: number;
  billed: number;
  collected: number;
}

export interface GradeSummaryRow {
  class_name: string;
  subject_name: string;
  total: number;
  avg_pct: number;
  a_count: number;
  b_count: number;
  c_count: number;
  d_count: number;
  f_count: number;
}

export interface ReportsOverview {
  students?:      number;
  teachers?:      number;
  books?:         number;
  active_loans?:  number;
  total_expenses?: number;
  total_revenue?:  number;
}

export const getAttendanceSummaryReport = (class_id?: number | null, month?: string) =>
  api.get<AttendanceSummaryRow[]>("/reports/attendance-summary", { params: { class_id, month } }).then((r) => r.data);

export const getFeeCollectionReport = (academic_year_id?: number) =>
  api.get<FeeCollectionRow[]>("/reports/fee-collection", { params: { academic_year_id } }).then((r) => r.data);

export const getGradeSummaryReport = (exam_id?: number) =>
  api.get<GradeSummaryRow[]>("/reports/grade-summary", { params: { exam_id } }).then((r) => r.data);

export const getReportsOverview = () =>
  api.get<ReportsOverview>("/reports/overview").then((r) => r.data);
