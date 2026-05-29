import api from "./client";

export interface HealthAlert {
  id:           number;
  ts:           string;
  metric:       string;
  level:        "warning" | "critical";
  value:        number | null;
  threshold:    number | null;
  message:      string;
  resolved:     number;
  resolved_at:  string | null;
  auto_resolved: number;
}

export interface AlertCount {
  total:    number;
  critical: number;
}

export interface LiveStatus {
  db: {
    connections: number;
    max:         number;
    pct:         number;
    status:      "ok" | "warning" | "critical";
  };
  errors_5min:     number;
  expired_schools: number;
}

export const getAlertCount  = () =>
  api.get<AlertCount>("/platform/health/count").then(r => r.data);

export const getAlerts = (resolved = 0) =>
  api.get<{ items: HealthAlert[]; total: number }>("/platform/health/alerts", { params: { resolved } }).then(r => r.data);

export const getLiveStatus = () =>
  api.get<LiveStatus>("/platform/health/status").then(r => r.data);

export const resolveAlert = (id: number) =>
  api.post(`/platform/health/alerts/${id}/resolve`).then(r => r.data);

export const clearResolvedAlerts = () =>
  api.delete("/platform/health/alerts/resolved").then(r => r.data);
