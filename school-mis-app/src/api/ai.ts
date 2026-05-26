import api from "./client";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessage(messages: ChatMessage[]): Promise<{ message: string }> {
  const res = await api.post("/ai/chat", { messages });
  return res.data;
}
