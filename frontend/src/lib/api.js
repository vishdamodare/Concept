import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_API_URL || "";
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

// httpOnly cookies (access_token for JWT, session_token for Google OAuth) are the
// authoritative auth store. `withCredentials` ensures they're sent on every call.
// We intentionally do NOT persist tokens in localStorage/sessionStorage — that would
// expose them to any XSS payload.
export const apiClient = axios.create({
  baseURL: API,
  withCredentials: true,
});

export const formatErr = (e) => {
  const d = e?.response?.data?.detail;
  if (!d) return e?.message || "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((x) => (x?.msg ? x.msg : JSON.stringify(x))).join(" ");
  return String(d);
};
