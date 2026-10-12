"""Three chunking strategies, all returning Chunks with page + char offsets so
citations can point back to the exact passage.

fixed     - sliding window of N chars with overlap (baseline)
sentence  - pack whole sentences up to N chars, overlap by trailing sentences
structure - detect headings/paragraphs, never mix sections, carry the heading
            as context (embedded with the text, stored separately for display)
"""
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    page: int
    start: int
    end: int
    heading: str | None = None

    @property
    def embed_text(self) -> str:
        return f"{self.heading}\n{self.text}" if self.heading else self.text


Span = tuple[int, int]


def _mk(text: str, page: int, s: int, e: int, heading=None) -> Chunk | None:
    raw = text[s:e]
    stripped = raw.strip()
    if not stripped:
        return None
    s += len(raw) - len(raw.lstrip())
    return Chunk(stripped, page, s, s + len(stripped), heading)


def fixed_size(text: str, page: int, size: int, overlap: int) -> list[Chunk]:
    step = max(size - overlap, 1)
    out = []
    for s in range(0, len(text), step):
        c = _mk(text, page, s, min(s + size, len(text)))
        if c:
            out.append(c)
        if s + size >= len(text):
            break
    return out


def _sentence_spans(text: str, base: int = 0, end: int | None = None) -> list[Span]:
    end = len(text) if end is None else end
    seg = text[base:end]
    spans, pos = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n{2,}", seg):
        if m.start() > pos:
            spans.append((base + pos, base + m.start()))
        pos = m.end()
    if pos < len(seg):
        spans.append((base + pos, end))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def _hard_split(span: Span, size: int) -> list[Span]:
    s, e = span
    return [(i, min(i + size, e)) for i in range(s, e, size)]


def _units(text: str, span: Span, size: int) -> list[Span]:
    """Break a span into <= size units (sentences, then hard splits)."""
    if span[1] - span[0] <= size:
        return [span]
    out = []
    for sp in _sentence_spans(text, span[0], span[1]):
        out.extend(_hard_split(sp, size) if sp[1] - sp[0] > size else [sp])
    return out


def _pack(text: str, spans: list[Span], size: int, overlap: int, page: int, heading=None) -> list[Chunk]:
    chunks: list[Chunk] = []
    cur: list[Span] = []

    def flush():
        if cur:
            c = _mk(text, page, cur[0][0], cur[-1][1], heading)
            if c:
                chunks.append(c)

    for sp in spans:
        if cur and sp[1] - cur[0][0] > size:
            flush()
            keep, total = [], 0
            for s in reversed(cur):
                if total + (s[1] - s[0]) > overlap:
                    break
                keep.insert(0, s)
                total += s[1] - s[0]
            cur = keep
        cur.append(sp)
    flush()
    return chunks


def sentence_aware(text: str, page: int, size: int, overlap: int) -> list[Chunk]:
    units = []
    for sp in _sentence_spans(text):
        units.extend(_units(text, sp, size))
    return _pack(text, units, size, overlap, page)


_HEAD = re.compile(r"^(#{1,6}\s+.+|\d+(\.\d+)*\.?\s+[A-Z].{0,80}|[A-Z][A-Z0-9 \-:,&]{3,80})$")


def _is_heading(line: str) -> bool:
    line = line.strip()
    return (
        0 < len(line) <= 100
        and not line.endswith((".", ",", ";"))
        and bool(_HEAD.match(line))
    )


def _blocks(text: str):
    """Yield (start, end, is_heading) for paragraphs and heading lines."""
    para_s = para_e = None
    for m in re.finditer(r"[^\n]*\n?", text):
        line = m.group()
        if not line:
            break
        body = line.rstrip()
        if not body.strip():
            if para_s is not None:
                yield para_s, para_e, False
                para_s = None
        elif _is_heading(body):
            if para_s is not None:
                yield para_s, para_e, False
                para_s = None
            yield m.start(), m.start() + len(body), True
        else:
            if para_s is None:
                para_s = m.start()
            para_e = m.start() + len(body)
    if para_s is not None:
        yield para_s, para_e, False


def structure_aware(text: str, page: int, size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    units: list[Span] = []

    def flush():
        nonlocal units
        if units:
            chunks.extend(_pack(text, units, size, 0, page, heading))
        units = []

    for s, e, is_head in _blocks(text):
        if is_head:
            flush()
            heading = text[s:e].strip().lstrip("#").strip()
        else:
            units.extend(_units(text, (s, e), size))
    flush()
    return chunks


STRATEGIES = {"fixed": fixed_size, "sentence": sentence_aware, "structure": structure_aware}


def chunk_text(text: str, page: int, strategy: str, size: int, overlap: int) -> list[Chunk]:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown chunk strategy: {strategy}")
    return STRATEGIES[strategy](text, page, size, overlap)
