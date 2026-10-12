import { DragEvent, useState } from "react";
import { APP_NAME, Conversation, Doc, Me } from "../lib/api";
import { IconClose, IconPlus, IconTrash, LogoMark } from "./Icons";

const STATUS: Record<string, string> = {
  queued: "Waiting to start", parsing: "Reading file", embedding: "Indexing", ready: "Ready", failed: "Failed",
};

type Props = {
  open: boolean;
  onClose: () => void;
  docs: Doc[];
  selected: string[];
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  onFiles: (files: File[]) => void;
  uploading: { name: string; pct: number } | null;
  convs: Conversation[];
  activeConv: string | null;
  onOpenConv: (id: string) => void;
  onNewChat: () => void;
  me: Me | null;
  onLogout: () => void;
};

export default function Sidebar(p: Props) {
  const [tab, setTab] = useState<"docs" | "history">("docs");
  const [drag, setDrag] = useState(false);
  const readyCount = p.docs.filter((d) => d.status === "ready").length;

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files.length) p.onFiles(Array.from(e.dataTransfer.files));
  };

  const pct = p.me ? Math.min(100, (p.me.tokens_used_today / Math.max(p.me.daily_token_quota, 1)) * 100) : 0;

  return (
    <aside className={"sidebar" + (p.open ? " open" : "")}>
      <div className="side-top">
        <div className="side-row">
          <div className="brand"><LogoMark /><span>{APP_NAME}</span></div>
          <button className="icon-btn side-close" onClick={p.onClose} aria-label="Close menu"><IconClose /></button>
        </div>
        <button className="btn btn-primary" onClick={p.onNewChat}><IconPlus /> New chat</button>
        <div className="seg" role="tablist">
          <button role="tab" aria-selected={tab === "docs"} className={tab === "docs" ? "on" : ""} onClick={() => setTab("docs")}>Documents</button>
          <button role="tab" aria-selected={tab === "history"} className={tab === "history" ? "on" : ""} onClick={() => setTab("history")}>History</button>
        </div>
      </div>

      <div className="side-body">
        {tab === "docs" ? (
          <>
            <label className={"drop" + (drag ? " drop-on" : "")} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
              <input className="sr-only" type="file" multiple accept=".pdf,.txt,.md" onChange={(e) => { if (e.target.files) p.onFiles(Array.from(e.target.files)); e.target.value = ""; }} />
              <span className="drop-title">Add documents</span>
              <span className="drop-sub">Drop files here or click. PDF, TXT or Markdown.</span>
            </label>

            {p.uploading && (
              <div className="doc">
                <div className="doc-name">{p.uploading.name}</div>
                <div className="bar"><i style={{ width: `${p.uploading.pct}%` }} /></div>
                <div className="doc-status">Uploading {p.uploading.pct}%</div>
              </div>
            )}

            {p.docs.length === 0 && !p.uploading && <p className="side-empty">No documents yet. Add one to start asking questions.</p>}

            <ul className="doc-list">
              {p.docs.map((d) => {
                const working = ["queued", "parsing", "embedding"].includes(d.status);
                return (
                  <li key={d.id} className={"doc" + (p.selected.includes(d.id) ? " doc-on" : "")}>
                    <div className="doc-top">
                      {d.status === "ready" && readyCount > 1 ? (
                        <input type="checkbox" checked={p.selected.includes(d.id)} onChange={() => p.onToggle(d.id)} aria-label={`Only search ${d.filename}`} />
                      ) : null}
                      <div className="doc-name" title={d.filename}>{d.filename}</div>
                      <button className="icon-btn icon-btn-sm" onClick={() => p.onDelete(d.id)} aria-label={`Delete ${d.filename}`}><IconTrash width={16} height={16} /></button>
                    </div>
                    {working && <div className="bar"><i style={{ width: `${d.progress}%` }} /></div>}
                    <div className={"doc-status" + (d.status === "failed" ? " bad" : "")}>
                      {STATUS[d.status] ?? d.status}
                      {d.status === "ready" && d.chunk_count ? <span className="gap">{d.chunk_count} passages</span> : null}
                      {d.error ? <span className="gap">{d.error}</span> : null}
                    </div>
                  </li>
                );
              })}
            </ul>
            {readyCount > 1 && <p className="side-hint">Tick documents to search only those. With none ticked, all are searched.</p>}
          </>
        ) : (
          <ul className="hist-list">
            {p.convs.length === 0 && <li className="side-empty">Your past chats will appear here.</li>}
            {p.convs.map((c) => (
              <li key={c.id}>
                <button className={"hist" + (p.activeConv === c.id ? " hist-on" : "")} onClick={() => p.onOpenConv(c.id)}>
                  <span className="hist-title">{c.title}</span>
                  <span className="hist-date">{new Date(c.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="side-foot">
        {p.me && (
          <div className="meter" title="Tokens used today across chat and indexing">
            <div className="meter-text">{p.me.tokens_used_today.toLocaleString()} of {p.me.daily_token_quota.toLocaleString()} tokens used today</div>
            <div className="bar"><i className={pct > 90 ? "warn" : ""} style={{ width: `${pct}%` }} /></div>
          </div>
        )}
        <div className="acct">
          <span className="acct-email" title={p.me?.email}>{p.me?.email}</span>
          <button className="link" onClick={p.onLogout}>Log out</button>
        </div>
      </div>
    </aside>
  );
}
