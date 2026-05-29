import api from "./client";

export type MediaType = "poster" | "banner" | "screenshot";

export interface LandingMediaItem {
  id:          number;
  filename:    string;
  title:       string | null;
  description: string | null;
  media_type:  MediaType;
  sort_order:  number;
  is_active:   number;
  created_at:  string;
}

export const getMedia = (activeOnly = true) =>
  api.get<{ items: LandingMediaItem[] }>("/landing/media", { params: { active_only: activeOnly } })
     .then(r => r.data.items);

export const uploadMedia = (form: FormData) =>
  api.post<LandingMediaItem>("/landing/media", form).then(r => r.data);

export const updateMedia = (id: number, body: Partial<{
  title: string; description: string; media_type: MediaType; sort_order: number; is_active: number;
}>) => api.put<LandingMediaItem>(`/landing/media/${id}`, body).then(r => r.data);

export const deleteMedia = (id: number) =>
  api.delete(`/landing/media/${id}`).then(r => r.data);

/** Build the URL for a media filename. */
export const mediaUrl = (filename: string) => `/uploads/landing/${filename}`;
