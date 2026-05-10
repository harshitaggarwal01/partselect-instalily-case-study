import type { ChatResponse, FrontendMessage } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function sendChat(
  messages: FrontendMessage[]
): Promise<ChatResponse> {
  const payload = {
    messages: messages.map((m) => ({ role: m.role, content: m.content })),
  };
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json() as Promise<ChatResponse>;
}
