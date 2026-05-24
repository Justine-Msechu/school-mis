import api from "./client";

export interface StudentPromotionStatus {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  promoted: number;
  promoted_to_class_id: number | null;
}

export interface AcademicYear {
  id: number;
  label: string;
  is_current: number;
}

export const getClassStatus = (class_id: number, academic_year_id: number) =>
  api.get<StudentPromotionStatus[]>("/promotion/class-status", { params: { class_id, academic_year_id } }).then((r) => r.data);

export const promoteBatch = (body: { class_id: number; academic_year_id: number; to_class_id: number; student_ids: number[] }) =>
  api.post("/promotion/promote", body).then((r) => r.data);

export const getPromotionHistory = (student_id?: number) =>
  api.get("/promotion/history", { params: { student_id } }).then((r) => r.data);

export const getAcademicYears = () =>
  api.get<AcademicYear[]>("/promotion/academic-years").then((r) => r.data);
