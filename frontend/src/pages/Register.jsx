import React, { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { formatErr } from "../lib/api";
import { toast } from "sonner";
import GoogleSignInButton from "../components/GoogleSignInButton";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await register(name, email, password);
      toast.success("Account created");
      nav("/app" + (loc.search || ""));
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="register-page" className="min-h-[calc(100vh-65px)] grid-bg flex items-center justify-center p-6">
      <form onSubmit={onSubmit} className="w-full max-w-md brut-card p-8 fade-up">
        <div className="label-tag mb-2">// CREATE ACCOUNT</div>
        <h1 className="font-display text-4xl font-black tracking-tighter">Forge your first path.</h1>
        <p className="mt-2 font-mono text-sm text-zinc-600">Takes 10 seconds. No credit card.</p>

        <div className="mt-8 space-y-4">
          <div>
            <label className="label-tag block mb-2">Name</label>
            <input
              data-testid="register-name-input"
              required value={name} onChange={(e) => setName(e.target.value)}
              className="brut-input" placeholder="Ada Lovelace"
            />
          </div>
          <div>
            <label className="label-tag block mb-2">Email</label>
            <input
              data-testid="register-email-input"
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="brut-input" placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="label-tag block mb-2">Password</label>
            <input
              data-testid="register-password-input"
              type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
              className="brut-input" placeholder="6+ characters"
            />
          </div>
        </div>

        <button data-testid="register-submit-btn" disabled={busy} type="submit" className="brut-btn w-full justify-center mt-8">
          {busy ? "Creating…" : "Create account"}
        </button>

        <div className="mt-6 flex items-center gap-3">
          <div className="flex-1 h-px bg-zinc-200" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">or</span>
          <div className="flex-1 h-px bg-zinc-200" />
        </div>

        <div className="mt-6">
          <GoogleSignInButton testId="register-google-btn" label="Sign up with Google" />
        </div>

        <p className="mt-6 font-mono text-xs text-zinc-600 text-center">
          Already have an account?{" "}
          <Link data-testid="register-go-login" to="/login" className="underline decoration-[#002FA7] font-bold">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
