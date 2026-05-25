import api from "./client";

export interface ReportCard {
  id: number;
  student_id: number;
  exam_id: number;
  academic_year_id: number;
  class_id: number;
  class_name_snapshot: string;
  overall_pct: number | null;
  overall_grade: string | null;
  class_rank: number | null;
  is_published: number;
  is_locked: number;
  generated_at: string;
  student_name?: string;
  admission_no?: string;
  subjects?: ReportCardSubject[];
  comments?: ReportCardComment[];
}

export interface ReportCardSubject {
  id: number;
  subject_name: string;
  marks_obtained: number | null;
  total_marks: number | null;
  percentage: number | null;
  grade_label: string | null;
  gpa_points: number | null;
  position: number | null;
  teacher_name: string | null;
}

export interface ReportCardComment {
  id: number;
  comment_type: string;
  comment_text: string;
  author_role: string | null;
  created_at: string;
}

export const generateCards = (exam_id: number, class_id: number) =>
  api.post("/report-cards/generate", { exam_id, class_id }).then((r) => r.data);

export const listCards = (exam_id: number, class_id?: number): Promise<ReportCard[]> =>
  api.get(`/report-cards/exam/${exam_id}`, { params: { class_id } }).then((r) => r.data);

export const getCard = (student_id: number, exam_id: number): Promise<ReportCard> =>
  api.get(`/report-cards/student/${student_id}/exam/${exam_id}`).then((r) => r.data);

export const publishCard = (card_id: number) =>
  api.post(`/report-cards/${card_id}/publish`).then((r) => r.data);

export const lockCard = (card_id: number) =>
  api.post(`/report-cards/${card_id}/lock`).then((r) => r.data);

export const addComment = (card_id: number, comment_type: string, comment_text: string) =>
  api.post(`/report-cards/${card_id}/comments`, { comment_type, comment_text }).then((r) => r.data);

export const listJobs = (exam_id: number) =>
  api.get(`/report-cards/jobs/exam/${exam_id}`).then((r) => r.data);
