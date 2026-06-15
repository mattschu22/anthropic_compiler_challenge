"""A clarity-first diagram of the target VLIW + SIMD core.

Shows, per engine: how many slots issue each cycle (drawn as cells), the SIMD
width, and the instruction set it supports (as chips). Grounded directly in
frozen_problem.py (SLOT_LIMITS, VLEN, and the alu/valu/load/store/flow ops).
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "charts" / "cpu_diagram.svg"

VLEN = 8
PEAK_SLOTS = 12 + 6 + 2 + 2 + 1            # 23 issue slots / cycle
PEAK_ELEMENT_OPS = 12 + 6 * VLEN + 2 + 2 + 1  # 65 element ops / cycle with SIMD

# (key, name, color, role, slots, lanes, slot_label, op_groups)
ENGINES = [
    (
        "alu", "ALU", "#2563eb", "Scalar integer & comparison", 12, 1,
        "12 slots / cycle",
        [["+", "-", "*", "//", "cdiv", "%"], ["^", "&", "|", "<<", ">>"], ["<", "=="]],
    ),
    (
        "valu", "VALU", "#7c3aed", "Vector SIMD — 8-wide", 6, VLEN,
        "6 slots x 8 lanes = 48 ops",
        [["any ALU op (x8)"], ["vbroadcast", "multiply_add (FMA)"]],
    ),
    (
        "load", "LOAD", "#0f766e", "Memory reads & constants", 2, 1,
        "2 slots / cycle",
        [["load", "vload", "load_offset", "const"]],
    ),
    (
        "store", "STORE", "#dc2626", "Memory writes", 2, 1,
        "2 slots / cycle",
        [["store", "vstore"]],
    ),
    (
        "flow", "FLOW", "#f59e0b", "Control flow, select & misc", 1, 1,
        "1 slot / cycle",
        [
            ["select", "vselect", "add_imm"],
            ["jump", "jump_indirect", "cond_jump", "cond_jump_rel"],
            ["halt", "pause", "trace_write", "coreid"],
        ],
    ),
]

MONO = "Menlo, Consolas, monospace"
SANS = "Arial, sans-serif"


def _esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# Geometry ------------------------------------------------------------------ #
WIDTH = 1280
MARGIN = 56
CARD_X = MARGIN
CARD_W = WIDTH - 2 * MARGIN
STRIPE = 6
NAME_X = CARD_X + 26
NAME_W = 200
CELLS_X = CARD_X + 232
CELLS_W = 196
OPS_X = CARD_X + 452
OPS_W = CARD_X + CARD_W - 22 - OPS_X

PILL_H = 26
PILL_FS = 13
PILL_PAD = 9         # snug horizontal padding so chips hug their text
CHAR_W = 7.9         # monospace advance width at 13px
PILL_GAP = 5         # tight gap between chips
GROUP_GAP = 14
LINE_H = PILL_H + 9
CARD_GAP = 14
TOP = 150


def _pill_w(text: str) -> float:
    return len(text) * CHAR_W + 2 * PILL_PAD


def _layout_ops(groups, x0, y0, color):
    """Flow op chips left-to-right with wrapping; return (svg_parts, height)."""
    parts = []
    cx, cy = x0, y0
    for gi, ops in enumerate(groups):
        if gi > 0:
            cx += GROUP_GAP
        for op in ops:
            w = _pill_w(op)
            if cx + w > x0 + OPS_W and cx > x0:
                cx = x0
                cy += LINE_H
            parts.append(
                f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{w:.1f}" height="{PILL_H}" rx="5" '
                f'fill="#eef1f5"/>'
            )
            parts.append(
                f'<text x="{cx + w / 2:.1f}" y="{cy + PILL_H / 2 + 4.5:.1f}" text-anchor="middle" '
                f'font-family="{MONO}" font-size="{PILL_FS}" fill="#334155">{_esc(op)}</text>'
            )
            cx += w + PILL_GAP
    return parts, (cy - y0) + PILL_H


def _cells(color, slots, lanes, cx, cy_center):
    """Draw `slots` issue-slot cells, flat-filled. SIMD slots are split into
    `lanes` solid sub-bars (no overlay highlights)."""
    parts = []
    cols = min(slots, 6)
    rows = (slots + cols - 1) // cols
    cell = 22 if lanes > 1 else 20
    gap = 5
    block_h = rows * cell + (rows - 1) * gap
    x0 = cx
    y0 = cy_center - block_h / 2
    drawn = 0
    for r in range(rows):
        for c in range(cols):
            if drawn >= slots:
                break
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            if lanes > 1:  # the 8 SIMD lanes drawn as solid sub-bars
                lane_gap = 1.4
                bw = (cell - (lanes - 1) * lane_gap) / lanes
                for li in range(lanes):
                    lx = x + li * (bw + lane_gap)
                    parts.append(
                        f'<rect x="{lx:.2f}" y="{y:.1f}" width="{bw:.2f}" height="{cell}" fill="{color}"/>'
                    )
            else:
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="3" fill="{color}"/>'
                )
            drawn += 1
    return parts, block_h


def _measure_card_h(groups):
    _, ops_h = _layout_ops(groups, OPS_X, 0, "#000")
    return max(96, ops_h + 38)


def write_svg(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    card_heights = [_measure_card_h(e[7]) for e in ENGINES]
    total_cards = sum(card_heights) + CARD_GAP * (len(ENGINES) - 1)
    height = TOP + total_cards + 48

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" viewBox="0 0 {WIDTH} {height:.0f}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="{MARGIN}" y="52" font-family="{SANS}" font-size="29" font-weight="700" fill="#0f172a">Target Machine: One VLIW + SIMD Core</text>',
        f'<text x="{MARGIN}" y="82" font-family="{SANS}" font-size="15" fill="#475569">Every cycle, one instruction issues all five engines in parallel · VLEN = 8 · 32-bit words · 1,536-word scratch</text>',
        # Peak callout (top-right).
        f'<text x="{WIDTH - MARGIN:.0f}" y="44" text-anchor="end" font-family="{SANS}" font-size="13" fill="#475569">peak throughput</text>',
        f'<text x="{WIDTH - MARGIN:.0f}" y="78" text-anchor="end" font-family="{SANS}" font-size="30" font-weight="700" fill="#0f766e">{PEAK_SLOTS} slots / cycle</text>',
        f'<text x="{WIDTH - MARGIN:.0f}" y="98" text-anchor="end" font-family="{SANS}" font-size="12" fill="#94a3b8">up to {PEAK_ELEMENT_OPS} element ops with SIMD</text>',
        # Column captions above the cards.
        f'<text x="{CELLS_X}" y="{TOP - 14}" font-family="{SANS}" font-size="11" font-weight="700" fill="#94a3b8">ISSUE SLOTS / CYCLE</text>',
        f'<text x="{OPS_X}" y="{TOP - 14}" font-family="{SANS}" font-size="11" font-weight="700" fill="#94a3b8">INSTRUCTION SET</text>',
    ]

    # Left brace spanning all cards: "one VLIW bundle / cycle".
    by0 = TOP
    by1 = TOP + total_cards
    bx = CARD_X - 22
    parts.extend(
        [
            f'<path d="M {bx + 8:.1f} {by0:.1f} H {bx:.1f} V {by1:.1f} H {bx + 8:.1f}" fill="none" stroke="#cbd5e1" stroke-width="1.5"/>',
            f'<text x="{bx - 6:.1f}" y="{(by0 + by1) / 2:.1f}" transform="rotate(-90 {bx - 6:.1f} {(by0 + by1) / 2:.1f})" '
            f'text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="700" fill="#64748b">one VLIW bundle / cycle</text>',
        ]
    )

    y = TOP
    for (key, name, color, role, slots, lanes, slot_label, groups), card_h in zip(ENGINES, card_heights):
        cy = y + card_h / 2
        # Card background + colored stripe.
        parts.append(
            f'<rect x="{CARD_X}" y="{y:.1f}" width="{CARD_W}" height="{card_h:.1f}" rx="11" fill="#ffffff" stroke="#e6eaf0" stroke-width="1.2"/>'
        )
        # Name block.
        parts.extend(
            [
                f'<text x="{NAME_X}" y="{cy - 14:.1f}" font-family="{SANS}" font-size="23" font-weight="700" fill="{color}">{name}</text>',
                f'<text x="{NAME_X}" y="{cy + 6:.1f}" font-family="{SANS}" font-size="12.5" fill="#475569">{_esc(role)}</text>',
                f'<text x="{NAME_X}" y="{cy + 25:.1f}" font-family="{SANS}" font-size="12.5" font-weight="700" fill="{color}">{_esc(slot_label)}</text>',
            ]
        )
        # Slot cells.
        cell_parts, _ = _cells(color, slots, lanes, CELLS_X, cy)
        parts.extend(cell_parts)
        # Op chips, vertically centered.
        _, ops_h = _layout_ops(groups, OPS_X, 0, color)
        op_parts, _ = _layout_ops(groups, OPS_X, cy - ops_h / 2, color)
        parts.extend(op_parts)

        y += card_h + CARD_GAP

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def main():
    print(write_svg())


if __name__ == "__main__":
    main()
