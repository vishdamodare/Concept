import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { apiClient, formatErr } from "../lib/api";
import { toast } from "sonner";
import { Sparkle, Trash, ArrowRight, BookBookmark, CircleNotch, MagnifyingGlass, X } from "@phosphor-icons/react";

const LEVELS = ["beginner", "intermediate", "advanced"];

const STAGES = [
  "Drafting roadmap with Claude…",
  "Writing in-depth study guide…",
  "Rendering blueprint with Gemini…",
  "Curating YouTube videos…",
  "Scouring the web for resources…",
  "Stitching it together…",
];

export default function Dashboard() {
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const seed = sp.get("seed") || "";
  const seedLevel = sp.get("level") || "beginner";

  const [concept, setConcept] = useState(seed);
  const [level, setLevel] = useState(LEVELS.includes(seedLevel) ? seedLevel : "beginner");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const triggeredSeedRef = useRef(null);

  const handleGenerate = useCallback(async (n, l) => {
    const name = (n ?? concept).trim();
    const lvl = l ?? level;
    if (name.length < 2) {
      toast.error("Please enter a concept name");
      return;
    }
    setBusy(true);
    try {
      const r = await apiClient.post("/concepts/generate", { name, level: lvl });
      toast.success("Forge started — opening live view");
      nav(`/app/concept/${r.data.id}`);
    } catch (e) {
      toast.error(formatErr(e));
    } finally {
      setBusy(false);
    }
  }, [concept, level, nav]);

  useEffect(() => {
    apiClient.get("/concepts")
      .then((r) => setItems(r.data))
      .catch((e) => toast.error(formatErr(e)))
      .finally(() => setLoading(false));
  }, []);

  // Auto-generate when ?seed= appears (ref tracks current seed for Strict Mode + re-navigation)
  useEffect(() => {
    if (!seed) {
      triggeredSeedRef.current = null;
      return;
    }
    const lvl = LEVELS.includes(seedLevel) ? seedLevel : "beginner";
    if (triggeredSeedRef.current === seed) return;
    triggeredSeedRef.current = seed;
    setConcept(seed);
    setLevel(lvl);
    setSp({}, { replace: true });
    handleGenerate(seed, lvl);
  }, [seed, seedLevel, setSp, handleGenerate]);

  // Rotating loader stage
  useEffect(() => {
    if (!busy) return undefined;
    const t = setInterval(() => setStage((s) => (s + 1) % STAGES.length), 2200);
    return () => clearInterval(t);
  }, [busy]);

  const onDelete = async (id, name) => {
    if (!window.confirm(`Delete "${name}"? This can't be undone.`)) return;
    try {
      await apiClient.delete(`/concepts/${id}`);
      setItems((prev) => prev.filter((x) => x.id !== id));
      toast.success("Deleted");
    } catch (e) { toast.error(formatErr(e)); }
  };

  return (
    <div data-testid="dashboard-page" className="mx-auto max-w-7xl px-6 py-12">
      {/* Generator */}
      <section className="brut-card p-8 mb-12">
        <div className="grid grid-cols-12 gap-8 items-start">
          <div className="col-span-12 md:col-span-7">
            <div className="label-tag mb-2">// NEW CONCEPT</div>
            <h1 className="font-display text-4xl md:text-5xl font-black tracking-tighter">
              What do you want to learn?
            </h1>
            <p className="mt-3 font-mono text-sm text-zinc-600">
              Drop a topic. Pick your level. We&apos;ll build the rest.
            </p>
            <div className="mt-6 space-y-3">
              <input
                data-testid="generate-name-input"
                value={concept}
                disabled={busy}
                onChange={(e) => setConcept(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                placeholder="e.g. Bayesian inference, Mughal architecture…"
                className="brut-input"
              />
              <div className="flex flex-wrap gap-2">
                {LEVELS.map((l) => (
                  <button
                    key={l}
                    data-testid={`generate-level-${l}`}
                    disabled={busy}
                    onClick={() => setLevel(l)}
                    className={`px-3 py-2 border border-black font-mono text-xs uppercase tracking-widest ${level === l ? "bg-black text-white" : "bg-white hover:bg-zinc-100"}`}
                  >
                    {l}
                  </button>
                ))}
              </div>
              <button
                data-testid="generate-submit-btn"
                disabled={busy}
                onClick={() => handleGenerate()}
                className="brut-btn"
              >
                {busy ? (<><CircleNotch className="animate-spin" size={16} weight="bold" /> Forging…</>) : (<><Sparkle size={16} weight="fill" /> Forge concept</>)}
              </button>
            </div>
          </div>

          <div className="col-span-12 md:col-span-5 border border-black p-6 bg-zinc-50 min-h-[220px]">
            {busy ? (
              <div data-testid="generation-loader">
                <div className="label-tag mb-3">// LIVE</div>
                <div className="font-mono text-sm leading-relaxed">
                  {STAGES.map((s, i) => (
                    <div key={i} className={`flex items-center gap-2 ${i === stage ? "text-black" : i < stage ? "text-zinc-400" : "text-zinc-300"}`}>
                      <span>{i < stage ? "✓" : i === stage ? "▸" : "·"}</span>
                      <span>{s}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 term-loader font-mono text-xs text-zinc-500">working</div>
              </div>
            ) : (
              <div>
                <div className="label-tag mb-3">// TIP</div>
                <p className="font-mono text-sm leading-relaxed text-zinc-700">
                  Be specific. &quot;Transformers in NLP&quot; beats &quot;AI.&quot;
                  <br /><br />
                  Try: <span className="text-[#002FA7]">&quot;Kubernetes networking&quot;</span>,{" "}
                  <span className="text-[#002FA7]">&quot;Music theory: modes&quot;</span>,{" "}
                  <span className="text-[#002FA7]">&quot;Game theory for negotiation&quot;</span>.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Library */}
      <LibrarySection
        items={items}
        loading={loading}
        onDelete={onDelete}
      />
    </div>
  );
}

function LibrarySection({ items, loading, onDelete }) {
  const [q, setQ] = useState("");
  const [levelF, setLevelF] = useState("all");
  const [statusF, setStatusF] = useState("all");
  const [sort, setSort] = useState("newest");

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    let list = items.filter((c) => {
      if (levelF !== "all" && c.level !== levelF) return false;
      const st = c.status || "ready";
      if (statusF !== "all" && st !== statusF) return false;
      if (term && !(c.name || "").toLowerCase().includes(term)) return false;
      return true;
    });
    list = [...list];
    if (sort === "newest") list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    if (sort === "oldest") list.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    if (sort === "progress") list.sort((a, b) => {
      const pa = a.milestone_count ? (a.progress?.length || 0) / a.milestone_count : 0;
      const pb = b.milestone_count ? (b.progress?.length || 0) / b.milestone_count : 0;
      return pb - pa;
    });
    if (sort === "az") list.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    return list;
  }, [items, q, levelF, statusF, sort]);

  const counts = useMemo(() => {
    const c = { all: items.length, beginner: 0, intermediate: 0, advanced: 0, generating: 0 };
    items.forEach((it) => {
      if (c[it.level] !== undefined) c[it.level] += 1;
      if ((it.status || "ready") === "generating") c.generating += 1;
    });
    return c;
  }, [items]);

  return (
    <section data-testid="library-section">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <div className="label-tag">// YOUR LIBRARY</div>
          <h2 className="font-display text-3xl font-black tracking-tighter mt-1">Saved concepts</h2>
        </div>
        <span className="font-mono text-xs text-zinc-500">
          {filtered.length} of {items.length} shown
        </span>
      </div>

      {/* Toolbar */}
      <div data-testid="library-toolbar" className="brut-card p-4 mb-6 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <MagnifyingGlass size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            data-testid="library-search-input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name…"
            className="brut-input pl-8 pr-9"
          />
          {q && (
            <button
              data-testid="library-search-clear"
              onClick={() => setQ("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-black"
              aria-label="Clear search"
            >
              <X size={14} weight="bold" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1 border border-black p-1 bg-white">
          {[
            ["all", `All · ${counts.all}`],
            ["beginner", `Beg · ${counts.beginner}`],
            ["intermediate", `Int · ${counts.intermediate}`],
            ["advanced", `Adv · ${counts.advanced}`],
          ].map(([id, label]) => (
            <button
              key={id}
              data-testid={`filter-level-${id}`}
              onClick={() => setLevelF(id)}
              className={`px-2.5 py-1.5 font-mono text-[11px] uppercase tracking-widest ${levelF === id ? "bg-black text-white" : "hover:bg-zinc-100"}`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 border border-black p-1 bg-white">
          {[
            ["all", "All"],
            ["ready", "Ready"],
            ["generating", `Live · ${counts.generating}`],
          ].map(([id, label]) => (
            <button
              key={id}
              data-testid={`filter-status-${id}`}
              onClick={() => setStatusF(id)}
              className={`px-2.5 py-1.5 font-mono text-[11px] uppercase tracking-widest ${statusF === id ? "bg-black text-white" : "hover:bg-zinc-100"}`}
            >
              {label}
            </button>
          ))}
        </div>

        <select
          data-testid="library-sort"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="brut-input !w-auto !py-2 !text-xs !uppercase !tracking-widest"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="progress">Progress</option>
          <option value="az">A → Z</option>
        </select>
      </div>

      {loading ? (
        <div className="font-mono text-sm text-zinc-500 term-loader">Loading library</div>
      ) : items.length === 0 ? (
        <div className="border border-dashed border-black p-12 text-center">
          <BookBookmark size={32} weight="duotone" className="text-[#002FA7] mx-auto" />
          <div className="mt-3 font-display text-xl font-bold">Empty library</div>
          <p className="mt-1 font-mono text-sm text-zinc-600">Forge your first concept above.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div data-testid="no-results" className="border border-dashed border-black p-10 text-center">
          <div className="font-display text-xl font-bold">No matches</div>
          <p className="mt-1 font-mono text-sm text-zinc-600">Try a different search or clear filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((c) => {
            const pct = c.milestone_count
              ? Math.round(((c.progress?.length || 0) / c.milestone_count) * 100)
              : 0;
            const isGenerating = (c.status || "ready") === "generating";
            return (
              <div data-testid={`concept-card-${c.id}`} key={c.id} className="brut-card p-5 flex flex-col">
                <div className="flex items-start justify-between">
                  <span className="label-tag">{c.level}</span>
                  <div className="flex items-center gap-2">
                    {isGenerating && (
                      <span data-testid="card-status-generating" className="font-mono text-[9px] uppercase tracking-widest bg-[#002FA7] text-white px-1.5 py-0.5">
                        Live
                      </span>
                    )}
                    <button
                      data-testid={`delete-concept-${c.id}`}
                      onClick={() => onDelete(c.id, c.name)}
                      className="text-zinc-400 hover:text-red-500 transition"
                      aria-label="Delete"
                    >
                      <Trash size={16} weight="bold" />
                    </button>
                  </div>
                </div>
                <div className="font-display text-xl font-bold mt-3 leading-tight line-clamp-2">{c.name}</div>

                {c.milestone_count > 0 && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between font-mono text-[10px] text-zinc-500 mb-1">
                      <span>{c.progress?.length || 0} / {c.milestone_count}</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="h-1.5 w-full border border-black bg-white relative overflow-hidden">
                      <div className="absolute inset-y-0 left-0 bg-[#002FA7] transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )}

                <div className="mt-auto pt-4 flex items-center justify-between">
                  <span className="font-mono text-[10px] text-zinc-500">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  <Link
                    data-testid={`open-concept-${c.id}`}
                    to={`/app/concept/${c.id}`}
                    className="font-mono text-xs uppercase tracking-widest font-bold text-[#002FA7] hover:underline inline-flex items-center gap-1"
                  >
                    Open <ArrowRight size={12} weight="bold" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
