import api from "./client";

export interface HealthVisit {
  id: number;
  student_id: number;
  student_name?: string;
  visit_date: string;
  complaint: string;
  diagnosis: string;
  treatment: string;
  prescription: string;
  referred: boolean;
  follow_up: string | null;
}

export const getHealthVisits = (params?: { student_id?: number; date_from?: string; date_to?: string; limit?: number }) =>
  api.get<HealthVisit[]>("/health/visits", { params }).then((r) => r.data);

export const recordHealthVisit = (body: Omit<HealthVisit, "id">) =>
  api.post("/health/visits", body).then((r) => r.data);

export const getHealthVisit = (id: number) =>
  api.get<HealthVisit>(`/health/visits/${id}`).then((r) => r.data);

export const getStudentHealthHistory = (student_id: number) =>
  api.get<HealthVisit[]>(`/health/student/${student_id}/history`).then((r) => r.data);

export const getHealthStats = () =>
  api.get("/health/stats").then((r) => r.data);
