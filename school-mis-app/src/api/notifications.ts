import api from "@/api/client";

export interface Notification {
  id:           number;
  type:         string;
  title:        string;
  body:         string;
  data_json:    string | null;
  created_at:   string;
  read_at:      string | null;
  dismissed_at: string | null;
}

export async function getNotifications(unreadOnly = false, limit = 50): Promise<Notification[]> {
  const r = await api.get("/notifications", { params: { unread_only: unreadOnly, limit } });
  return r.data;
}

export async function getUnreadCount(): Promise<number> {
  const r = await api.get("/notifications/unread-count");
  return r.data.count;
}

export async function markRead(id: number): Promise<void> {
  await api.post(`/notifications/${id}/read`);
}

export async function markAllRead(): Promise<void> {
  await api.post("/notifications/mark-all-read");
}

export async function getAuditLog(params?: {
  table_name?: string;
  actor_id?:   number;
  action?:     string;
  limit?:      number;
}): Promise<any[]> {
  const r = await api.get("/audit", { params });
  return r.data;
}
