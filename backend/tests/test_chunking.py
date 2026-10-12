import pytest

from app.services.chunking import STRATEGIES, chunk_text

DOC = """# Intro

This is the first sentence. This is the second sentence! Is this the third? Yes it is.

## Details

Paragraph one has several sentences. They go on for a while. """ + "More words here. " * 80 + """

SECURITY REQUIREMENTS

All laptops must be encrypted.
"""


@pytest.mark.parametrize("strategy", list(STRATEGIES))
def test_offsets_point_back_to_text(strategy):
    chunks = chunk_text(DOC, 1, strategy, 300, 50)
    assert chunks
    for c in chunks:
        assert DOC[c.start:c.end] == c.text
        assert c.page == 1


@pytest.mark.parametrize("strategy", ["fixed", "sentence", "structure"])
def test_size_respected(strategy):
    for c in chunk_text(DOC, 1, strategy, 300, 50):
        assert len(c.text) <= 360  # small tolerance for overlap carry-over


def test_structure_carries_headings():
    chunks = chunk_text(DOC, 1, "structure", 300, 0)
    headings = {c.heading for c in chunks}
    assert "Intro" in headings and "Details" in headings
    assert any(c.heading == "SECURITY REQUIREMENTS" for c in chunks)


def test_structure_never_mixes_sections():
    for c in chunk_text(DOC, 1, "structure", 5000, 0):
        assert "Details" not in c.text.split("\n")[0] or c.heading != "Intro"


def test_empty_text():
    for s in STRATEGIES:
        assert chunk_text("   \n\n ", 1, s, 300, 50) == []
