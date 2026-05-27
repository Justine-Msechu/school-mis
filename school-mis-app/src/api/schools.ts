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

export const registerSchool = (body: RegisterSchoolPayload) =>
  api.post<{ ok: boolean; school_name: string; trial_ends: string; message: string }>(
    "/schools/register",
    body,
  );

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
  total_schools:  number;
  active:         number;
  trial:          number;
  expired:        number;
  new_this_week:  number;
  total_users:    number;
  expiring_soon:  number;
  by_plan:        Record<string, number>;
  recent_schools: RecentSchool[];
  expiring_list:  ExpiringSchool[];
}

export const getSuperAdminSchools = () =>
  api.get<SchoolRow[]>("/superadmin/schools");

export const getPlatformStats = () =>
  api.get<PlatformStats>("/superadmin/stats");

export const updateSchoolSubscription = (schoolId: number, body: SubscriptionUpdate) =>
  api.put<{ ok: boolean }>(`/superadmin/schools/${schoolId}/subscription`, body);
