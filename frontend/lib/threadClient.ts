import type { Thread } from "./types";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function authHeader(token: string) {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

export async function listThreads(token: string): Promise<Thread[]> {
  const res = await fetch(`${API}/api/threads`, { headers: authHeader(token) });
  if (!res.ok) return [];
  return res.json();
}

export async function createThread(token: string, title?: string): Promise<Thread> {
  const res = await fetch(`${API}/api/threads`, {
    method: "POST", headers: authHeader(token),
    body: JSON.stringify({ title: title ?? "New Conversation" }),
  });
  if (!res.ok) throw new Error("Failed to create thread");
  return res.json();
}

export async function getThreadMessages(token: string, threadId: string): Promise<{ role: string; content: string }[]> {
  const res = await fetch(`${API}/api/threads/${threadId}`, { headers: authHeader(token) });
  if (!res.ok) return [];
  const data = await res.json();
  return data.messages ?? [];
}
