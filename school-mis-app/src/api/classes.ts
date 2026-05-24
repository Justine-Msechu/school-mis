import api from "./client";

export interface ClassRecord {
  id: number;
  name: string;
  level: string | null;
  stream: string | null;
}

export const getClassList = () =>
  api.get<ClassRecord[]>("/classes").then((r) => r.data);
