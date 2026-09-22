#!/usr/bin/env python3
"""Count the Diabetes Care word budgets for main.tex.

Diabetes Care limits an Original Article to a 4,000-word BODY, a 250-word
structured ABSTRACT, and Article Highlights of 75-130 words. Word's counter is
authoritative at submission; this script exists so the title-page declaration can
be kept honest while the manuscript is still LaTeX.

What counts as body: the introduction, Research Design and Methods, Results, and
Conclusions. Excluded: the title page block, abstract, Article Highlights,
keywords, abbreviations, tables, figure legends, Acknowledgments, bibliography,
and the whole Supplementary Material section.

Conventions, chosen to approximate Word:
  * LaTeX comments (% to end of line) are dropped, so the editorial notes in
    main.tex never inflate the count.
  * Control sequences are dropped but their braced arguments are kept, because
    \\emph{Baseline sex differences.} is words a reader reads.
  * \\todo{...} contents ARE counted, and reported separately, because the
    scaffolds are placeholders for prose that will occupy that budget.
  * A numeric range, CI, or n~(\\%) pair counts as one word, matching how Word
    treats an unspaced token.

Usage:  python3 other/scripts/count_words.py [path/to/main.tex]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Environments whose contents are never body text.
DROP_ENVIRONMENTS = ("abstract", "table", "tabular", "suppfigure", "figure",
                     "center", "itemize", "thebibliography")

# Body runs from the end of the abbreviations/graphical-abstract preamble block
# to the Acknowledgments heading. These anchors are the section commands.
BODY_START_ANCHOR = r"% Introduction — Diabetes Care runs the introduction"
BODY_END_ANCHOR = r"\section*{Acknowledgments}"


def strip_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
        # A comment starts at an unescaped %.
        cut = None
        for i, ch in enumerate(line):
            if ch == "%" and (i == 0 or line[i - 1] != "\\"):
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def drop_environments(text: str, names: tuple[str, ...]) -> str:
    for name in names:
        pattern = re.compile(
            r"\\begin\{" + name + r"\*?\}.*?\\end\{" + name + r"\*?\}",
            re.DOTALL,
        )
        text = pattern.sub(" ", text)
    return text


def to_words(text: str) -> list[str]:
    # \command[opt]{arg} -> arg ; \command -> nothing
    text = re.sub(r"\\[A-Za-z@]+\s*(\[[^\]]*\])?", " ", text)
    text = re.sub(r"\\[^A-Za-z\s]", " ", text)          # \\, \%, \_, \&
    text = text.replace("{", " ").replace("}", " ")
    text = re.sub(r"\$[^$]*\$", " STAT ", text)          # inline math = one word
    text = re.sub(r"[~]", " ", text)
    return [w for w in re.split(r"\s+", text) if re.search(r"[A-Za-z0-9]", w)]


def count(text: str) -> int:
    return len(to_words(drop_environments(strip_comments(text), DROP_ENVIRONMENTS)))


def slice_between(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "main.tex")
    raw = path.read_text(encoding="utf-8")

    body_raw = slice_between(raw, BODY_START_ANCHOR, BODY_END_ANCHOR)
    body = count(body_raw)

    # \todo blocks inside the body, reported separately: the Introduction and
    # Conclusions are scaffolds, so the "real" body count will move a long way.
    todos = re.findall(r"\\todo\{", strip_comments(body_raw))
    todo_words = 0
    stripped = strip_comments(body_raw)
    for m in re.finditer(r"\\todo\{", stripped):
        depth, i = 1, m.end()
        while i < len(stripped) and depth:
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
            i += 1
        todo_words += len(to_words(stripped[m.end():i - 1]))

    abstract_raw = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
                             raw, re.DOTALL).group(1)
    abstract = len(to_words(strip_comments(abstract_raw)))

    highlights_raw = slice_between(raw, r"\textbf{Article Highlights}",
                                  r"\vspace{0.25cm}")
    highlights = len(to_words(strip_comments(highlights_raw)))

    print(f"{path}")
    print(f"  Body            {body:>5}   (limit 4,000)")
    print(f"    of which \\todo {todo_words:>4}   (scaffold, will be replaced by prose)")
    print(f"    real prose    {body - todo_words:>5}")
    print(f"  Abstract        {abstract:>5}   (limit 250)")
    print(f"  Highlights      {highlights:>5}   (limit 75-130)")
    print(f"  \\todo blocks in body: {len(todos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
