"""Render the reference-kernel source to slide images.

Produces two images:
  * code_reference_kernel.svg            -- the original source, syntax-highlighted
  * code_reference_kernel_index_removed.svg -- same, with the index-bookkeeping
                                            lines that the optimization removed
                                            highlighted and struck through.

The snippet is `reference_kernel` from frozen_problem.py (verbatim). The removed
lines are the index memory I/O: the per-iteration load `idx = inp.indices[i]`
and the writeback `inp.indices[i] = idx`. The "Removing Unnecessary Work" rung
drops both memory operations because final indices are not graded, and the live
index stays in scratch while the index arithmetic still runs.
"""

from __future__ import annotations

import io
import keyword
import tokenize
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "results" / "charts"

SOURCE = '''def reference_kernel(t: Tree, inp: Input):
    """
    Reference implementation of the kernel.

    A parallel tree traversal where at each node we set
    cur_inp_val = myhash(cur_inp_val ^ node_val)
    and then choose the left branch if cur_inp_val is even.
    If we reach the bottom of the tree we wrap around to the top.
    """
    for h in range(inp.rounds):
        for i in range(len(inp.indices)):
            idx = inp.indices[i]
            val = inp.values[i]
            val = myhash(val ^ t.values[idx])
            idx = 2 * idx + (1 if val % 2 == 0 else 2)
            idx = 0 if idx >= len(t.values) else idx
            inp.values[i] = val
            inp.indices[i] = idx
'''

# 1-based line numbers of the index memory I/O removed by the optimization.
REMOVED_LINES = {12, 18}

# Light syntax theme (GitHub-ish); red reserved for the "removed" highlight.
COL_DEFAULT = "#1f2328"
COL_KEYWORD = "#0550ae"
COL_FUNC = "#8250df"
COL_STRING = "#116329"
COL_COMMENT = "#6e7781"
COL_NUMBER = "#953800"
COL_OP = "#57606a"

MONO = "Menlo, Consolas, 'DejaVu Sans Mono', monospace"
FS = 15
CHAR_W = 9.03      # monospace advance at 15px
LINE_H = 23


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _color(prev_kw_def: bool, toktype: int, text: str) -> str:
    if toktype == tokenize.COMMENT:
        return COL_COMMENT
    if toktype == tokenize.STRING:
        return COL_STRING
    if toktype == tokenize.NUMBER:
        return COL_NUMBER
    if toktype == tokenize.OP:
        return COL_OP
    if toktype == tokenize.NAME:
        if prev_kw_def:
            return COL_FUNC
        if keyword.iskeyword(text):
            return COL_KEYWORD
    return COL_DEFAULT


def _tokenize_lines(src: str):
    """Return {line_no: [(col, text, color), ...]} for visible tokens."""
    lines: dict[int, list[tuple[int, str, str]]] = {}
    prev_was_def = False
    toks = tokenize.generate_tokens(io.StringIO(src).readline)
    for toktype, text, (srow, scol), (erow, ecol), _line in toks:
        if toktype in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
                       tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        if not text:
            continue
        color = _color(prev_was_def, toktype, text)
        # Multi-line tokens (the docstring) get split across physical lines.
        parts = text.split("\n")
        for k, piece in enumerate(parts):
            if piece == "":
                continue
            row = srow + k
            col = scol if k == 0 else 0
            lines.setdefault(row, []).append((col, piece, color))
        prev_was_def = (toktype == tokenize.NAME and text == "def")
    return lines


def _render(highlight: bool, title: str, caption: str | None, path: Path) -> Path:
    src_lines = SOURCE.rstrip("\n").split("\n")
    tok_lines = _tokenize_lines(SOURCE)
    n = len(src_lines)
    max_chars = max(len(l) for l in src_lines)

    pad = 18
    gutter_w = 50
    code_x = 40 + gutter_w + 14
    panel_x = 40
    panel_y = 86
    panel_w = code_x + int(max_chars * CHAR_W) + 22 - panel_x
    panel_h = pad * 2 + n * LINE_H
    width = panel_x + panel_w + 40
    height = panel_y + panel_h + (54 if caption else 28)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="{panel_x}" y="50" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#0f172a">{_esc(title)}</text>',
        f'<text x="{panel_x}" y="72" font-family="Arial, sans-serif" font-size="13" fill="#64748b">frozen_problem.py · reference_kernel()</text>',
        # Panel + gutter.
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" fill="#ffffff" stroke="#d8dee4" stroke-width="1.2"/>',
        f'<rect x="{panel_x}" y="{panel_y}" width="{gutter_w}" height="{panel_h}" rx="10" fill="#f6f8fa"/>',
        f'<rect x="{panel_x + gutter_w - 10}" y="{panel_y}" width="10" height="{panel_h}" fill="#f6f8fa"/>',
        f'<line x1="{panel_x + gutter_w}" y1="{panel_y}" x2="{panel_x + gutter_w}" y2="{panel_y + panel_h}" stroke="#e6eaf0" stroke-width="1"/>',
    ]

    top = panel_y + pad
    for i, raw in enumerate(src_lines):
        line_no = i + 1
        ytop = top + i * LINE_H
        ybase = ytop + FS + 2
        removed = highlight and line_no in REMOVED_LINES
        if removed:
            parts.append(
                f'<rect x="{panel_x + gutter_w}" y="{ytop - 2:.1f}" width="{panel_w - gutter_w}" height="{LINE_H}" fill="#ffebe9"/>'
            )
            parts.append(
                f'<rect x="{panel_x + gutter_w}" y="{ytop - 2:.1f}" width="3.5" height="{LINE_H}" fill="#cf222e"/>'
            )
        # Line number.
        parts.append(
            f'<text x="{panel_x + gutter_w - 12}" y="{ybase:.1f}" text-anchor="end" font-family="{MONO}" font-size="12" fill="#9aa5b1">{line_no}</text>'
        )
        # Tokens.
        op_color = "#1f2328"
        for col, text, color in tok_lines.get(line_no, []):
            x = code_x + col * CHAR_W
            fill = color
            extra = ' opacity="0.55"' if removed else ""
            parts.append(
                f'<text x="{x:.1f}" y="{ybase:.1f}" font-family="{MONO}" font-size="{FS}" fill="{fill}"{extra} xml:space="preserve">{_esc(text)}</text>'
            )
        if removed:
            line_w = len(raw.rstrip()) * CHAR_W
            indent = (len(raw) - len(raw.lstrip())) * CHAR_W
            parts.append(
                f'<line x1="{code_x + indent:.1f}" y1="{ybase - 5:.1f}" x2="{code_x + line_w:.1f}" y2="{ybase - 5:.1f}" stroke="#cf222e" stroke-width="1.6"/>'
            )

    if caption:
        cy = panel_y + panel_h + 30
        parts.extend(
            [
                f'<rect x="{panel_x}" y="{cy - 16:.1f}" width="14" height="14" rx="3" fill="#ffebe9" stroke="#cf222e" stroke-width="1.2"/>',
                f'<text x="{panel_x + 22}" y="{cy - 4:.1f}" font-family="Arial, sans-serif" font-size="14" fill="#334155">{_esc(caption)}</text>',
            ]
        )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def write_all():
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = [
        _render(False, "Reference Kernel: original source", None,
                CHARTS / "code_reference_kernel.svg"),
        _render(True, "Reference Kernel: index bookkeeping removed",
                "Removed: index load and writeback to memory; final indices are not graded, and the live index stays in scratch.",
                CHARTS / "code_reference_kernel_index_removed.svg"),
    ]
    return out


def main():
    for p in write_all():
        print(p)


if __name__ == "__main__":
    main()
