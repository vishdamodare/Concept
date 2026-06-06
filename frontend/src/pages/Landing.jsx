import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowRight, Lightning, GraduationCap, MapTrifold, Sparkle, Brain, FilmReel } from "@phosphor-icons/react";
import { useAuth } from "../lib/auth";

const LEVELS = [
  { id: "beginner", label: "Beginner", hint: "Brand new to it" },
  { id: "intermediate", label: "Intermediate", hint: "Know the basics" },
  { id: "advanced", label: "Advanced", hint: "Going deep" },
];

export default function Landing() {
  const [concept, setConcept] = useState("");
  const [level, setLevel] = useState("beginner");
  const { user } = useAuth();
  const nav = useNavigate();

  const onStart = (e) => {
    e?.preventDefault?.();
    const target = user ? "/app" : "/register";
    const params = concept.trim() ? `?seed=${encodeURIComponent(concept)}&level=${level}` : "";
    nav(target + params);
  };

  return (
    <div data-testid="landing-page">
      {/* HERO */}
      <section className="relative grid-bg border-b border-black">
        <div className="mx-auto max-w-7xl px-6 py-20 md:py-28 grid grid-cols-12 gap-8">
          <div className="col-span-12 md:col-span-8">
            <div className="label-tag mb-6">AI LEARNING SYSTEM // V1.0</div>
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-black tracking-tighter leading-[0.92]">
              Type a concept.<br />
              <span className="text-[#002FA7]">Get a learning</span><br />
              blueprint in 30s.
            </h1>
            <p className="mt-8 max-w-xl text-base md:text-lg leading-relaxed text-zinc-700">
              Drop any topic — quantum entanglement, REST APIs, mughal architecture — and ConceptForge crafts a
              personalized roadmap, study guide, illustrations, video picks, and a tutor that adapts to your level.
            </p>

            <form onSubmit={onStart} className="mt-10 flex flex-col gap-3 max-w-xl">
              <input
                data-testid="concept-search-input"
                value={concept}
                onChange={(e) => setConcept(e.target.value)}
                placeholder="e.g. Neural networks, French Revolution, Linear Algebra…"
                className="brut-input"
              />
              <div className="flex flex-wrap gap-2">
                {LEVELS.map((l) => (
                  <button
                    type="button"
                    key={l.id}
                    data-testid={`level-${l.id}`}
                    onClick={() => setLevel(l.id)}
                    className={`px-3 py-2 border border-black font-mono text-xs uppercase tracking-widest transition ${level === l.id ? "bg-black text-white" : "bg-white hover:bg-zinc-100"}`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
              <button data-testid="landing-cta-btn" type="submit" className="brut-btn self-start">
                Forge my path <ArrowRight size={16} weight="bold" />
              </button>
            </form>
          </div>

          <div className="col-span-12 md:col-span-4 flex">
            <div className="brut-card w-full p-6 flex flex-col gap-4 self-stretch">
              <div className="label-tag">// SAMPLE OUTPUT</div>
              <div className="font-display text-2xl font-bold leading-tight">
                "Transformers (deep learning)"
              </div>
              <div className="font-mono text-xs text-zinc-500">level=intermediate</div>
              <ol className="font-mono text-sm space-y-2 mt-2">
                {[
                  "01  Tokens, embeddings & attention math",
                  "02  Self-attention from scratch",
                  "03  Multi-head & positional encoding",
                  "04  Encoder vs decoder stacks",
                  "05  Training tricks: LR, warmup, masking",
                  "06  Build a mini-GPT in PyTorch",
                ].map((line) => (
                  <li key={line} className="flex gap-2 items-start">
                    <span className="text-[#002FA7]">▸</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ol>
              <div className="mt-auto pt-4 border-t border-zinc-200 flex items-center justify-between">
                <span className="label-tag">~7h total</span>
                <Sparkle size={20} weight="duotone" className="text-[#002FA7]" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="border-b border-black diagonal-bg">
        <div className="mx-auto max-w-7xl px-6 py-20 grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-4">
            <div className="label-tag mb-4">// WHAT YOU GET</div>
            <h2 className="font-display text-4xl md:text-5xl font-black tracking-tighter">
              Five things, one prompt.
            </h2>
            <p className="mt-4 text-zinc-600 font-mono text-sm leading-relaxed">
              Every concept generates a full learning package — no flipping through 12 tabs.
            </p>
          </div>
          {[
            { icon: MapTrifold, title: "Structured Roadmap", desc: "5-7 milestones from foundations to mastery, with time estimates." },
            { icon: GraduationCap, title: "Deep Study Guide", desc: "A focused markdown lesson with worked examples & practice questions." },
            { icon: FilmReel, title: "Curated Videos", desc: "Hand-picked YouTube clips that match your roadmap." },
            { icon: Sparkle, title: "Concept Image", desc: "AI-illustrated visual to anchor the idea in your head." },
            { icon: Brain, title: "Adaptive Tutor", desc: "Chat with a tutor calibrated to your knowledge level." },
            { icon: Lightning, title: "Save & resume", desc: "Every concept is saved to your dashboard. Pick up anytime." },
          ].map((f, i) => (
            <div key={i} data-testid={`feature-${i}`} className="col-span-12 md:col-span-4 brut-card p-6">
              <f.icon size={28} weight="duotone" className="text-[#002FA7]" />
              <div className="mt-4 font-display text-xl font-bold">{f.title}</div>
              <p className="mt-2 font-mono text-sm text-zinc-600 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="border-b border-black">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <div className="label-tag mb-4">// PROCESS</div>
          <h2 className="font-display text-4xl md:text-5xl font-black tracking-tighter mb-12">
            Three steps, zero fluff.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              ["01", "Name it", "Type any concept — broad or niche. Pick your current level."],
              ["02", "We forge", "Claude Sonnet drafts the roadmap & guide. Gemini sketches the visual. YouTube delivers the clips."],
              ["03", "You learn", "Move through milestones, watch, read, then chat with the tutor when stuck."],
            ].map(([n, t, d]) => (
              <div key={n} className="p-6 border border-black">
                <div className="font-display text-6xl font-black text-[#002FA7] leading-none">{n}</div>
                <div className="mt-4 font-display text-2xl font-bold">{t}</div>
                <p className="mt-2 font-mono text-sm text-zinc-600 leading-relaxed">{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="bg-black text-white">
        <div className="mx-auto max-w-7xl px-6 py-20 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <div className="label-tag !text-zinc-400 mb-4">// READY?</div>
            <h2 className="font-display text-4xl md:text-5xl font-black tracking-tighter">
              Stop bookmarking. Start learning.
            </h2>
          </div>
          <Link
            data-testid="footer-cta-btn"
            to={user ? "/app" : "/register"}
            className="brut-btn bg-[#002FA7] border-[#002FA7] hover:bg-white hover:text-black hover:border-white"
          >
            {user ? "Go to dashboard" : "Create free account"}
            <ArrowRight size={16} weight="bold" />
          </Link>
        </div>
        <div className="border-t border-zinc-800">
          <div className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between font-mono text-xs text-zinc-500">
            <span>© ConceptForge · built with Claude + Gemini</span>
            <span>v1.0</span>
          </div>
        </div>
      </section>
    </div>
  );
}
