import api from "./client";

export interface DashboardStats {
  students?:            number;
  teachers?:            number;
  classes?:             number;
  pending_fees?:        number;
  attendance_today?:    number;
  attendance_rate?:     number;
  welfare_cases?:       number;
  health_visits_today?: number;
  recent_activity?:     Activity[];
}

export interface Activity {
  id:         number;
  action:     string;
  module:     string;
  created_at: string;
  user_name:  string;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get("/dashboard/stats");
  return data;
}
