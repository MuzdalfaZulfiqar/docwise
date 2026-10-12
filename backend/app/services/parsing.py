from pathlib import Path

from pypdf import PdfReader


def parse_file(path: str) -> list[tuple[int, str]]:
    """Return [(page_number, text)]. Plain text/markdown is treated as one page."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(str(p))
        return [(i + 1, (pg.extract_text() or "")) for i, pg in enumerate(reader.pages)]
    if ext in {".txt", ".md"}:
        return [(1, p.read_text(encoding="utf-8", errors="replace"))]
    raise ValueError(f"unsupported file type: {ext}")
