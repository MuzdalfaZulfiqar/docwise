import React from "react";
import type { Source } from "../lib/api";

type Props = {
  text: string;
  sources?: Source[];
  activeChunk?: number | null;
  streaming?: boolean;
  onCite: (s: Source) => void;
};

// **bold** and [n] citation markers -> elements
function inline(text: string, keyBase: string, p: Props): React.ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|\[\d+\])/g).filter(Boolean).map((part, i) => {
    const key = `${keyBase}-${i}`;
    if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) return <strong key={key}>{part.slice(2, -2)}</strong>;
    const m = /^\[(\d+)\]$/.exec(part);
    if (m) {
      const s = p.sources?.find((x) => x.n === Number(m[1]));
      if (s) {
        return (
          <button key={key} className={"cite" + (p.activeChunk === s.chunk_id ? " cite-on" : "")} onClick={() => p.onCite(s)} title={`${s.filename}, page ${s.page}`} aria-label={`Source ${s.n}: ${s.filename}, page ${s.page}`}>
            {s.n}
          </button>
        );
      }
    }
    return <span key={key}>{part}</span>;
  });
}

export default function Answer(props: Props) {
  const blocks: React.ReactNode[] = [];
  const st = { para: [] as string[], list: null as null | { ordered: boolean; items: string[] } };

  const flushPara = () => {
    if (!st.para.length) return;
    const k = `p${blocks.length}`;
    blocks.push(<p key={k}>{inline(st.para.join(" "), k, props)}</p>);
    st.para = [];
  };
  const flushList = () => {
    if (!st.list) return;
    const k = `l${blocks.length}`;
    const Tag = st.list.ordered ? "ol" : "ul";
    blocks.push(<Tag key={k}>{st.list.items.map((it, i) => <li key={i}>{inline(it, `${k}-${i}`, props)}</li>)}</Tag>);
    st.list = null;
  };

  for (const line of props.text.split("\n")) {
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      flushPara();
      const ordered = !!numbered;
      if (st.list && st.list.ordered !== ordered) flushList();
      if (!st.list) st.list = { ordered, items: [] };
      st.list.items.push((bullet || numbered)![1]);
    } else if (!line.trim()) {
      flushPara();
      flushList();
    } else {
      flushList();
      st.para.push(line.trim());
    }
  }
  flushPara();
  flushList();

  return (
    <div className="answer">
      {blocks}
      {props.streaming && <span className="caret" aria-hidden="true" />}
    </div>
  );
}
