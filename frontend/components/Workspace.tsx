"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api, ApiError, Conversation, Doc, Me, Msg, openOriginal, PassageView, Source, streamChat, upload,
} from "../lib/api";
import Answer from "./Answer";
import { IconFile, IconMenu, IconSend } from "./Icons";
import Sidebar from "./Sidebar";
import SourcePanel from "./SourcePanel";

const REFUSAL_PREFIX = "I couldn't find this";
const SUGGESTIONS = [
  "Summarize the main points",
  "What dates, numbers or deadlines are mentioned?",
  "List any requirements or action items",
];

export default function Workspace({ token, onLogout }: { token: string; onLogout: () => void }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [view, setView] = useState<PassageView | null>(null);
  const [uploading, setUploading] = useState<{ name: string; pct: number } | null>(null);
  const [notice, setNotice] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const logoutRef = useRef(onLogout);
  logoutRef.current = onLogout;

  const fail = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) return logoutRef.current();
    setNotice(e instanceof Error ? e.message : "Something went wrong");
  }, []);

  const loadDocs = useCallback(async () => {
    try { setDocs(await (await api("/documents", token)).json()); } catch (e) { fail(e); }
  }, [token, fail]);
  const loadMe = useCallback(async () => {
    try { setMe(await (await api("/auth/me", token)).json()); } catch (e) { fail(e); }
  }, [token, fail]);
  const loadConvs = useCallback(async () => {
    try { setConvs(await (await api("/conversations", token)).json()); } catch (e) { fail(e); }
  }, [token, fail]);

  useEffect(() => { loadDocs(); loadMe(); loadConvs(); }, [loadDocs, loadMe, loadConvs]);

  const processing = docs.some((d) => ["queued", "parsing", "embedding"].includes(d.status));
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(loadDocs, 1500);
    return () => clearInterval(t);
  }, [processing, loadDocs]);

  // keep the newest text in view unless the reader scrolled up
  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [msgs]);
  const onScroll = () => {
    const el = scroller.current;
    if (el) stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  // auto-growing composer
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [input]);

  async function addFiles(files: File[]) {
    for (const f of files) {
      try {
        setUploading({ name: f.name, pct: 0 });
        await upload(f, token, (pct) => setUploading({ name: f.name, pct }));
        await loadDocs();
      } catch (e) { fail(e); }
    }
    setUploading(null);
    loadMe();
  }

  async function removeDoc(id: string) {
    try {
      await api(`/documents/${id}`, token, { method: "DELETE" });
      setSelected((s) => s.filter((x) => x !== id));
      if (view?.source.document_id === id) setView(null);
      await loadDocs();
    } catch (e) { fail(e); }
  }

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || busy) return;
    setInput("");
    setNotice("");
    setBusy(true);
    stick.current = true;
    setMsgs((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "", status: "Searching your documents" }]);
    const patch = (f: (m: Msg) => Msg) => setMsgs((m) => (m.length ? [...m.slice(0, -1), f(m[m.length - 1])] : m));
    try {
      await streamChat(token, { question, conversation_id: convId, document_ids: selected.length ? selected : null }, (ev, d) => {
        if (ev === "meta") setConvId(d.conversation_id);
        else if (ev === "sources") patch((m) => ({ ...m, sources: d, status: d.length ? `Reading ${d.length} passage${d.length === 1 ? "" : "s"}` : "No matching passages" }));
        else if (ev === "token") patch((m) => ({ ...m, content: m.content + d.text, status: undefined }));
        else if (ev === "done") patch((m) => ({ ...m, usage: d, status: undefined }));
        else if (ev === "error") patch((m) => ({ ...m, error: d.message, status: undefined }));
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) { logoutRef.current(); return; }
      patch((m) => ({ ...m, error: e instanceof Error ? e.message : "Something went wrong", status: undefined }));
    }
    setBusy(false);
    loadMe();
    loadConvs();
  }

  async function openSource(s: Source) {
    setView({ source: s, passage: null });
    try {
      const passage = await (await api(`/documents/${s.document_id}/chunks/${s.chunk_id}`, token)).json();
      setView({ source: s, passage });
    } catch (e) {
      setView(null);
      fail(e);
    }
  }

  async function openConv(id: string) {
    try {
      const rows: { role: "user" | "assistant"; content: string; sources: Source[] | null }[] =
        await (await api(`/conversations/${id}/messages`, token)).json();
      setMsgs(rows.map((r) => ({ role: r.role, content: r.content, sources: r.sources ?? undefined })));
      setConvId(id);
      setView(null);
      setMenuOpen(false);
      stick.current = true;
    } catch (e) { fail(e); }
  }

  function newChat() {
    setConvId(null);
    setMsgs([]);
    setView(null);
    setMenuOpen(false);
  }

  const ready = docs.filter((d) => d.status === "ready");
  const scope = !ready.length ? "" : selected.length
    ? `Searching ${selected.length} of ${ready.length} documents.`
    : `Searching ${ready.length === 1 ? "your document" : `all ${ready.length} documents`}.`;
  const title = convs.find((c) => c.id === convId)?.title ?? "New chat";

  return (
    <div className={"app" + (view ? " has-panel" : "")}>
      <Sidebar
        open={menuOpen} onClose={() => setMenuOpen(false)}
        docs={docs} selected={selected}
        onToggle={(id) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))}
        onDelete={removeDoc} onFiles={addFiles} uploading={uploading}
        convs={convs} activeConv={convId} onOpenConv={openConv} onNewChat={newChat}
        me={me} onLogout={onLogout}
      />
      {menuOpen && <div className="backdrop" onClick={() => setMenuOpen(false)} />}

      <main className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setMenuOpen(true)} aria-label="Open menu"><IconMenu /></button>
          <h2 className="topbar-title">{title}</h2>
        </header>

        <div className="scroll" ref={scroller} onScroll={onScroll}>
          <div className="thread">
            {msgs.length === 0 ? (
              <div className="empty">
                {docs.length === 0 ? (
                  <>
                    <div className="empty-icon"><IconFile width={28} height={28} /></div>
                    <h3>Add a document to begin</h3>
                    <p>Upload a PDF, text or Markdown file. Once it’s indexed you can ask questions and see exactly which passage each answer came from.</p>
                    <button className="btn btn-primary" onClick={() => fileRef.current?.click()}>Add documents</button>
                    <input ref={fileRef} className="sr-only" type="file" multiple accept=".pdf,.txt,.md" onChange={(e) => { if (e.target.files) addFiles(Array.from(e.target.files)); e.target.value = ""; }} />
                  </>
                ) : ready.length === 0 ? (
                  <>
                    <h3>Getting your documents ready</h3>
                    <p>This usually takes a few seconds. You can ask a question as soon as one shows as Ready.</p>
                  </>
                ) : (
                  <>
                    <h3>Ask about your documents</h3>
                    <p>Answers use only what’s in your files, and each one links to its source.</p>
                    <div className="suggest">
                      {SUGGESTIONS.map((s) => <button key={s} className="suggest-btn" onClick={() => send(s)}>{s}</button>)}
                    </div>
                  </>
                )}
              </div>
            ) : (
              msgs.map((m, i) => {
                if (m.role === "user") return <div className="turn-q" key={i}>{m.content}</div>;
                const refused = m.content.startsWith(REFUSAL_PREFIX);
                const last = i === msgs.length - 1;
                return (
                  <article className="turn-a" key={i}>
                    {m.status && <div className="status"><span className="pulse" />{m.status}</div>}
                    {refused ? (
                      <p className="no-match">{m.content}</p>
                    ) : m.content ? (
                      <Answer text={m.content} sources={m.sources} activeChunk={view?.source.chunk_id} streaming={busy && last && !m.usage && !m.error} onCite={openSource} />
                    ) : null}
                    {m.error && <div className="msg-error" role="alert">{m.error}</div>}
                    {!refused && !!m.sources?.length && m.content && (
                      <ul className="srcs" aria-label="Sources">
                        {m.sources.map((s) => (
                          <li key={s.chunk_id}>
                            <button className={"src" + (view?.source.chunk_id === s.chunk_id ? " src-on" : "")} onClick={() => openSource(s)} title={s.snippet}>
                              <span className="src-n">{s.n}</span>
                              <span className="src-name">{s.filename}</span>
                              <span className="src-page">p. {s.page}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                    {m.usage && (
                      <div className="meta">
                        <span>{m.usage.model}</span>
                        <span>{(m.usage.input_tokens + m.usage.output_tokens + m.usage.embed_tokens).toLocaleString()} tokens</span>
                        <span>{m.usage.cost_usd === 0 ? "$0" : `$${m.usage.cost_usd.toFixed(4)}`}</span>
                        <span>{(m.usage.latency_ms / 1000).toFixed(1)}s</span>
                      </div>
                    )}
                  </article>
                );
              })
            )}
          </div>
        </div>

        <div className="composer-wrap">
          {notice && (
            <div className="notice" role="alert">
              <span>{notice}</span>
              <button className="link" onClick={() => setNotice("")}>Dismiss</button>
            </div>
          )}
          <div className="composer">
            <textarea
              ref={taRef} rows={1} value={input} placeholder="Ask a question about your documents"
              aria-label="Your question"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); }
              }}
            />
            <button className="send" disabled={busy || !input.trim()} onClick={() => send()} aria-label="Send question"><IconSend /></button>
          </div>
          <p className="hint">{scope || "Add a document to start."} Check the numbered sources before relying on an answer.</p>
        </div>
      </main>

      {view && <SourcePanel view={view} onClose={() => setView(null)} onOpenOriginal={() => openOriginal(view.source.document_id, view.source.page, token).catch(fail)} />}
    </div>
  );
}
