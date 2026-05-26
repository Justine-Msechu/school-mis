import api from "./api";

export interface Subject {
  id: number;
  name: string;
  code: string | null;
  grade_level: number | null;
  subject_type: string;
  credit_hours: number;
  is_active: number;
}

export interface SubjectPayload {
  name: string;
  code?: string;
  grade_level?: number | null;
  subject_type?: string;
  credit_hours?: number;
}

export const getSubjects = (includeInactive = false) =>
  api.get<Subject[]>("/subjects", { params: { include_inactive: includeInactive } }).then(r => r.data);

export const createSubject = (data: SubjectPayload) =>
  api.post<Subject>("/subjects", data).then(r => r.data);

export const updateSubject = (id: number, data: SubjectPayload) =>
  api.put<Subject>(`/subjects/${id}`, data).then(r => r.data);

export const toggleSubject = (id: number) =>
  api.patch(`/subjects/${id}/toggle`).then(r => r.data);
