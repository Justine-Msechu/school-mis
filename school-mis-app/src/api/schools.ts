import api from "./client";

export interface RegisterSchoolPayload {
  school_name:    string;
  school_email?:  string;
  contact_phone?: string;
  admin_fullname: string;
  admin_username: string;
  admin_password: string;
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

export const getSuperAdminSchools = () =>
  api.get<SchoolRow[]>("/superadmin/schools");

export const updateSchoolSubscription = (schoolId: number, body: SubscriptionUpdate) =>
  api.put<{ ok: boolean }>(`/superadmin/schools/${schoolId}/subscription`, body);
