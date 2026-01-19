from pathlib import Path


def _extract_snippet(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = None
    end = None

    for idx, line in enumerate(lines):
        if line.strip() == "# DOCS_SNIPPET_START":
            start = idx
        if line.strip() == "# DOCS_SNIPPET_END":
            end = idx
            break

    assert start is not None, "DOCS_SNIPPET_START not found in example file"
    assert end is not None, "DOCS_SNIPPET_END not found in example file"
    assert end > start, "DOCS_SNIPPET_END appears before DOCS_SNIPPET_START"

    return "\n".join(lines[start : end + 1]).rstrip()


def _extract_doc_block(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_block = False
    blocks = []
    current = []

    for line in lines:
        if line.startswith("```") and "python" in line:
            in_block = True
            current = []
            continue
        if line.startswith("```") and in_block:
            in_block = False
            blocks.append("\n".join(current).rstrip())
            current = []
            continue
        if in_block:
            current.append(line)

    for block in blocks:
        if "# DOCS_SNIPPET_START" in block:
            return block.rstrip()

    raise AssertionError("Python docs block with DOCS_SNIPPET_START not found")


def test_first_game_walkthrough_docs_match_example():
    example_path = Path("examples/first_game_walkthrough.py")
    docs_path = Path("docs/first_game_walkthrough.md")

    snippet = _extract_snippet(example_path)
    doc_block = _extract_doc_block(docs_path)

    assert doc_block == snippet
