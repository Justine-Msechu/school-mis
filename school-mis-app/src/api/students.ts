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
  parent_name: string | null;
  parent_phone: string | null;
  parent_email: string | null;
  address: string | null;
  notes: string | null;
  student_category: string;
  student_type?: string;
  sponsorship_type?: string;
  sponsor_ngo_id?: number | null;
  sponsor_name?: string | null;
  sponsor_phone?: string | null;
  sponsor_relationship?: string | null;
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

export async function getNextAdmissionNo(): Promise<string> {
  const { data } = await api.get("/students/next-admission-no");
  return data.admission_no;
}

export async function createStudent(payload: Record<string, unknown>): Promise<Student> {
  const { data } = await api.post("/students", payload);
  return data;
}

export async function updateStudent(id: number, payload: Record<string, unknown>): Promise<Student> {
  const { data } = await api.put(`/students/${id}`, payload);
  return data;
}

export async function deactivateStudent(id: number): Promise<void> {
  await api.delete(`/students/${id}`);
}
