import api from "./client";

export interface ClassRecord {
  id: number;
  name: string;
  grade_level: number | null;
  capacity: number | null;
  room: string | null;
  teacher_id: number | null;
  teacher_name: string | null;
  student_count: number;
}

export interface ClassStudent {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  gender: string;
}

export const getClassList = () =>
  api.get<ClassRecord[]>("/classes").then((r) => r.data);

export const createClass = (body: { name: string; grade_level?: number | null; capacity?: number | null; room?: string | null; teacher_id?: number | null }) =>
  api.post<ClassRecord>("/classes", body).then((r) => r.data);

export const updateClass = (id: number, body: { name: string; grade_level?: number | null; capacity?: number | null; room?: string | null; teacher_id?: number | null }) =>
  api.put<ClassRecord>(`/classes/${id}`, body).then((r) => r.data);

export const getClassStudents = (class_id: number) =>
  api.get<ClassStudent[]>(`/classes/${class_id}/students`).then((r) => r.data);
