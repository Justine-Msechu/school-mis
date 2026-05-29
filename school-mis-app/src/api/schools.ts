import api from "./client";

export interface RegisterSchoolPayload {
  school_name:           string;
  school_type?:          string;
  school_ownership?:     string;
  registration_number?:  string;
  school_email?:         string;
  contact_phone?:        string;
  school_address?:       string;
  school_location?:      string;
  country?:              string;
  website?:              string;
  login_header_message?: string;
  admin_fullname:        string;
  admin_username:        string;
  admin_password:        string;
}

export interface SchoolRow {
  id:                  number;
  name:                string;
  email:               string | null;
  contact_phone:       string | null;
  admin_name:          string | null;
  plan:                string;
  subscription_status: string;
  trial_ends:          string | null;
  is_active:           number;
  created_at:          string;
  user_count:          number;
}

export interface SubscriptionUpdate {
  plan:        string;
  status:      string;
  trial_ends?: string;
}

export interface RecentSchool {
  id:                  number;
  name:                string;
  plan:                string;
  subscription_status: string;
  created_at:          string | null;
  admin_name:          string | null;
}

export interface ExpiringSchool {
  id:                  number;
  name:                string;
  plan:                string;
  subscription_status: string;
  trial_ends:          string;
  admin_name:          string | null;
}

export interface PlatformStats {
  total_schools:   number;
  active:          number;
  trial:           number;
  expired:         number;
  suspended:       number;
  new_this_week:   number;
  total_users:     number;
  total_students:  number;
  total_teachers:  number;
  expiring_soon:   number;
  by_plan:         Record<string, number>;
  recent_schools:  RecentSchool[];
  expiring_list:   ExpiringSchool[];
}

export type FeatureFlags = Record<string, Record<string, boolean>>;

export interface Announcement {
  id:          number;
  title:       string;
  body:        string;
  priority:    "normal" | "warning" | "critical";
  target_plan: string;
  created_at:  string;
  expires_at:  string | null;
  is_active?:  number;
}

export interface AnnouncementPayload {
  title:        string;
  body:         string;
  priority:     "normal" | "warning" | "critical";
  target_plan:  string;
  expires_at?:  string | null;
}

export interface PlatformUser {
  id:          number;
  username:    string;
  full_name:   string;
  role:        string;
  is_active:   number;
  school_id:   number | null;
  school_name: string | null;
}

// ── Public ────────────────────────────────────────────────────────────────────

export const registerSchool = (body: RegisterSchoolPayload) =>
  api.post<{ ok: boolean; school_name: string; trial_ends: string; message: string }>(
    "/schools/register",
    body,
  );

// ── Superadmin ────────────────────────────────────────────────────────────────

export const getPlatformStats = () =>
  api.get<PlatformStats>("/superadmin/stats");

export const getSuperAdminSchools = () =>
  api.get<SchoolRow[]>("/superadmin/schools");

export const updateSchoolSubscription = (schoolId: number, body: SubscriptionUpdate) =>
  api.put<{ ok: boolean }>(`/superadmin/schools/${schoolId}/subscription`, body);

export const suspendSchool = (schoolId: number) =>
  api.post<{ ok: boolean }>(`/superadmin/schools/${schoolId}/suspend`);

export const activateSchool = (schoolId: number) =>
  api.post<{ ok: boolean }>(`/superadmin/schools/${schoolId}/activate`);

export const resetAdminPassword = (schoolId: number) =>
  api.post<{ ok: boolean; temp_password: string }>(`/superadmin/schools/${schoolId}/reset-admin-password`);

export const getFeatureFlags = () =>
  api.get<FeatureFlags>("/superadmin/feature-flags");

export const setFeatureFlag = (plan: string, module: string, enabled: boolean) =>
  api.put<{ ok: boolean }>(`/superadmin/feature-flags/${plan}/${module}`, { enabled });

export const listAnnouncements = () =>
  api.get<Announcement[]>("/superadmin/announcements");

export const createAnnouncement = (body: AnnouncementPayload) =>
  api.post<{ ok: boolean; id: number }>("/superadmin/announcements", body);

export const deleteAnnouncement = (id: number) =>
  api.delete<{ ok: boolean }>(`/superadmin/announcements/${id}`);

export const getSuperAdminUsers = () =>
  api.get<PlatformUser[]>("/superadmin/users").then((r) => r.data);

// ── School-facing ─────────────────────────────────────────────────────────────

export const getActiveAnnouncements = () =>
  api.get<Announcement[]>("/announcements");
