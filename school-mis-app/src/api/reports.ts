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
  class?: string;
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

// ── My Subject types ──────────────────────────────────────────────────────────

export interface SubjectAssignment {
  subject_id:   number;
  subject_name: string;
  class_id:     number;
  class_name:   string;
}

export interface MySubjectInfo {
  assignments: SubjectAssignment[];
  subjects:    { id: number; name: string }[];
  exams:       { id: number; name: string; term: number; status: string }[];
}

export interface SubjectClassAverage {
  subject:        string;
  class:          string;
  avg_pct:        number;
  total_students: number;
  a: number; b: number; c: number; d: number; f: number;
}

export interface SubjectTermRow {
  label:  string;
  term1?: number;
  term2?: number;
  term3?: number;
}

export interface GradeDist {
  name:  string;
  value: number;
}

// ── My Subject API functions ──────────────────────────────────────────────────

export const getMySubjectInfo = () =>
  api.get<MySubjectInfo>("/reports/my-subject/info").then((r) => r.data);

export const getMySubjectAverages = (exam_id?: number | null, subject_id?: number | null) =>
  api.get<SubjectClassAverage[]>("/reports/my-subject/averages", { params: { exam_id, subject_id } }).then((r) => r.data);

export const getMySubjectTermComparison = (subject_id?: number | null) =>
  api.get<SubjectTermRow[]>("/reports/my-subject/term-comparison", { params: { subject_id } }).then((r) => r.data);

export const getMySubjectGradeDist = (exam_id?: number | null, subject_id?: number | null) =>
  api.get<GradeDist[]>("/reports/my-subject/grade-distribution", { params: { exam_id, subject_id } }).then((r) => r.data);

export const getMySubjectMissingMarks = (exam_id?: number | null, subject_id?: number | null) =>
  api.get<MissingMark[]>("/reports/my-subject/missing-marks", { params: { exam_id, subject_id } }).then((r) => r.data);

// ── Accounting reports ────────────────────────────────────────────────────────

export interface FeeByClassRow { class_name: string; billed: number; collected: number; outstanding: number }
export interface MonthlyIncomeRow { month: string; income: number }
export interface ExpenseBreakdownRow { category: string; total: number }
export interface IncomeVsExpenseRow { month: string; income: number; expense: number }
export interface OutstandingRow {
  student_id: number; student_name: string; admission_no: string;
  class_name: string | null; total_billed: number; total_paid: number; balance: number;
}
export interface LedgerEntry {
  id: number; entry_date: string; account_code: string; account_name: string;
  debit_amount: number; credit_amount: number; reference_type: string;
  reference_id: number; description: string; created_at: string;
}

export const getFeeCollectionByClass = (academic_year_id?: number | null, term?: number | null) =>
  api.get<FeeByClassRow[]>("/reports/accounting/fee-collection-by-class", { params: { academic_year_id, term } }).then((r) => r.data);

export const getMonthlyIncome = (year?: number) =>
  api.get<MonthlyIncomeRow[]>("/reports/accounting/monthly-income", { params: { year } }).then((r) => r.data);

export const getExpenseBreakdown = (from_date?: string, to_date?: string) =>
  api.get<ExpenseBreakdownRow[]>("/reports/accounting/expense-breakdown", { params: { from_date, to_date } }).then((r) => r.data);

export const getIncomeVsExpense = (year?: number) =>
  api.get<IncomeVsExpenseRow[]>("/reports/accounting/income-vs-expense", { params: { year } }).then((r) => r.data);

// ── Inventory reports ─────────────────────────────────────────────────────────

export interface InventoryOverview {
  total_items: number;
  low_stock_count: number;
  stock_value: number;
  pending_requests: number;
  today_stock_in: number;
  today_issued: number;
}

export interface InventoryCategoryRow {
  category: string;
  item_count: number;
  total_qty: number;
  total_value: number;
}

export interface InventoryMovementRow {
  month: string;
  received: number;
  issued: number;
  adjusted: number;
}

export interface InventoryTypeRow {
  item_type: string;
  count: number;
  value: number;
}

export interface InventoryLowStockRow {
  id: number;
  name: string;
  main_category: string;
  location: string;
  quantity: number;
  reorder_qty: number;
  unit: string;
  unit_price: number;
  shortage: number;
}

export const getInventoryReportOverview = () =>
  api.get<InventoryOverview>("/reports/inventory/overview").then((r) => r.data);

export const getInventoryByCategory = () =>
  api.get<InventoryCategoryRow[]>("/reports/inventory/by-category").then((r) => r.data);

export const getInventoryMonthlyMovements = (months = 12) =>
  api.get<InventoryMovementRow[]>("/reports/inventory/monthly-movements", { params: { months } }).then((r) => r.data);

export const getInventoryTypeDistribution = () =>
  api.get<InventoryTypeRow[]>("/reports/inventory/type-distribution").then((r) => r.data);

export const getInventoryLowStockDetail = () =>
  api.get<InventoryLowStockRow[]>("/reports/inventory/low-stock-detail").then((r) => r.data);
