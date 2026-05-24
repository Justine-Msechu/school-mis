import api from "./client";

export interface AppUser {
  id: number;
  username: string;
  full_name: string;
  role: string;
  role_label: string;
  is_active: number;
  created_at: string;
}

export interface Role {
  key: string;
  label: string;
  color: string;
}

export const getConfig = () =>
  api.get<Record<string, string>>("/settings/config").then((r) => r.data);

export const setConfig = (key: string, value: string) =>
  api.post("/settings/config", { key, value }).then((r) => r.data);

export const getUsers = () =>
  api.get<AppUser[]>("/settings/users").then((r) => r.data);

export const getRoles = () =>
  api.get<Role[]>("/settings/roles").then((r) => r.data);

export const createUser = (body: { username: string; full_name: string; role: string; password: string }) =>
  api.post<AppUser>("/settings/users", body).then((r) => r.data);

export const updateUser = (id: number, body: { full_name: string; role: string; password?: string }) =>
  api.put<AppUser>(`/settings/users/${id}`, body).then((r) => r.data);

export const toggleUserActive = (id: number) =>
  api.post(`/settings/users/${id}/toggle-active`).then((r) => r.data);
