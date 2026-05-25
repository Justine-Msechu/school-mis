import api from "./client";

export interface WelfareRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  category: string;       // orphan | half_orphan | sponsored | vulnerable
  support_type: string;   // full_fees | partial | non_financial
  sponsor_name: string;
  sponsor_org: string;
  notes: string;
  verified: number;
}

export const getWelfareRecords = (params?: { student_id?: number; category?: string; verified?: boolean; limit?: number }) =>
  api.get<WelfareRecord[]>("/welfare/records", { params }).then((r) => r.data);

export const createWelfareRecord = (body: {
  student_id: number;
  category: string;
  support_type?: string;
  sponsor_name?: string;
  sponsor_org?: string;
  notes?: string;
}) => api.post("/welfare/records", body).then((r) => r.data);

export const verifyWelfareRecord = (id: number) =>
  api.post(`/welfare/records/${id}/verify`).then((r) => r.data);

export const getWelfareCategories = () =>
  api.get<string[]>("/welfare/categories").then((r) => r.data);
