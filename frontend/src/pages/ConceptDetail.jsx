import React, { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiClient, formatErr } from "../lib/api";
import { toast } from "sonner";
import Markdown from "../components/Markdown";
import {
  MapTrifold, GraduationCap, FilmReel, ChatTeardropDots, ImageSquare,
  PaperPlaneTilt, ArrowLeft, Clock, CircleNotch
} from "@phosphor-icons/react";

const TABS = [
  { id: "roadmap", label: "Roadmap", icon: MapTrifold },
  { id: "guide", label: "Study Guide", icon: GraduationCap },
  { id: "videos", label: "Videos", icon: FilmReel },
  { id: "image", label: "Image", icon: ImageSquare },
  { id: "tutor", label: "Tutor", icon: ChatTeardropDots },
];

export default function ConceptDetail() {
  const { id } = useParams();
  const [concept, setConcept] = useState(null);
  const [tab, setTab] = useState("roadmap");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/concepts/${id}`)
      .then((r) => setConcept(r.data))
      .catch((e) => toast.error(formatErr(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12 font-mono text-sm term-loader">Loading concept</div>
    );
  }
  if (!concept) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="border border-dashed border-black p-12 text-center">
          <div className="font-display text-2xl font-bold">Not found</div>
          <Link to="/app" className="brut-btn mt-4 inline-flex">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="concept-detail-page" className="mx-auto max-w-7xl px-6 py-10">
      <Link to="/app" data-testid="back-to-dashboard" className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-zinc-600 hover:text-black">
        <ArrowLeft size={14} weight="bold" /> back to dashboard
      </Link>

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
        {tab === "roadmap" && <RoadmapTab concept={concept} />}
        {tab === "guide" && <GuideTab concept={concept} />}
        {tab === "videos" && <VideosTab concept={concept} />}
        {tab === "image" && <ImageTab concept={concept} />}
        {tab === "tutor" && <TutorTab concept={concept} />}
      </section>
    </div>
  );
}

function RoadmapTab({ concept }) {
  const rm = concept.roadmap || {};
  const milestones = rm.milestones || [];
  return (
    <div data-testid="roadmap-tab" className="grid grid-cols-12 gap-6">
      <div className="col-span-12 md:col-span-4">
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
          {milestones.map((m, i) => (
            <div data-testid={`milestone-${i}`} key={i} className="brut-card p-6">
              <div className="flex items-start justify-between gap-3">
                <div className="font-display text-5xl font-black text-[#002FA7] leading-none w-14 shrink-0">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="flex-1">
                  <div className="font-display text-xl font-bold leading-tight">{m.title}</div>
                  <p className="mt-2 font-mono text-sm text-zinc-700 leading-relaxed">{m.description}</p>
                  {m.topics && m.topics.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {m.topics.map((t, k) => (
                        <span key={k} className="border border-black px-2 py-0.5 font-mono text-[11px]">{t}</span>
                      ))}
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
          ))}
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
            <iframe
              title={v.title}
              src={v.embed}
              className="absolute inset-0 h-full w-full"
              frameBorder="0"
              allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
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
  if (!concept.image) {
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
