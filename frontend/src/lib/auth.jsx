import React, { createContext, useContext, useEffect, useState } from "react";
import { apiClient } from "./api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); // null = checking, false = guest
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    // CRITICAL: If returning from Emergent OAuth callback, skip /me check.
    // AuthCallback will exchange the session_id and establish the session first.
    if (typeof window !== "undefined" && window.location.hash?.includes("session_id=")) {
      setBootstrapped(true);
      return;
    }
    apiClient
      .get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => {
        setUser(false);
        localStorage.removeItem("cf_token");
      })
      .finally(() => setBootstrapped(true));
  }, []);

  const login = async (email, password) => {
    const r = await apiClient.post("/auth/login", { email, password });
    setUser(r.data);
    return r.data;
  };

  const register = async (name, email, password) => {
    const r = await apiClient.post("/auth/register", { name, email, password });
    setUser(r.data);
    return r.data;
  };

  const setSessionUser = (u) => setUser(u);

  const logout = async () => {
    try { await apiClient.post("/auth/logout"); } catch (e) { /* ignore network errors during logout */ }
    localStorage.removeItem("cf_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, login, register, logout, setSessionUser, bootstrapped }}>
      {children}
    </AuthCtx.Provider>
  );
};

export const useAuth = () => useContext(AuthCtx);
