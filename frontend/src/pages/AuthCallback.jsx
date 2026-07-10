import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient, formatErr } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const nav = useNavigate();
  const { setSessionUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    if (!match) {
      nav("/login", { replace: true });
      return;
    }
    const sessionId = decodeURIComponent(match[1]);

    (async () => {
      try {
        const r = await apiClient.post(
          "/auth/session",
          {},
          { headers: { "X-Session-ID": sessionId } }
        );
        setSessionUser(r.data);
        // Clean the URL fragment and go home
        window.history.replaceState(null, "", window.location.pathname);
        toast.success(`Welcome, ${r.data.name || r.data.email}`);
        nav("/app", { replace: true, state: { user: r.data } });
      } catch (e) {
        toast.error(formatErr(e));
        nav("/login", { replace: true });
      }
    })();
  }, [nav, setSessionUser]);

  return (
    <div
      data-testid="auth-callback"
      className="min-h-[70vh] flex flex-col items-center justify-center font-mono text-sm text-zinc-500"
    >
      <div className="term-loader">Signing you in</div>
    </div>
  );
}
