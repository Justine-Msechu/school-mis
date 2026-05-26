import api from "./client";

export interface SetupStatus {
  needs_setup: boolean;
  school_name: string;
}

export interface SetupPayload {
  school_name:    string;
  school_address: string;
  school_phone:   string;
  school_email:   string;
  school_type:    string;
  admin_username: string;
  admin_fullname: string;
  admin_password: string;
}

export const getSetupStatus = () =>
  api.get<SetupStatus>("/setup/status").then((r) => r.data);

export const initializeSystem = (payload: SetupPayload) =>
  api.post<{ ok: boolean; school_name: string; trial_ends: string; message: string }>(
    "/setup/initialize",
    payload,
  ).then((r) => r.data);
