import api from "./client";

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: string;
  role_label: string;
  role_color: string;
  permissions: string[];
}

export interface LoginResponse {
  token: string;
  user: User;
  must_change_pw: boolean;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const { data } = await api.post("/auth/login", { username, password });
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await api.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getMe(): Promise<User & { must_change_pw: boolean }> {
  const { data } = await api.get("/auth/me");
  return data;
}
