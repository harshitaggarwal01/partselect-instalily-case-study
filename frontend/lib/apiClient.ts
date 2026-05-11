import type { ChatResponse, FrontendMessage } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function sendChat(
  messages: FrontendMessage[],
  sessionId?: string
): Promise<ChatResponse> {
  // When a sessionId is active, the backend holds full history — send only the last message
  const messagesToSend = sessionId
    ? [messages[messages.length - 1]]
    : messages;

  const payload: Record<string, unknown> = {
    messages: messagesToSend.map((m) => ({ role: m.role, content: m.content })),
  };
  if (sessionId) {
    payload.session_id = sessionId;
  }

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
