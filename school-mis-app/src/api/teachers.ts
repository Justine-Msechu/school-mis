import api from "./client";

export interface Teacher {
  id: number;
  first_name: string;
  last_name: string;
  employee_no: string;
  gender: string;
  phone: string | null;
  email: string | null;
  subject_specialization: string | null;
  qualification: string | null;
  joining_date: string | null;
  is_active: number;
  username?: string;
  role?: string;
  user_active?: number;
}

export interface TeacherPayload {
  first_name: string;
  last_name: string;
  employee_no?: string;
  gender?: string;
  date_of_birth?: string | null;
  phone?: string | null;
  email?: string | null;
  subject_specialization?: string | null;
  qualification?: string | null;
  joining_date?: string | null;
}

export const getTeachers = (search = "") =>
  api.get<Teacher[]>("/teachers", { params: { search } }).then((r) => r.data);

export const getNextEmployeeNo = (): Promise<string> =>
  api.get<{ employee_no: string }>("/teachers/next-employee-no").then((r) => r.data.employee_no);

export const getTeacher = (id: number) =>
  api.get<Teacher>(`/teachers/${id}`).then((r) => r.data);

export const createTeacher = (body: TeacherPayload) =>
  api.post<Teacher>("/teachers", body).then((r) => r.data);

export const updateTeacher = (id: number, body: TeacherPayload) =>
  api.put<Teacher>(`/teachers/${id}`, body).then((r) => r.data);

export const deactivateTeacher = (id: number) =>
  api.delete(`/teachers/${id}`).then((r) => r.data);
