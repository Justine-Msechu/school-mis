import api from "./client";

export interface ErrorLogItem {
  id:          number;
  ts:          string;
  source:      "backend" | "frontend";
  level:       string;
  path:        string | null;
  method:      string | null;
  user_id:     number | null;
  school_id:   number | null;
  role:        string | null;
  error_type:  string | null;
  message:     string;
  stack?:      string | null;
  context?:    string | null;
  request_id?: string | null;
  resolved:    number;
  resolved_at: string | null;
}

export interface ErrorLogList {
  total: number;
  items: ErrorLogItem[];
}

export const reportFrontendError = (body: {
  message:     string;
  stack?:      string;
  path?:       string;
  error_type?: string;
  context?:    Record<string, unknown>;
  request_id?: string;
}) => api.post("/error-logs/report", body).catch(() => {/* never throw */});

export const getErrorLogs = (params?: {
  source?: string;
  resolved?: number;
  limit?: number;
  offset?: number;
}) => api.get<ErrorLogList>("/error-logs", { params }).then(r => r.data);

export const getErrorDetail = (id: number) =>
  api.get<ErrorLogItem & { stack: string; context: string }>(`/error-logs/${id}`).then(r => r.data);

export const resolveError = (id: number) =>
  api.post(`/error-logs/${id}/resolve`).then(r => r.data);

export const clearResolvedErrors = () =>
  api.delete("/error-logs/resolved").then(r => r.data);
