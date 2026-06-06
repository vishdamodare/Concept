import React, { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { formatErr } from "../lib/api";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(email, password);
      toast.success("Welcome back");
      nav("/app" + (loc.search || ""));
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="login-page" className="min-h-[calc(100vh-65px)] grid-bg flex items-center justify-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-md brut-card p-8 fade-up">
        <div className="label-tag mb-2">// SIGN IN</div>
        <h1 className="font-display text-4xl font-black tracking-tighter">Welcome back.</h1>
        <p className="mt-2 font-mono text-sm text-zinc-600">Keep building your learning library.</p>

        <div className="mt-8 space-y-4">
          <div>
            <label className="label-tag block mb-2">Email</label>
            <input
              data-testid="login-email-input"
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="brut-input" placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="label-tag block mb-2">Password</label>
            <input
              data-testid="login-password-input"
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="brut-input" placeholder="••••••••"
            />
          </div>
        </div>

        <button data-testid="login-submit-btn" disabled={busy} type="submit" className="brut-btn w-full justify-center mt-8">
          {busy ? "Signing in…" : "Sign in"}
        </button>

        <p className="mt-6 font-mono text-xs text-zinc-600 text-center">
          No account?{" "}
          <Link data-testid="login-go-register" to="/register" className="underline decoration-[#002FA7] font-bold">
            Create one
          </Link>
        </p>
      </form>
    </div>
  );
}
