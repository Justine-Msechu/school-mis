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
  students?:       number;
  teachers?:       number;
  books?:          number;
  active_loans?:   number;
  total_expenses?: number;
  total_revenue?:  number;
}

// ── My Class types ────────────────────────────────────────────────────────────

export interface MyClassInfo {
  class: { id: number; name: string; grade_level: number | null };
  student_count: number;
  exams: { id: number; name: string; term: number; status: string }[];
}

export interface SubjectAverage {
  subject: string;
  avg_pct: number;
  total_students: number;
  a: number; b: number; c: number; d: number; f: number;
}

export interface TermComparisonRow {
  subject: string;
  term1?: number;
  term2?: number;
  term3?: number;
}

export interface AttendanceTrendRow {
  week: string;
  week_label: string;
  total: number;
  present: number;
  rate: number;
}

export interface MissingMark {
  student_name: string;
  admission_no: string;
  subject: string;
}

// ── API functions ─────────────────────────────────────────────────────────────

export const getAttendanceSummaryReport = (class_id?: number | null, month?: string) =>
  api.get<AttendanceSummaryRow[]>("/reports/attendance-summary", { params: { class_id, month } }).then((r) => r.data);

export const getFeeCollectionReport = (academic_year_id?: number) =>
  api.get<FeeCollectionRow[]>("/reports/fee-collection", { params: { academic_year_id } }).then((r) => r.data);

export const getGradeSummaryReport = (exam_id?: number) =>
  api.get<GradeSummaryRow[]>("/reports/grade-summary", { params: { exam_id } }).then((r) => r.data);

export const getReportsOverview = () =>
  api.get<ReportsOverview>("/reports/overview").then((r) => r.data);

export const getMyClassInfo = () =>
  api.get<MyClassInfo>("/reports/my-class/info").then((r) => r.data);

export const getMyClassSubjectAverages = (exam_id?: number | null) =>
  api.get<SubjectAverage[]>("/reports/my-class/subject-averages", { params: { exam_id } }).then((r) => r.data);

export const getMyClassTermComparison = () =>
  api.get<TermComparisonRow[]>("/reports/my-class/term-comparison").then((r) => r.data);

export const getMyClassAttendanceTrend = () =>
  api.get<AttendanceTrendRow[]>("/reports/my-class/attendance-trend").then((r) => r.data);

export const getMyClassMissingMarks = (exam_id?: number | null) =>
  api.get<MissingMark[]>("/reports/my-class/missing-marks", { params: { exam_id } }).then((r) => r.data);
