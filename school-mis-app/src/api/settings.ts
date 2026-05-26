import api from "./client";

export interface AppUser {
  id: number;
  username: string;
  full_name: string;
  role: string;
  role_label: string;
  is_active: number;
  created_at: string;
}

export interface Role {
  key: string;
  label: string;
  color: string;
}

export const getConfig = () =>
  api.get<Record<string, string>>("/settings/config").then((r) => r.data);

export const setConfig = (key: string, value: string) =>
  api.post("/settings/config", { key, value }).then((r) => r.data);

export const getUsers = () =>
  api.get<AppUser[]>("/settings/users").then((r) => r.data);

export const getRoles = () =>
  api.get<Role[]>("/settings/roles").then((r) => r.data);

export const createUser = (body: { username: string; full_name: string; role: string; password: string }) =>
  api.post<AppUser>("/settings/users", body).then((r) => r.data);

export const updateUser = (id: number, body: { full_name: string; role: string; password?: string }) =>
  api.put<AppUser>(`/settings/users/${id}`, body).then((r) => r.data);

export const toggleUserActive = (id: number) =>
  api.post(`/settings/users/${id}/toggle-active`).then((r) => r.data);

export interface AcademicYear {
  id: number;
  label: string;
  start_date: string;
  end_date: string;
  is_current: number;
}

export const getAcademicYears = () =>
  api.get<AcademicYear[]>("/settings/academic-years").then((r) => r.data);

export const createAcademicYear = (body: { label: string; start_date: string; end_date: string; is_current?: boolean }) =>
  api.post<AcademicYear>("/settings/academic-years", body).then((r) => r.data);

export const setCurrentYear = (id: number) =>
  api.put(`/settings/academic-years/${id}/set-current`).then((r) => r.data);

export interface FeeType {
  id: number;
  name: string;
  description: string;
}

export interface FeeStructure {
  id: number;
  fee_type_id: number;
  fee_type_name: string;
  academic_year_id: number;
  year_label: string;
  amount: number;
  due_date: string;
  term: number | null;
  grade_level: number | null;
  grade_name: string | null;
  class_id: number | null;
  class_name: string | null;
  student_id: number | null;
  student_name: string | null;
  student_admission_no: string | null;
  student_type: string | null;
}

export const getFeeTypes = () =>
  api.get<FeeType[]>("/settings/fee-types").then((r) => r.data);

export const createFeeType = (body: { name: string; description?: string }) =>
  api.post<FeeType>("/settings/fee-types", body).then((r) => r.data);

export const getFeeStructures = () =>
  api.get<FeeStructure[]>("/settings/fee-structures").then((r) => r.data);

export const createFeeStructure = (body: {
  fee_type_id: number;
  academic_year_id: number;
  amount: number;
  due_date?: string;
  term?: number;
  grade_level?: number | null;
  class_id?: number | null;
  student_id?: number | null;
  student_type?: string | null;
}) => api.post<FeeStructure>("/settings/fee-structures", body).then((r) => r.data);
