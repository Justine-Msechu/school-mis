import api from "./client";

// ── Roles ──────────────────────────────────────────────────────────────────────

export interface RbacRole {
  id: number;
  name: string;
  label: string;
  color: string;
  is_system: number;
  permissions: string[];
}

export interface Permission {
  id: number;
  code: string;
  domain: string;
  action: string;
  description: string;
  scope_type: string;
}

export const getRbacRoles = () =>
  api.get<RbacRole[]>("/rbac/roles").then((r) => r.data);

export const createRbacRole = (body: { name: string; label: string; color?: string }) =>
  api.post<RbacRole>("/rbac/roles", body).then((r) => r.data);

export const updateRbacRole = (id: number, body: { label: string; color?: string }) =>
  api.put<RbacRole>(`/rbac/roles/${id}`, body).then((r) => r.data);

export const getRolePermissions = (roleId: number) =>
  api.get<{ role: RbacRole; permissions: Permission[] }>(`/rbac/roles/${roleId}/permissions`).then((r) => r.data);

export const setRolePermissions = (roleId: number, permission_codes: string[]) =>
  api.put(`/rbac/roles/${roleId}/permissions`, { permission_codes }).then((r) => r.data);

export const listPermissions = () =>
  api.get<Permission[]>("/rbac/permissions").then((r) => r.data);

// ── User permission overrides ──────────────────────────────────────────────────

export interface PermissionOverride {
  id: number;
  user_id: number;
  permission: string;
  effect: "ALLOW" | "DENY";
  reason: string;
  granted_by: number | null;
  granted_by_name: string | null;
  expires_at: string | null;
  created_at: string;
}

export const getUserOverrides = (uid: number) =>
  api.get<{ user: { id: number; username: string; full_name: string; role: string }; overrides: PermissionOverride[] }>(
    `/rbac/users/${uid}/overrides`
  ).then((r) => r.data);

export const addUserOverride = (
  uid: number,
  body: { permission: string; effect: "ALLOW" | "DENY"; reason?: string; expires_at?: string | null }
) => api.post<PermissionOverride>(`/rbac/users/${uid}/overrides`, body).then((r) => r.data);

export const deleteUserOverride = (uid: number, oid: number) =>
  api.delete(`/rbac/users/${uid}/overrides/${oid}`).then((r) => r.data);

// ── Teacher subject assignments ────────────────────────────────────────────────

export interface TeacherAssignment {
  id: number;
  user_id: number;
  class_id: number;
  subject_id: number;
  academic_year_id: number | null;
  is_active: number;
  assigned_at: string;
  teacher_name: string;
  teacher_role: string;
  class_name: string;
  subject_name: string;
  year_label: string | null;
}

export const listTeacherAssignments = (params?: { user_id?: number; class_id?: number }) =>
  api.get<TeacherAssignment[]>("/rbac/assignments/teacher", { params }).then((r) => r.data);

export const assignTeacher = (body: {
  user_id: number;
  class_id: number;
  subject_id: number;
  academic_year_id?: number | null;
}) => api.post<TeacherAssignment>("/rbac/assignments/teacher", body).then((r) => r.data);

export const removeTeacherAssignment = (id: number) =>
  api.delete(`/rbac/assignments/teacher/${id}`).then((r) => r.data);

// ── Class teacher assignments ──────────────────────────────────────────────────

export interface ClassTeacherAssignment {
  id: number;
  user_id: number;
  class_id: number;
  academic_year_id: number | null;
  is_active: number;
  assigned_at: string;
  teacher_name: string;
  class_name: string;
  year_label: string | null;
}

export const listClassTeacherAssignments = () =>
  api.get<ClassTeacherAssignment[]>("/rbac/assignments/classteacher").then((r) => r.data);

export const assignClassTeacher = (body: {
  user_id: number;
  class_id: number;
  academic_year_id?: number | null;
}) => api.post<ClassTeacherAssignment>("/rbac/assignments/classteacher", body).then((r) => r.data);

export const removeClassTeacherAssignment = (id: number) =>
  api.delete(`/rbac/assignments/classteacher/${id}`).then((r) => r.data);

// ── User roles ─────────────────────────────────────────────────────────────────

export const getUserRoles = (uid: number) =>
  api.get<{ user: { id: number; username: string; full_name: string; role: string }; roles: RbacRole[] }>(
    `/rbac/users/${uid}/roles`
  ).then((r) => r.data);

export const setUserRoles = (uid: number, role_ids: number[]) =>
  api.put(`/rbac/users/${uid}/roles`, { role_ids }).then((r) => r.data);
