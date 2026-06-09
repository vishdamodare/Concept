import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiClient, formatErr } from "../lib/api";
import { isSafeHttpUrl, isSafeImageSrc, isSafeYouTubeEmbedUrl } from "../lib/utils";
import { toast } from "sonner";
import Markdown from "../components/Markdown";
import {
  MapTrifold, GraduationCap, FilmReel, ChatTeardropDots, ImageSquare,
  PaperPlaneTilt, ArrowLeft, Clock, CircleNotch, CheckSquare, Square,
  BookOpen, ArrowSquareOut, Question, Lightning, FileText, Books, Code,
  ArticleMedium, DownloadSimple, FilePdf, FileMd
} from "@phosphor-icons/react";

const CourseIcon = GraduationCap;

const TABS = [
  { id: "roadmap", label: "Roadmap", icon: MapTrifold },
  { id: "guide", label: "Study Guide", icon: GraduationCap },
  { id: "resources", label: "Resources", icon: BookOpen },
  { id: "videos", label: "Videos", icon: FilmReel },
  { id: "image", label: "Image", icon: ImageSquare },
  { id: "tutor", label: "Tutor", icon: ChatTeardropDots },
];

export default function ConceptDetail() {
  const { id } = useParams();
  const [concept, setConcept] = useState(null);
  const [tab, setTab] = useState("roadmap");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const progressSeq = useRef(0);

  useEffect(() => {
    let cancelled = false;
    let timer = null;

    const tick = async () => {
      try {
        const r = await apiClient.get(`/concepts/${id}`);
        if (cancelled) return;
        setConcept(r.data);
        setLoadError(null);
        setLoading(false);
        if (r.data?.status === "generating") {
          timer = setTimeout(tick, 3500);
        }
      } catch (e) {
        if (cancelled) return;
        setLoadError(e?.response?.status === 404 ? "not_found" : "error");
        toast.error(formatErr(e));
        setLoading(false);
      }
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  const toggleMilestone = async (index, completed) => {
    if (!concept) return;
    const seq = ++progressSeq.current;
    const next = new Set(concept.progress || []);
    if (completed) next.add(index); else next.delete(index);
    const optimistic = Array.from(next).sort((a, b) => a - b);
    setConcept({ ...concept, progress: optimistic });
    try {
      const r = await apiClient.patch(`/concepts/${id}/progress`, { index, completed });
      if (seq !== progressSeq.current) return;
      setConcept((c) => c ? { ...c, progress: r.data.progress } : c);
    } catch (e) {
      if (seq !== progressSeq.current) return;
      toast.error(formatErr(e));
      try {
        const r = await apiClient.get(`/concepts/${id}`);
        if (seq === progressSeq.current) {
          setConcept(r.data);
        }
      } catch {
        // leave current optimistic state if refresh fails
      }
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12 font-mono text-sm term-loader">Loading concept</div>
    );
  }
  if (!concept) {
    const title = loadError === "not_found" ? "Not found" : "Could not load concept";
    const detail = loadError === "not_found"
      ? "This concept does not exist or you do not have access."
      : "Something went wrong while loading. Please try again.";
    return (
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="border border-dashed border-black p-12 text-center">
          <div className="font-display text-2xl font-bold">{title}</div>
          <p className="mt-2 font-mono text-sm text-zinc-600">{detail}</p>
          <Link to="/app" className="brut-btn mt-4 inline-flex">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  if (concept && concept.status === "generating") {
    return <GeneratingView concept={concept} />;
  }
  if (concept && concept.status === "failed") {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16" data-testid="generation-failed">
        <Link to="/app" className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-zinc-600 hover:text-black mb-6">
          <ArrowLeft size={14} weight="bold" /> back to dashboard
        </Link>
        <div className="brut-card p-8">
          <div className="label-tag mb-2 !text-red-500">// GENERATION FAILED</div>
          <h1 className="font-display text-3xl font-black tracking-tighter">{concept.name}</h1>
          <p className="mt-3 font-mono text-sm text-zinc-700">{concept.error || "Something went wrong while forging this concept."}</p>
          <Link to="/app" className="brut-btn mt-6 inline-flex">Try another</Link>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="concept-detail-page" className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <Link to="/app" data-testid="back-to-dashboard" className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-zinc-600 hover:text-black">
          <ArrowLeft size={14} weight="bold" /> back to dashboard
        </Link>
        <ExportMenu concept={concept} />
      </div>

      <header className="mt-4 border-b border-black pb-8">
        <div className="label-tag mb-2">// CONCEPT // LEVEL: {concept.level}</div>
        <h1 className="font-display text-4xl md:text-6xl font-black tracking-tighter leading-[0.95]">
          {concept.name}
        </h1>
        {concept.roadmap?.summary && (
          <p className="mt-6 max-w-3xl text-base font-mono text-zinc-700 leading-relaxed">
            {concept.roadmap.summary}
          </p>
        )}
      </header>

      <div data-testid="concept-tabs" className="mt-6 flex flex-wrap gap-2 border-b border-black pb-4">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            data-testid={`tab-${tid}`}
            onClick={() => setTab(tid)}
            className={`px-4 py-2 border border-black font-mono text-xs uppercase tracking-widest inline-flex items-center gap-2 ${tab === tid ? "tab-active" : "bg-white hover:bg-zinc-100"}`}
          >
            <Icon size={14} weight="bold" /> {label}
          </button>
        ))}
      </div>

      <section className="mt-8">
        {tab === "roadmap" && <RoadmapTab concept={concept} onToggle={toggleMilestone} />}
        {tab === "guide" && <GuideTab concept={concept} />}
        {tab === "resources" && <ResourcesTab concept={concept} />}
        {tab === "videos" && <VideosTab concept={concept} />}
        {tab === "image" && <ImageTab concept={concept} />}
        {tab === "tutor" && <TutorTab concept={concept} />}
      </section>
    </div>
  );
}

function RoadmapTab({ concept, onToggle }) {
  const rm = concept.roadmap || {};
  const milestones = rm.milestones || [];
  const done = new Set(concept.progress || []);
  const total = milestones.length;
  const completedCount = milestones.reduce((acc, _, i) => acc + (done.has(i) ? 1 : 0), 0);
  const pct = total === 0 ? 0 : Math.round((completedCount / total) * 100);

  return (
    <div data-testid="roadmap-tab" className="grid grid-cols-12 gap-6">
      <div className="col-span-12 md:col-span-4 space-y-4">
        <div data-testid="progress-card" className="brut-card p-6">
          <div className="label-tag mb-2">// PROGRESS</div>
          <div className="flex items-baseline gap-2">
            <div data-testid="progress-percent" className="font-display text-5xl font-black text-[#002FA7] leading-none">{pct}%</div>
            <div className="font-mono text-xs text-zinc-600">{completedCount} / {total} done</div>
          </div>
          <div className="mt-4 h-2 w-full border border-black bg-white relative overflow-hidden">
            <div className="absolute inset-y-0 left-0 bg-[#002FA7] transition-all" style={{ width: `${pct}%` }} />
          </div>
          {pct === 100 && total > 0 && (
            <div className="mt-3 font-mono text-xs text-[#10B981] font-bold">✓ MASTERED</div>
          )}
        </div>

        <div className="brut-card p-6">
          <div className="label-tag mb-2">// PREREQUISITES</div>
          {(rm.prerequisites || []).length === 0 ? (
            <p className="font-mono text-sm text-zinc-500">No prerequisites listed.</p>
          ) : (
            <ul className="font-mono text-sm space-y-2">
              {(rm.prerequisites || []).map((p, i) => (
                <li key={i} className="flex gap-2"><span className="text-[#002FA7]">▸</span> <span>{p}</span></li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="col-span-12 md:col-span-8">
        <div className="label-tag mb-3">// LEARNING PATH</div>
        <div className="space-y-3">
          {milestones.map((m, i) => {
            const isDone = done.has(i);
            return (
              <div
                data-testid={`milestone-${i}`}
                key={i}
                className={`brut-card p-6 transition ${isDone ? "bg-zinc-50" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <button
                    data-testid={`milestone-toggle-${i}`}
                    onClick={() => onToggle(i, !isDone)}
                    aria-label={isDone ? "Mark incomplete" : "Mark complete"}
                    className={`mt-1 shrink-0 transition ${isDone ? "text-[#10B981]" : "text-zinc-400 hover:text-black"}`}
                  >
                    {isDone
                      ? <CheckSquare size={28} weight="fill" />
                      : <Square size={28} weight="regular" />}
                  </button>
                  <div className={`font-display text-5xl font-black leading-none w-14 shrink-0 ${isDone ? "text-zinc-300 line-through decoration-2" : "text-[#002FA7]"}`}>
                    {String(i + 1).padStart(2, "0")}
                  </div>
                  <div className="flex-1">
                    <div className={`font-display text-xl font-bold leading-tight ${isDone ? "text-zinc-500 line-through decoration-2" : ""}`}>
                      {m.title}
                    </div>
                    <p className={`mt-2 font-mono text-sm leading-relaxed ${isDone ? "text-zinc-400" : "text-zinc-700"}`}>
                      {m.description}
                    </p>
                    {m.topics && m.topics.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {m.topics.map((t, k) => (
                          <span key={k} className="border border-black px-2 py-0.5 font-mono text-[11px]">{t}</span>
                        ))}
                      </div>
                    )}

                    {m.key_questions && m.key_questions.length > 0 && (
                      <div className="mt-4 border-l-2 border-[#002FA7] pl-3">
                        <div className="label-tag mb-1 flex items-center gap-1">
                          <Question size={12} weight="bold" /> KEY QUESTIONS
                        </div>
                        <ul className="font-mono text-sm space-y-1 text-zinc-700">
                          {m.key_questions.map((q, k) => (
                            <li key={k}>· {q}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {m.exercise && (
                      <div className="mt-4 bg-zinc-50 border border-zinc-200 p-3">
                        <div className="label-tag mb-1 flex items-center gap-1">
                          <Lightning size={12} weight="fill" /> EXERCISE
                        </div>
                        <p className="font-mono text-sm leading-relaxed text-zinc-800">{m.exercise}</p>
                      </div>
                    )}

                    {m.estimate && (
                      <div className="mt-3 inline-flex items-center gap-1 font-mono text-xs text-zinc-500">
                        <Clock size={12} weight="bold" /> {m.estimate}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function GuideTab({ concept }) {
  return (
    <div data-testid="guide-tab" className="max-w-3xl">
      <div className="brut-card p-8">
        <Markdown text={concept.study_guide || "_No study guide available._"} />
      </div>
    </div>
  );
}

const KIND_ICON = {
  docs: FileText,
  article: ArticleMedium,
  course: CourseIcon,
  book: Books,
  paper: FileText,
  tool: Code,
};

function ResourcesTab({ concept }) {
  const categories = concept.resources?.categories || [];
  if (categories.length === 0) {
    return (
      <div data-testid="resources-tab" className="font-mono text-sm text-zinc-600">
        No web resources were collected for this concept.
      </div>
    );
  }
  const totalCount = categories.reduce((acc, c) => acc + (c.items?.length || 0), 0);

  return (
    <div data-testid="resources-tab">
      <div className="mb-6 flex items-baseline gap-3">
        <div className="label-tag">// HAND-PICKED FROM THE WEB</div>
        <span className="font-mono text-xs text-zinc-500">{totalCount} resources across {categories.length} categories</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {categories.map((cat, ci) => (
          <div data-testid={`resource-category-${ci}`} key={ci} className="brut-card p-5">
            <div className="border-b border-black pb-3 mb-3 flex items-baseline justify-between">
              <h3 className="font-display text-lg font-bold tracking-tight">{cat.name}</h3>
              <span className="font-mono text-[10px] text-zinc-500">{cat.items?.length || 0}</span>
            </div>
            <ul className="space-y-3">
              {(cat.items || []).map((it, ii) => {
                const Icon = KIND_ICON[it.kind] || ArticleMedium;
                const safeUrl = isSafeHttpUrl(it.url);
                const rowClass = "group flex gap-3 items-start p-2 -mx-2 border border-transparent hover:border-black hover:bg-zinc-50 transition";
                const inner = (
                  <>
                    <Icon size={18} weight="duotone" className="text-[#002FA7] shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-bold text-sm leading-snug group-hover:text-[#002FA7] flex items-center gap-1">
                        <span className="truncate">{it.title}</span>
                        {safeUrl && (
                          <ArrowSquareOut size={12} weight="bold" className="opacity-0 group-hover:opacity-100 shrink-0" />
                        )}
                      </div>
                      {it.description && (
                        <p className="mt-1 font-mono text-xs text-zinc-600 leading-relaxed line-clamp-2">
                          {it.description}
                        </p>
                      )}
                      <div className="mt-1 font-mono text-[10px] text-zinc-400 truncate">
                        {safeUrl ? safeHost(it.url) : "Unsafe link blocked"}
                      </div>
                    </div>
                  </>
                );
                return (
                  <li key={ii} data-testid={`resource-item-${ci}-${ii}`}>
                    {safeUrl ? (
                      <a href={it.url} target="_blank" rel="noopener noreferrer" className={rowClass}>
                        {inner}
                      </a>
                    ) : (
                      <div className={rowClass}>{inner}</div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function safeHost(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

function VideosTab({ concept }) {
  const videos = concept.videos || [];
  if (videos.length === 0) {
    return <div data-testid="videos-tab" className="font-mono text-sm text-zinc-600">No videos found for this concept.</div>;
  }
  return (
    <div data-testid="videos-tab" className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {videos.map((v) => (
        <div data-testid={`video-${v.id}`} key={v.id} className="brut-card overflow-hidden">
          <div className="relative w-full" style={{ paddingBottom: "56.25%" }}>
            {isSafeYouTubeEmbedUrl(v.embed) ? (
              <iframe
                title={v.title}
                src={v.embed}
                className="absolute inset-0 h-full w-full"
                frameBorder="0"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-zinc-100 font-mono text-xs text-zinc-600 p-4 text-center">
                Video embed unavailable
              </div>
            )}
          </div>
          <div className="p-4 border-t border-black">
            <div className="font-display font-bold text-sm leading-tight line-clamp-2">{v.title}</div>
            <div className="mt-1 font-mono text-[11px] text-zinc-500 truncate">{v.channel}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ImageTab({ concept }) {
  if (!concept.image || !isSafeImageSrc(concept.image)) {
    return <div data-testid="image-tab" className="font-mono text-sm text-zinc-600">No image was generated for this concept.</div>;
  }
  return (
    <div data-testid="image-tab" className="brut-card p-3 max-w-3xl">
      <img src={concept.image} alt={concept.name} className="w-full h-auto block" />
      <div className="px-3 py-3 border-t border-black">
        <div className="label-tag">// CONCEPT IMAGE</div>
        <div className="mt-1 font-mono text-xs text-zinc-600 leading-relaxed">
          {concept.roadmap?.image_prompt}
        </div>
      </div>
    </div>
  );
}

function TutorTab({ concept }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingHist, setLoadingHist] = useState(true);
  const scrollRef = useRef(null);

  useEffect(() => {
    apiClient.get(`/concepts/${concept.id}/chat`)
      .then((r) => setMessages(r.data))
      .catch((e) => toast.error(formatErr(e)))
      .finally(() => setLoadingHist(false));
  }, [concept.id]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, busy]);

  const send = async (e) => {
    e?.preventDefault?.();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    const optimistic = { id: `tmp-${Date.now()}`, role: "user", content: text };
    setMessages((m) => [...m, optimistic]);
    setBusy(true);
    try {
      const r = await apiClient.post(`/concepts/${concept.id}/chat`, { message: text });
      setMessages((m) => [...m.filter((x) => x.id !== optimistic.id), r.data.user, r.data.assistant]);
    } catch (err) {
      toast.error(formatErr(err));
      setMessages((m) => m.filter((x) => x.id !== optimistic.id));
    } finally {
      setBusy(false);
    }
  };

  const suggestions = [
    "Explain it like I'm 12",
    "Give me a worked example",
    "Quiz me with 3 questions",
    "What's the biggest misconception?",
  ];

  return (
    <div data-testid="tutor-tab" className="brut-card flex flex-col h-[70vh] max-w-4xl">
      <div className="px-5 py-4 border-b border-black flex items-center justify-between">
        <div>
          <div className="label-tag">// TUTOR · {concept.level}</div>
          <div className="font-display font-bold text-lg leading-tight mt-1">{concept.name}</div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 space-y-4 no-scrollbar">
        {loadingHist ? (
          <div className="font-mono text-xs text-zinc-500 term-loader">Loading conversation</div>
        ) : messages.length === 0 ? (
          <div className="text-center py-10">
            <ChatTeardropDots size={36} weight="duotone" className="text-[#002FA7] mx-auto" />
            <div className="mt-3 font-display text-lg font-bold">Ask your tutor anything</div>
            <p className="mt-1 font-mono text-xs text-zinc-600">
              The tutor knows your roadmap and adapts to your level.
            </p>
            <div className="mt-5 flex flex-wrap gap-2 justify-center">
              {suggestions.map((s) => (
                <button
                  key={s}
                  data-testid={`tutor-suggestion-${s.slice(0, 8)}`}
                  onClick={() => setInput(s)}
                  className="border border-black px-3 py-1.5 font-mono text-xs hover:bg-zinc-100"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              data-testid={`message-${m.role}`}
              className={`p-4 border border-black ${m.role === "user" ? "chat-msg-user ml-12" : "chat-msg-assistant mr-12"}`}
            >
              <div className="label-tag !text-current opacity-70 mb-1">{m.role === "user" ? "YOU" : "TUTOR"}</div>
              {m.role === "assistant"
                ? <Markdown text={m.content} />
                : <div className="font-mono text-sm whitespace-pre-wrap leading-relaxed">{m.content}</div>}
            </div>
          ))
        )}
        {busy && (
          <div className="chat-msg-assistant p-4 border border-black mr-12">
            <div className="label-tag opacity-70 mb-1">TUTOR</div>
            <div className="spinner-dots"><span /><span /><span /></div>
          </div>
        )}
      </div>

      <form onSubmit={send} className="border-t border-black p-3 flex gap-2">
        <input
          data-testid="tutor-input"
          disabled={busy}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the tutor…"
          className="brut-input flex-1"
        />
        <button data-testid="tutor-send-btn" disabled={busy || !input.trim()} type="submit" className="brut-btn">
          {busy ? <CircleNotch className="animate-spin" size={14} weight="bold" /> : <PaperPlaneTilt size={14} weight="bold" />}
          Send
        </button>
      </form>
    </div>
  );
}

const STAGE_FLOW = [
  { id: "roadmap", label: "Roadmap: structuring milestones with Claude" },
  { id: "expanding", label: "Study guide, image, videos, web resources" },
  { id: "done", label: "Stitching it all together" },
];

function GeneratingView({ concept }) {
  const idx = Math.max(0, STAGE_FLOW.findIndex((s) => s.id === concept.stage));
  return (
    <div data-testid="generating-view" className="mx-auto max-w-3xl px-6 py-16">
      <Link to="/app" className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-zinc-600 hover:text-black mb-6">
        <ArrowLeft size={14} weight="bold" /> back to dashboard
      </Link>
      <div className="brut-card p-10 fade-up">
        <div className="label-tag mb-2">// FORGING · LEVEL: {concept.level}</div>
        <h1 className="font-display text-4xl md:text-5xl font-black tracking-tighter leading-tight">
          {concept.name}
        </h1>
        <p className="mt-4 font-mono text-sm text-zinc-600">
          We&apos;re building your concept package. Stay here — the page will update live.
        </p>

        <div className="mt-8 space-y-3 font-mono text-sm">
          {STAGE_FLOW.map((s, i) => {
            const state = i < idx ? "done" : i === idx ? "active" : "pending";
            return (
              <div
                key={s.id}
                data-testid={`stage-${s.id}`}
                className={`flex items-center gap-3 p-3 border ${
                  state === "active" ? "border-black bg-zinc-50" :
                  state === "done"   ? "border-zinc-200 text-zinc-400" :
                                       "border-zinc-200 text-zinc-300"
                }`}
              >
                <span className={`w-6 inline-block ${state === "active" ? "text-[#002FA7] font-bold" : ""}`}>
                  {state === "done" ? "✓" : state === "active" ? "▸" : "·"}
                </span>
                <span className="flex-1">{s.label}</span>
                {state === "active" && <span className="spinner-dots"><span /><span /><span /></span>}
              </div>
            );
          })}
        </div>

        <div className="mt-6 font-mono text-xs text-zinc-500 term-loader">working</div>
      </div>
    </div>
  );
}



function ExportMenu({ concept }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(null); // 'md' | 'pdf' | null

  const isReady = !concept.status || concept.status === "ready";

  const handleDownload = async (fmt) => {
    if (!isReady) {
      toast.error("Concept must finish generating before export");
      return;
    }
    setBusy(fmt);
    try {
      const r = await apiClient.get(`/concepts/${concept.id}/export?format=${fmt}`, {
        responseType: "blob",
      });
      const blob = new Blob([r.data], {
        type: fmt === "md" ? "text/markdown;charset=utf-8" : "application/pdf",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safe = (concept.name || "concept").replace(/[^a-z0-9_\- ]+/gi, "").trim().replace(/\s+/g, "_").slice(0, 80) || "concept";
      a.download = `${safe}.${fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Exported as .${fmt}`);
      setOpen(false);
    } catch (e) {
      toast.error(formatErr(e));
    } finally {
      setBusy(null);
    }
  };

  // close on outside click
  useEffect(() => {
    if (!open) return;
    const onClick = (e) => {
      if (!e.target.closest('[data-export-menu]')) setOpen(false);
    };
    window.addEventListener("click", onClick);
    return () => window.removeEventListener("click", onClick);
  }, [open]);

  return (
    <div data-export-menu className="relative">
      <button
        data-testid="export-menu-btn"
        disabled={!isReady}
        onClick={(e) => { e.stopPropagation(); setOpen((v) => !v); }}
        className="brut-btn brut-btn-ghost"
      >
        <DownloadSimple size={14} weight="bold" /> Export
      </button>
      {open && (
        <div data-testid="export-menu" className="absolute right-0 mt-2 w-56 border border-black bg-white z-50 shadow-[6px_6px_0_0_#09090B]">
          <button
            data-testid="export-md-btn"
            disabled={busy !== null}
            onClick={() => handleDownload("md")}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-zinc-100 text-left border-b border-black"
          >
            <FileMd size={18} weight="duotone" className="text-[#002FA7]" />
            <div className="flex-1">
              <div className="font-display font-bold text-sm">Markdown</div>
              <div className="font-mono text-[10px] text-zinc-500">.md · portable plain text</div>
            </div>
            {busy === "md" && <CircleNotch className="animate-spin" size={14} weight="bold" />}
          </button>
          <button
            data-testid="export-pdf-btn"
            disabled={busy !== null}
            onClick={() => handleDownload("pdf")}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-zinc-100 text-left"
          >
            <FilePdf size={18} weight="duotone" className="text-[#002FA7]" />
            <div className="flex-1">
              <div className="font-display font-bold text-sm">PDF</div>
              <div className="font-mono text-[10px] text-zinc-500">.pdf · print-ready</div>
            </div>
            {busy === "pdf" && <CircleNotch className="animate-spin" size={14} weight="bold" />}
          </button>
        </div>
      )}
    </div>
  );
}
