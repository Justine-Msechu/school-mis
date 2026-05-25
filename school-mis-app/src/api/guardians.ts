import api from "./client";

export interface Guardian {
  id: number;
  full_name: string;
  relationship: string;
  gender: string | null;
  phone: string | null;
  alt_phone: string | null;
  email: string | null;
  id_number: string | null;
  occupation: string | null;
  address: string | null;
  is_emergency_contact: number;
  is_pickup_authorized: number;
  is_billing_contact: number;
  communication_pref: string;
  notes: string | null;
  student_count?: number;
  students?: Array<{ id: number; full_name: string; admission_no: string; is_primary: number }>;
}

export const listGuardians = (search = ""): Promise<Guardian[]> =>
  api.get("/guardians", { params: { search } }).then((r) => r.data);

export const getGuardian = (id: number): Promise<Guardian> =>
  api.get(`/guardians/${id}`).then((r) => r.data);

export const createGuardian = (data: Partial<Guardian>): Promise<Guardian> =>
  api.post("/guardians", data).then((r) => r.data);

export const updateGuardian = (id: number, data: Partial<Guardian>): Promise<Guardian> =>
  api.patch(`/guardians/${id}`, data).then((r) => r.data);

export const deleteGuardian = (id: number) =>
  api.delete(`/guardians/${id}`).then((r) => r.data);

export const linkStudent = (guardian_id: number, student_id: number, is_primary = false) =>
  api.post(`/guardians/${guardian_id}/students`, { student_id, is_primary }).then((r) => r.data);

export const unlinkStudent = (guardian_id: number, student_id: number) =>
  api.delete(`/guardians/${guardian_id}/students/${student_id}`).then((r) => r.data);

export const getStudentGuardians = (student_id: number): Promise<Guardian[]> =>
  api.get(`/guardians/by-student/${student_id}`).then((r) => r.data);
