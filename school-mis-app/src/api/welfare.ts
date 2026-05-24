import api from "./client";

export interface WelfareRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  category: string;
  incident_date: string;
  description: string;
  action_taken: string;
  follow_up: string;
  is_verified: number;
}

export const getWelfareRecords = (params?: { student_id?: number; category?: string; verified?: boolean; limit?: number }) =>
  api.get<WelfareRecord[]>("/welfare/records", { params }).then((r) => r.data);

export const createWelfareRecord = (body: { student_id: number; category: string; incident_date: string; description: string; action_taken?: string; follow_up?: string }) =>
  api.post("/welfare/records", body).then((r) => r.data);

export const verifyWelfareRecord = (id: number) =>
  api.post(`/welfare/records/${id}/verify`).then((r) => r.data);

export const getWelfareCategories = () =>
  api.get<string[]>("/welfare/categories").then((r) => r.data);
