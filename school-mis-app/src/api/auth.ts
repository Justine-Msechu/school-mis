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

export async function login(username: string, password: string): Promise<{ token: string; user: User }> {
  const { data } = await api.post("/auth/login", { username, password });
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getMe(): Promise<User> {
  const { data } = await api.get("/auth/me");
  return data;
}
