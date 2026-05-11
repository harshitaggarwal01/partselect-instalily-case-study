const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function loginUser(username: string, password: string) {
  const res = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Invalid username or password");
  return res.json() as Promise<{ token: string; user: { id: string; username: string } }>;
}

export async function signupUser(username: string, password: string) {
  const res = await fetch(`${API}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Signup failed");
  }
  return res.json() as Promise<{ token: string; user: { id: string; username: string } }>;
}
