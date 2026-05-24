import api from "./client";

export interface Exam {
  id: number;
  name: string;
  term: number;
  year_label: string;
  status: string;
}

export interface ClassItem {
  id: number;
  name: string;
}

export interface Subject {
  id: number;
  name: string;
  code: string;
  credit_hours: number;
}

export interface GradeRow {
  student_id: number;
  student_name: string;
  admission_no: string;
  score: number | null;
  max_score: number;
  grade_letter: string | null;
  remarks: string;
  status: string;
  grade_id: number | null;
}

export interface ResultRow {
  student_id: number;
  student_name: string;
  admission_no: string;
  rank: number | string;
  grades: Record<number, { score: number; max_score: number; grade_letter: string; status: string }>;
  total: number;
  max_total: number;
  average: number | null;
  overall_grade: string;
  gpa: number | null;
}

export interface ResultReport {
  exam: Exam;
  class: ClassItem;
  subjects: Subject[];
  rows: ResultRow[];
  school_type: string;
}

export async function getExams(): Promise<Exam[]> {
  const { data } = await api.get("/grades/exams");
  return data;
}

export async function getClasses(): Promise<ClassItem[]> {
  const { data } = await api.get("/grades/classes");
  return data;
}

export async function getSubjectsForClass(classId: number): Promise<Subject[]> {
  const { data } = await api.get(`/grades/subjects?class_id=${classId}`);
  return data;
}

export async function getResultReport(examId: number, classId: number): Promise<ResultReport> {
  const { data } = await api.get(`/grades/results?exam_id=${examId}&class_id=${classId}`);
  return data;
}

export async function getGradeSheet(examId: number, classId: number, subjectId: number): Promise<GradeRow[]> {
  const { data } = await api.get(`/grades/sheet?exam_id=${examId}&class_id=${classId}&subject_id=${subjectId}`);
  return data;
}

export async function saveGrades(
  examId: number,
  classId: number,
  subjectId: number,
  entries: { student_id: number; score: number; max_score: number; remarks: string }[]
): Promise<number> {
  const { data } = await api.post("/grades/save", { exam_id: examId, class_id: classId, subject_id: subjectId, entries });
  return data.saved;
}

export async function submitGrades(examId: number, classId: number, subjectId: number): Promise<number> {
  const { data } = await api.post("/grades/submit", { exam_id: examId, class_id: classId, subject_id: subjectId });
  return data.submitted;
}

export async function requestGradeChange(
  gradeId: number,
  proposedScore: number,
  proposedMax: number,
  reason: string
): Promise<void> {
  await api.post("/grades/change-request", { grade_id: gradeId, proposed_score: proposedScore, proposed_max: proposedMax, reason });
}
