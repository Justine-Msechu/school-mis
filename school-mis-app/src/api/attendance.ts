import api from "./client";

export interface AttendanceRow {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  status: string;
  remarks: string;
}

export interface AttendanceSheet {
  date: string;
  class_id: number;
  rows: AttendanceRow[];
}

export interface AttendanceSummaryDay {
  date: string;
  present: number;
  absent: number;
  late: number;
  total: number;
}

export const getAttendanceSheet = (class_id: number, date?: string) =>
  api.get<AttendanceSheet>("/attendance/sheet", { params: { class_id, date } }).then((r) => r.data);

export const saveAttendance = (class_id: number, date: string, entries: { student_id: number; status: string; remarks?: string }[]) =>
  api.post("/attendance/save", { class_id, date, entries }).then((r) => r.data);

export const getAttendanceSummary = (class_id?: number | null, days = 30) =>
  api.get<AttendanceSummaryDay[]>("/attendance/summary", { params: { class_id, days } }).then((r) => r.data);

export const getLeaveRequests = (status = "pending") =>
  api.get("/attendance/leave-requests", { params: { status } }).then((r) => r.data);

export const reviewLeaveRequest = (lr_id: number, status: string, note = "") =>
  api.post(`/attendance/leave-requests/${lr_id}/review`, { status, note }).then((r) => r.data);
