"use client";
import React, { createContext, useContext, useState, useEffect } from "react";

interface UserPublic { id: string; username: string; }
interface AuthContextValue {
  user: UserPublic | null;
  token: string | null;
  login: (u: UserPublic, t: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null, token: null, login: () => {}, logout: () => {}
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const t = localStorage.getItem("auth_token");
    const u = localStorage.getItem("auth_user");
    if (t && u) { setToken(t); setUser(JSON.parse(u)); }
  }, []);

  const login = (u: UserPublic, t: string) => {
    setUser(u); setToken(t);
    localStorage.setItem("auth_token", t);
    localStorage.setItem("auth_user", JSON.stringify(u));
    // Also set cookie for middleware
    document.cookie = `auth_token=${t}; path=/; SameSite=Lax; max-age=86400`;
  };

  const logout = () => {
    setUser(null); setToken(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    document.cookie = "auth_token=; path=/; max-age=0";
  };

  return <AuthContext.Provider value={{ user, token, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
