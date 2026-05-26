import api from "./client";

export interface Route {
  id: number;
  name: string;
  description: string;
  fare: number;
  vehicle_no: string;
  driver_name: string;
  driver_phone: string;
}

export interface RoutePayload {
  name: string;
  description?: string;
  fare?: number;
  vehicle_no?: string;
  driver_name?: string;
  driver_phone?: string;
}

export const getRoutes = () =>
  api.get<Route[]>("/transport/routes").then((r) => r.data);

export const createRoute = (body: RoutePayload) =>
  api.post<Route>("/transport/routes", body).then((r) => r.data);

export const updateRoute = (id: number, body: RoutePayload) =>
  api.put<Route>(`/transport/routes/${id}`, body).then((r) => r.data);

export const getRouteStudents = (route_id: number) =>
  api.get(`/transport/routes/${route_id}/students`).then((r) => r.data);

export const assignStudent = (body: { student_id: number; route_id: number; academic_year_id: number; term?: number; pickup_point?: string }) =>
  api.post("/transport/assign", body).then((r) => r.data);

export const unassignStudent = (subId: number) =>
  api.delete(`/transport/subscriptions/${subId}`).then((r) => r.data);

export const getTransportStats = () =>
  api.get("/transport/stats").then((r) => r.data);
