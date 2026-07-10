import React from "react";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function GoogleSignInButton({ label = "Continue with Google", testId = "google-signin-btn" }) {
  const onClick = () => {
    const redirectUrl = window.location.origin + "/app";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <button
      data-testid={testId}
      type="button"
      onClick={onClick}
      className="w-full flex items-center justify-center gap-3 border border-black bg-white text-black px-4 py-3 font-mono text-xs uppercase tracking-widest font-bold hover:bg-[#002FA7] hover:text-white transition"
    >
      <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden>
        <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35.5 24 35.5 17.4 35.5 12 30.1 12 23.5S17.4 11.5 24 11.5c3 0 5.8 1.1 7.9 3l5.7-5.7C34 5.3 29.3 3.5 24 3.5 12.9 3.5 4 12.4 4 23.5S12.9 43.5 24 43.5c11 0 19.5-8 19.5-19.5 0-1.2-.1-2.4-.4-3.5z"/>
        <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.6 19 12.5 24 12.5c3 0 5.8 1.1 7.9 3l5.7-5.7C34 5.3 29.3 3.5 24 3.5 15.9 3.5 8.9 8.1 6.3 14.7z"/>
        <path fill="#4CAF50" d="M24 43.5c5.2 0 9.8-1.8 13.3-4.8l-6.1-5.1c-2 1.4-4.6 2.4-7.2 2.4-5.2 0-9.6-3.1-11.3-7.6l-6.5 5C8.5 39 15.7 43.5 24 43.5z"/>
        <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.4-2.4 4.4-4.4 5.8l6.1 5.1C40.6 35.1 44 30.2 44 24c0-1.2-.1-2.4-.4-3.5z"/>
      </svg>
      {label}
    </button>
  );
}
