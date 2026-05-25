import api from "./client";

export interface Enrollment {
  id: number;
  student_id: number;
  class_id: number;
  academic_year_id: number;
  status: "active" | "transferred" | "graduated" | "withdrawn" | "archived";
  enrollment_date: string;
  exit_date: string | null;
  transfer_reason: string | null;
  student_name?: string;
  class_name?: string;
  year_name?: string;
  admission_no?: string;
}

export interface HeadcountRow {
  class_id: number;
  class_name: string;
  enrolled: number;
  transferred: number;
  withdrawn: number;
}

export const enrollStudent = (data: { student_id: number; class_id: number; academic_year_id: number }) =>
  api.post("/enrollments", data).then((r) => r.data);

export const transferStudent = (enrollment_id: number, new_class_id: number, reason: string) =>
  api.post(`/enrollments/${enrollment_id}/transfer`, { new_class_id, reason }).then((r) => r.data);

export const withdrawStudent = (enrollment_id: number, reason: string) =>
  api.post(`/enrollments/${enrollment_id}/withdraw`, { reason }).then((r) => r.data);

export const getClassRoll = (class_id: number, academic_year_id: number, status = "active"): Promise<Enrollment[]> =>
  api.get(`/enrollments/class/${class_id}`, { params: { academic_year_id, status } }).then((r) => r.data);

export const getStudentHistory = (student_id: number): Promise<Enrollment[]> =>
  api.get(`/enrollments/student/${student_id}`).then((r) => r.data);

export const getCurrentEnrollment = (student_id: number): Promise<Enrollment | null> =>
  api.get(`/enrollments/student/${student_id}/current`).then((r) => r.data).catch(() => null);

export const getHeadcount = (academic_year_id?: number): Promise<HeadcountRow[]> =>
  api.get("/enrollments/headcount", { params: { academic_year_id } }).then((r) => r.data);
