import type { ChatResponse, FrontendMessage } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const API = API_BASE;

export async function sendChat(
  messages: FrontendMessage[],
  sessionId?: string,
  token?: string,
  threadId?: string
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
  if (threadId) {
    payload.thread_id = threadId;
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json() as Promise<ChatResponse>;
}

export async function getCart(token: string) {
  const res = await fetch(`${API}/api/cart`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) return null;
  return res.json();
}

export async function addToCart(token: string, partNumber: string) {
  const res = await fetch(`${API}/api/cart/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ part_number: partNumber }),
  });
  if (!res.ok) throw new Error("Failed to add to cart");
  return res.json();
}

export async function removeFromCart(token: string, partNumber: string) {
  const res = await fetch(`${API}/api/cart/items/${partNumber}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to remove from cart");
  return res.json();
}

export async function getCheckoutLinks(token: string): Promise<{ links: string[] }> {
  const res = await fetch(`${API}/api/cart/checkout-links`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) return { links: [] };
  return res.json();
}
