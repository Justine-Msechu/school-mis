import api from "./client";

export interface Student {
  id: number;
  first_name: string;
  last_name: string;
  admission_no: string;
  class_id: number | null;
  class_name: string | null;
  gender: string;
  date_of_birth: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  is_active: boolean;
}

export interface StudentFilters {
  search?: string;
  class_id?: number;
  is_active?: boolean;
  page?: number;
  per_page?: number;
}

export interface StudentList {
  items: Student[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export async function getStudents(filters: StudentFilters = {}): Promise<StudentList> {
  const params = new URLSearchParams();
  if (filters.search)   params.set("search", filters.search);
  if (filters.class_id) params.set("class_id", String(filters.class_id));
  if (filters.is_active !== undefined) params.set("is_active", String(filters.is_active));
  params.set("page", String(filters.page ?? 1));
  params.set("per_page", String(filters.per_page ?? 30));
  const { data } = await api.get(`/students?${params}`);
  return data;
}

export async function createStudent(payload: Partial<Student>): Promise<Student> {
  const { data } = await api.post("/students", payload);
  return data;
}

export async function updateStudent(id: number, payload: Partial<Student>): Promise<Student> {
  const { data } = await api.put(`/students/${id}`, payload);
  return data;
}

export async function deactivateStudent(id: number): Promise<void> {
  await api.delete(`/students/${id}`);
}
