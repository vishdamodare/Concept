import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { SignOut, User as UserIcon } from "@phosphor-icons/react";

export default function NavBar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();

  const onLogout = async () => {
    await logout();
    nav("/");
  };

  return (
    <header
      data-testid="navbar"
      className="sticky top-0 z-40 w-full border-b border-black bg-white/80 backdrop-blur-xl"
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link to="/" data-testid="nav-logo" className="flex items-center gap-2">
          <div className="h-7 w-7 border border-black bg-[#002FA7]" />
          <span className="font-display text-xl font-black tracking-tighter">
            CONCEPT/FORGE
          </span>
        </Link>

        <nav className="flex items-center gap-3 font-mono text-xs uppercase tracking-widest">
          {user ? (
            <>
              <Link
                data-testid="nav-dashboard-link"
                to="/app"
                className={`px-3 py-2 transition ${loc.pathname.startsWith("/app") ? "bg-black text-white" : "hover:bg-zinc-100"}`}
              >
                Dashboard
              </Link>
              <div className="hidden md:flex items-center gap-2 border border-black px-3 py-2">
                <UserIcon size={14} weight="bold" />
                <span data-testid="nav-user-email" className="truncate max-w-[160px]">{user.email}</span>
              </div>
              <button data-testid="nav-logout-btn" onClick={onLogout} className="brut-btn brut-btn-ghost">
                <SignOut size={14} weight="bold" /> Logout
              </button>
            </>
          ) : (
            <>
              <Link data-testid="nav-login-link" to="/login" className="brut-btn brut-btn-ghost">Login</Link>
              <Link data-testid="nav-register-link" to="/register" className="brut-btn">Start free</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
