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

export interface CounselingRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  session_date: string;
  reason: string;
  notes: string;
  counselor_name?: string;
  follow_up_date: string | null;
  follow_up_done: number;
  created_at: string;
}

export interface VisitRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  visit_date: string;
  address_visited: string;
  findings: string;
  action_taken: string;
  next_visit_date: string | null;
  officer_name?: string;
  created_at: string;
}

export interface DistributionRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  item_type: string;
  quantity: number;
  unit: string;
  distribution_date: string;
  notes: string;
  distributed_by_name?: string;
  created_at: string;
}

export interface DistributionSummary {
  item_type: string;
  count: number;
  total_qty: number;
}

export interface IncidentRecord {
  id: number;
  student_id: number;
  student_name?: string;
  admission_no?: string;
  incident_type: string;
  reported_date: string;
  description: string;
  action_taken: string;
  resolved: number;
  resolved_date: string | null;
  reporter_name?: string;
  created_at: string;
}

// Welfare Records
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

// Counseling
export const getCounseling = (params?: { student_id?: number; limit?: number }) =>
  api.get<CounselingRecord[]>("/welfare/counseling", { params }).then((r) => r.data);

export const addCounseling = (body: {
  student_id: number;
  session_date: string;
  reason: string;
  notes?: string;
  follow_up_date?: string | null;
}) => api.post("/welfare/counseling", body).then((r) => r.data);

export const markFollowUpDone = (id: number) =>
  api.post(`/welfare/counseling/${id}/follow-up-done`).then((r) => r.data);

// Home Visits
export const getVisits = (params?: { student_id?: number; limit?: number }) =>
  api.get<VisitRecord[]>("/welfare/visits", { params }).then((r) => r.data);

export const addVisit = (body: {
  student_id: number;
  visit_date: string;
  address_visited?: string;
  findings: string;
  action_taken?: string;
  next_visit_date?: string | null;
}) => api.post("/welfare/visits", body).then((r) => r.data);

// Distributions
export const getDistributions = (params?: { student_id?: number; item_type?: string; limit?: number }) =>
  api.get<DistributionRecord[]>("/welfare/distributions", { params }).then((r) => r.data);

export const getDistributionSummary = () =>
  api.get<DistributionSummary[]>("/welfare/distributions/summary").then((r) => r.data);

export const addDistribution = (body: {
  student_id: number;
  item_type: string;
  quantity?: number;
  unit?: string;
  distribution_date: string;
  notes?: string;
}) => api.post("/welfare/distributions", body).then((r) => r.data);

// Incidents
export const getIncidents = (params?: { student_id?: number; resolved?: boolean; limit?: number }) =>
  api.get<IncidentRecord[]>("/welfare/incidents", { params }).then((r) => r.data);

export const addIncident = (body: {
  student_id: number;
  incident_type: string;
  reported_date: string;
  description: string;
  action_taken?: string;
}) => api.post("/welfare/incidents", body).then((r) => r.data);

export const resolveIncident = (id: number) =>
  api.post(`/welfare/incidents/${id}/resolve`).then((r) => r.data);
