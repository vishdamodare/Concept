import React, { createContext, useContext, useEffect, useState } from "react";
import { apiClient } from "./api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null); // null = checking, false = guest
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    apiClient
      .get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => setUser(false))
      .finally(() => setBootstrapped(true));
  }, []);

  const login = async (email, password) => {
    const r = await apiClient.post("/auth/login", { email, password });
    if (r.data.token) localStorage.setItem("cf_token", r.data.token);
    setUser(r.data);
    return r.data;
  };

  const register = async (name, email, password) => {
    const r = await apiClient.post("/auth/register", { name, email, password });
    if (r.data.token) localStorage.setItem("cf_token", r.data.token);
    setUser(r.data);
    return r.data;
  };

  const logout = async () => {
    try { await apiClient.post("/auth/logout"); } catch (e) {}
    localStorage.removeItem("cf_token");
    setUser(false);
  };

  return (
    <AuthCtx.Provider value={{ user, login, register, logout, bootstrapped }}>
      {children}
    </AuthCtx.Provider>
  );
};

export const useAuth = () => useContext(AuthCtx);
