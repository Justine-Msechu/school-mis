import api from "./client";

// ── Student portal ────────────────────────────────────────────────────────────

export interface StudentProfile {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  date_of_birth: string | null;
  gender: string | null;
  photo_path: string | null;
  class_name: string | null;
  year_label: string | null;
}

export interface PortalGrade {
  exam_name: string;
  term: string;
  year_label: string | null;
  subject_name: string;
  subject_code: string;
  score: number;
  max_score: number;
  grade_letter: string | null;
  remarks: string | null;
}

export interface AttendanceRecord {
  date: string;
  status: "present" | "absent" | "late";
  notes: string | null;
}

export interface AttendanceSummary {
  total: number;
  present: number;
  absent: number;
  late: number;
  rate: number;
}

export interface AttendanceResponse {
  records: AttendanceRecord[];
  summary: AttendanceSummary;
}

export interface TimetableSlot {
  day_of_week: number;
  room: string | null;
  period_name: string;
  start_time: string;
  end_time: string;
  is_break: boolean;
  subject_name: string | null;
  subject_code: string | null;
  teacher_name: string | null;
}

export interface TimetablePeriod {
  id: number;
  name: string;
  period_no: number;
  start_time: string;
  end_time: string;
  is_break: boolean;
  sort_order: number;
}

export interface TimetableResponse {
  slots: TimetableSlot[];
  periods: TimetablePeriod[];
}

export const getStudentProfile   = ()           => api.get<StudentProfile>("/portal/student/profile").then(r => r.data);
export const getStudentGrades    = ()           => api.get<PortalGrade[]>("/portal/student/grades").then(r => r.data);
export const getStudentAttendance = (days = 60) => api.get<AttendanceResponse>("/portal/student/attendance", { params: { days } }).then(r => r.data);
export const getStudentTimetable = ()           => api.get<TimetableResponse>("/portal/student/timetable").then(r => r.data);

// ── Parent portal ─────────────────────────────────────────────────────────────

export interface PortalChild {
  id: number;
  name: string;
  admission_no: string;
  photo_path: string | null;
  class_name: string | null;
  relation: string;
}

export interface ChildFeeSummary {
  bills: {
    fee_name: string;
    year_label: string | null;
    term: string;
    amount_due: number;
    amount_paid: number;
    balance: number;
  }[];
  recent_payments: {
    amount: number;
    payment_date: string;
    payment_method: string;
    reference_no: string | null;
  }[];
  total_due: number;
  total_paid: number;
  balance: number;
}

export interface LeaveRequest {
  id: number;
  date_from: string;
  date_to: string;
  reason: string;
  status: "pending" | "approved" | "rejected";
  review_note: string | null;
  reviewed_at: string | null;
  reviewed_by_name: string | null;
}

export const getParentChildren         = ()                                              => api.get<PortalChild[]>("/portal/parent/children").then(r => r.data);
export const getChildGrades            = (studentId: number)                             => api.get<PortalGrade[]>(`/portal/parent/children/${studentId}/grades`).then(r => r.data);
export const getChildFees              = (studentId: number)                             => api.get<ChildFeeSummary>(`/portal/parent/children/${studentId}/fees`).then(r => r.data);
export const getChildAttendance        = (studentId: number, days = 60)                  => api.get<AttendanceResponse>(`/portal/parent/children/${studentId}/attendance`, { params: { days } }).then(r => r.data);
export const getChildLeave             = (studentId: number)                             => api.get<LeaveRequest[]>(`/portal/parent/children/${studentId}/leave`).then(r => r.data);
export const submitLeave               = (studentId: number, body: { date_from: string; date_to: string; reason: string }) => api.post(`/portal/parent/children/${studentId}/leave`, body).then(r => r.data);

// ── Admin account management ──────────────────────────────────────────────────

export interface PortalAccounts {
  student_accounts: {
    user_id: number;
    username: string;
    full_name: string;
    student_id: number;
    student_name: string;
    admission_no: string;
  }[];
  parent_accounts: {
    id: number;
    user_id: number;
    username: string;
    full_name: string;
    student_id: number;
    student_name: string;
    admission_no: string;
    relation: string;
  }[];
}

export const listPortalAccounts   = ()                                         => api.get<PortalAccounts>("/portal/admin/accounts").then(r => r.data);
export const createStudentAccount = (body: { student_id: number; username: string; password: string; full_name: string }) => api.post("/portal/admin/accounts/student", body).then(r => r.data);
export const createParentAccount  = (body: { student_id: number; username: string; password: string; full_name: string; relation: string }) => api.post("/portal/admin/accounts/parent", body).then(r => r.data);
export const deletePortalAccount  = (userId: number)                           => api.delete(`/portal/admin/accounts/${userId}`).then(r => r.data);
