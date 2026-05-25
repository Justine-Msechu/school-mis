import api from "./client";

export interface TimetablePeriod {
  id: number;
  name: string;
  period_no: number;
  start_time: string;
  end_time: string;
  is_break: number;
  sort_order: number;
}

export interface TimetableVersion {
  id: number;
  academic_year_id: number;
  term_id: number | null;
  name: string;
  status: "draft" | "active" | "archived";
  effective_from: string | null;
  effective_to: string | null;
  created_at: string;
}

export interface TimetableSlot {
  id: number;
  version_id: number;
  class_id: number;
  subject_id: number;
  teacher_id: number | null;
  period_id: number;
  day_of_week: number;
  room: string | null;
  period_name: string;
  start_time: string;
  end_time: string;
  subject_name: string;
  teacher_name: string | null;
  class_name?: string;
}

export const getPeriods = (): Promise<TimetablePeriod[]> =>
  api.get("/timetable/periods").then((r) => r.data);

export const listVersions = (academic_year_id: number): Promise<TimetableVersion[]> =>
  api.get("/timetable/versions", { params: { academic_year_id } }).then((r) => r.data);

export const createVersion = (data: { academic_year_id: number; name: string; term_id?: number }) =>
  api.post("/timetable/versions", data).then((r) => r.data);

export const activateVersion = (version_id: number) =>
  api.post(`/timetable/versions/${version_id}/activate`).then((r) => r.data);

export const archiveVersion = (version_id: number) =>
  api.post(`/timetable/versions/${version_id}/archive`).then((r) => r.data);

export const getClassTimetable = (version_id: number, class_id: number) =>
  api.get(`/timetable/versions/${version_id}/class/${class_id}`).then((r) => r.data);

export const getTeacherTimetable = (version_id: number, teacher_id: number): Promise<TimetableSlot[]> =>
  api.get(`/timetable/versions/${version_id}/teacher/${teacher_id}`).then((r) => r.data);

export const setSlot = (version_id: number, data: {
  class_id: number; subject_id: number; period_id: number;
  day_of_week: number; teacher_id?: number; room?: string;
}) => api.post(`/timetable/versions/${version_id}/slots`, data).then((r) => r.data);

export const deleteSlot = (slot_id: number) =>
  api.delete(`/timetable/slots/${slot_id}`).then((r) => r.data);

export const getActiveVersion = (academic_year_id: number): Promise<TimetableVersion | null> =>
  api.get("/timetable/active", { params: { academic_year_id } }).then((r) => r.data).catch(() => null);
