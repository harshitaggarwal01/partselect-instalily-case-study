"use client";
import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { loginUser } from "@/lib/authClient";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const { token, user } = await loginUser(username, password);
      login(user, token);
      window.location.href = "/support";
    } catch (err) {
      setError((err as Error).message);
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#f5f5f5] flex flex-col">
      {/* Header strip */}
      <div className="bg-[#1d6b64] px-6 py-3 flex items-center gap-3">
        <div className="w-8 h-8 bg-[#f0a020] rounded-sm flex items-center justify-center">
          <span className="text-white font-bold text-xs">PS</span>
        </div>
        <span className="text-white font-bold text-lg">PartSelect</span>
        <span className="text-[#a8d5d1] text-sm ml-1">Here to help since 1999</span>
      </div>
      {/* Login card */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 w-full max-w-sm p-8">
          <h1 className="text-2xl font-bold text-[#1a1a1a] mb-1">Sign in</h1>
          <p className="text-sm text-gray-500 mb-6">Access your PartSelect support assistant</p>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text" value={username} onChange={e => setUsername(e.target.value)}
                required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1d6b64]"
                placeholder="e.g. instalily"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)}
                required className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1d6b64]"
              />
            </div>
            {error && <p className="text-red-600 text-sm">{error}</p>}
            <button
              type="submit" disabled={loading}
              className="bg-[#1d6b64] hover:bg-[#165a54] text-white font-medium py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-4">
            No account?{" "}
            <Link href="/signup" className="text-[#0066cc] hover:underline">Create one</Link>
          </p>
          <p className="text-center text-xs text-gray-400 mt-2">Demo: instalily / instalily</p>
        </div>
      </div>
    </div>
  );
}
