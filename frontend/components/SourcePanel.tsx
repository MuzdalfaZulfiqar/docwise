import type { PassageView } from "../lib/api";
import { IconClose } from "./Icons";

const tail = (t: string) => (t.length > 260 ? "…" + t.slice(-260) : t);
const head = (t: string) => (t.length > 260 ? t.slice(0, 260) + "…" : t);

export default function SourcePanel({ view, onClose, onOpenOriginal }: {
  view: PassageView; onClose: () => void; onOpenOriginal: () => void;
}) {
  const { source, passage } = view;
  const prev = passage?.neighbors.find((n) => n.idx === passage.idx - 1);
  const next = passage?.neighbors.find((n) => n.idx === passage.idx + 1);
  const heading = passage?.heading ?? source.heading;

  return (
    <aside className="panel" aria-label="Source passage">
      <div className="panel-head">
        <div className="panel-titles">
          <div className="panel-file" title={source.filename}>{source.filename}</div>
          <div className="panel-loc">
            <span>Page {source.page}</span>
            {heading && <span className="panel-heading">{heading}</span>}
          </div>
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close source"><IconClose /></button>
      </div>

      <div className="panel-body">
        {!passage ? (
          <div className="skeleton" aria-label="Loading passage"><i /><i /><i /><i style={{ width: "60%" }} /></div>
        ) : (
          <div className="doc-text">
            {prev && <p className="ctx">{tail(prev.text)}</p>}
            <p><mark>{passage.text}</mark></p>
            {next && <p className="ctx">{head(next.text)}</p>}
          </div>
        )}
      </div>

      <div className="panel-foot">
        <button className="btn" onClick={onOpenOriginal}>Open original file at page {source.page}</button>
      </div>
    </aside>
  );
}
