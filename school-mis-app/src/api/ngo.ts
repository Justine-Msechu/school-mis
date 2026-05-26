import api from "./client";

export interface Ngo {
  id: number;
  name: string;
  contact_person: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  website: string | null;
  notes: string | null;
  is_active: number;
  created_at: string;
  student_count?: number;
}

export interface Sponsorship {
  sponsorship_id: number;
  student_id: number;
  full_name: string;
  admission_no: string;
  gender: string;
  class_name: string | null;
  ngo_id: number;
  ngo_name: string;
  support_types: string | null;
  fee_amount: number;
  start_date: string | null;
  end_date: string | null;
  sponsorship_notes: string | null;
  is_active: number;
  created_at: string;
}

export interface NgoReportStudent {
  student_id: number;
  full_name: string;
  admission_no: string;
  class_name: string | null;
  support_types: string | null;
  fee_amount: number;
  start_date: string | null;
  attendance_pct: number;
  total_billed: number;
  total_paid: number;
  balance: number;
}

export interface NgoReport {
  ngo: Ngo;
  students: NgoReportStudent[];
  summary: {
    total_beneficiaries: number;
    avg_attendance_pct: number;
    total_billed: number;
    total_paid: number;
    total_balance: number;
  };
}

export interface NgoPayload {
  name: string;
  contact_person?: string;
  phone?: string;
  email?: string;
  address?: string;
  website?: string;
  notes?: string;
}

export interface SponsorshipPayload {
  student_id: number;
  support_types?: string;
  fee_amount?: number;
  start_date?: string;
  end_date?: string;
  notes?: string;
}

export const getNgos = () =>
  api.get<Ngo[]>("/ngos").then((r) => r.data);

export const createNgo = (body: NgoPayload) =>
  api.post<Ngo>("/ngos", body).then((r) => r.data);

export const updateNgo = (id: number, body: NgoPayload) =>
  api.put<Ngo>(`/ngos/${id}`, body).then((r) => r.data);

export const deactivateNgo = (id: number) =>
  api.delete(`/ngos/${id}`).then((r) => r.data);

export const getNgoStudents = (ngoId: number) =>
  api.get<Sponsorship[]>(`/ngos/${ngoId}/students`).then((r) => r.data);

export const getAllSponsorships = (ngoId?: number) =>
  api.get<Sponsorship[]>("/sponsorships", { params: ngoId ? { ngo_id: ngoId } : {} }).then((r) => r.data);

export const addSponsorship = (ngoId: number, body: SponsorshipPayload) =>
  api.post<Sponsorship>(`/ngos/${ngoId}/students`, body).then((r) => r.data);

export const updateSponsorship = (spId: number, body: SponsorshipPayload) =>
  api.put(`/sponsorships/${spId}`, body).then((r) => r.data);

export const removeSponsorship = (spId: number) =>
  api.delete(`/sponsorships/${spId}`).then((r) => r.data);

export const getNgoReport = (ngoId: number) =>
  api.get<NgoReport>(`/ngos/${ngoId}/report`).then((r) => r.data);
