"""Tree-cache reuse heatmap, weighted by the real 16-round schedule.

Companion to tree_cache_heatmap.py. That chart shows reuse for a single
root->leaf pass (clean halving). This one weights each node by how often the
whole run actually touches it.

The 16 rounds step depth = round % (forest_height + 1) = round % 11, so the
sequence is depths 0..10 (rounds 0-10) then 0..4 again (rounds 11-15). Depths
0-4 are therefore traversed twice and 5-10 once, which puts a 4x drop (not 2x)
between depth 4 and depth 5 -- the "kink". Total accesses per node:

    total(d) = (256 / 2**d) * (2 if d <= 4 else 1)
             = 512, 256, 128, 64, 32 | 8, 4, 2, 1, <1, <1

Grounded in optimization_ladder/builders.py (depth = r % (forest_height + 1);
cached_node_count = 7; gather -> vselect for depth <= 2).
"""

from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "charts" / "tree_cache_heatmap_rounds.svg"

DEPTH = 10
INPUTS = 256
ROUNDS = 16
CACHED_DEPTH = 2
REVISIT_MAX_DEPTH = ROUNDS - (DEPTH + 1) - 1  # depths 0..4 get a second pass
TOTAL_NODES = 2 ** (DEPTH + 1) - 1
CACHED_NODES = 2 ** (CACHED_DEPTH + 1) - 1

_RAMP = [
    (0.00, (255, 255, 204)),
    (0.25, (254, 217, 118)),
    (0.50, (253, 141, 60)),
    (0.75, (240, 59, 32)),
    (1.00, (189, 0, 38)),
]


def _heat_color(t: float) -> str:
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(_RAMP, _RAMP[1:]):
        if t <= p1:
            f = 0 if p1 == p0 else (t - p0) / (p1 - p0)
            r = round(c0[0] + (c1[0] - c0[0]) * f)
            g = round(c0[1] + (c1[1] - c0[1]) * f)
            b = round(c0[2] + (c1[2] - c0[2]) * f)
            return f"#{r:02x}{g:02x}{b:02x}"
    c = _RAMP[-1][1]
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def _visits(d: int) -> int:
    return 2 if d <= REVISIT_MAX_DEPTH else 1


def _total(d: int) -> float:
    """Total inputs traversing each node at depth d across all 16 rounds."""
    return (INPUTS / (2 ** d)) * _visits(d)


def _t(d: int) -> float:
    tot = _total(d)
    return max(0.0, min(1.0, math.log2(tot) / 9.0)) if tot > 0 else 0.0


DRAWN_DEPTH = 4   # depths 0..4 drawn explicitly; 5..10 collapsed into glyphs
NODE_R = {0: 27, 1: 23, 2: 19, 3: 15, 4: 11}


def write_svg(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1150, 812

    left, right = 132, 968
    usable = right - left
    tree_top = 168
    dy = 78
    baseline_y = 690

    def node_x(d, i):
        return left + usable * (i + 0.5) / (2 ** d)

    def node_y(d):
        return tree_top + d * dy

    y_cut = node_y(CACHED_DEPTH) + dy / 2          # cached / gathered boundary
    collapsed_nodes = TOTAL_NODES - (2 ** (DRAWN_DEPTH + 1) - 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="44" y="52" font-family="Arial, sans-serif" font-size="29" font-weight="700" fill="#0f172a">Tree Caching: Node Access Frequency by Depth</text>',
        f'<text x="44" y="82" font-family="Arial, sans-serif" font-size="15" fill="#475569">Heat = inputs traversing each node over {ROUNDS} rounds · depths 0–{REVISIT_MAX_DEPTH} are traversed twice</text>',
    ]

    # Gradients: page heat ramp + the cold fill for collapsed subtrees.
    ramp_stops = "".join(
        f'<stop offset="{p * 100:.0f}%" stop-color="{_heat_color(p)}"/>' for p, _ in _RAMP
    )
    parts.append(
        "<defs>"
        f'<linearGradient id="heat" x1="0%" y1="0%" x2="100%" y2="0%">{ramp_stops}</linearGradient>'
        '<linearGradient id="cold" x1="0%" y1="0%" x2="0%" y2="100%">'
        f'<stop offset="0%" stop-color="{_heat_color(_t(DRAWN_DEPTH + 1))}"/>'
        f'<stop offset="100%" stop-color="{_heat_color(0)}"/>'
        "</linearGradient>"
        '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="1.4" stdDeviation="1.6" flood-color="#0f172a" flood-opacity="0.18"/>'
        "</filter></defs>"
    )

    # Cached region wash (behind everything).
    parts.append(
        f'<rect x="{left - 60:.1f}" y="{tree_top - 44:.1f}" width="{usable + 120:.1f}" height="{y_cut - (tree_top - 44):.1f}" rx="10" fill="#0f766e" opacity="0.06"/>'
    )

    # Collapsed cold subtrees: one heat-graded wedge under each depth-4 node.
    apex_y = node_y(DRAWN_DEPTH) + NODE_R[DRAWN_DEPTH] + 2
    half = (usable / (2 ** DRAWN_DEPTH)) * 0.46
    for i in range(2 ** DRAWN_DEPTH):
        x = node_x(DRAWN_DEPTH, i)
        parts.append(
            f'<path d="M {x:.1f} {apex_y:.1f} L {x - half:.1f} {baseline_y:.1f} '
            f'Q {x:.1f} {baseline_y + 9:.1f} {x + half:.1f} {baseline_y:.1f} Z" '
            f'fill="url(#cold)" stroke="#fcd9a0" stroke-width="0.8" opacity="0.96"/>'
        )
    # A few faint "more nodes" dot hints inside the wedges, just for texture.
    for i in range(2 ** DRAWN_DEPTH):
        x = node_x(DRAWN_DEPTH, i)
        for ry, rh in ((0.42, 0.55), (0.72, 0.78)):
            yy = apex_y + (baseline_y - apex_y) * ry
            hw = half * rh
            for k in range(3):
                dotx = x - hw + hw * k
                parts.append(
                    f'<circle cx="{dotx:.1f}" cy="{yy:.1f}" r="1.4" fill="#f59e0b" opacity="0.30"/>'
                )

    # Tree edges for the drawn portion (depths 0..3 -> 1..4).
    for d in range(DRAWN_DEPTH):
        for i in range(2 ** d):
            px, py = node_x(d, i), node_y(d)
            for child in (2 * i, 2 * i + 1):
                cx, cy = node_x(d + 1, child), node_y(d + 1)
                parts.append(
                    f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{cx:.1f}" y2="{cy:.1f}" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round"/>'
                )

    # Drawn nodes (depths 0..4), shallow last so the hot root sits on top.
    for d in range(DRAWN_DEPTH, -1, -1):
        color = _heat_color(_t(d))
        r = NODE_R[d]
        y = node_y(d)
        for i in range(2 ** d):
            parts.append(
                f'<circle cx="{node_x(d, i):.1f}" cy="{y:.1f}" r="{r}" fill="{color}" stroke="#ffffff" stroke-width="2" filter="url(#soft)"/>'
            )
        # Label per-node access count on the wide upper rows.
        if d <= 2:
            for i in range(2 ** d):
                tot = int(_total(d))
                parts.append(
                    f'<text x="{node_x(d, i):.1f}" y="{y + 4:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{11 if d == 2 else 13}" font-weight="700" fill="#ffffff">{tot}</text>'
                )

    # Root annotation.
    parts.extend(
        [
            f'<text x="{node_x(0, 0):.1f}" y="{node_y(0) - NODE_R[0] - 10:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12.5" font-weight="700" fill="#9a3412">all {INPUTS} inputs pass through the root</text>',
        ]
    )

    # Cache cut line + region labels.
    parts.extend(
        [
            f'<line x1="{left - 60:.1f}" y1="{y_cut:.1f}" x2="{right + 92:.1f}" y2="{y_cut:.1f}" stroke="#0f766e" stroke-width="2" stroke-dasharray="9 5"/>',
            f'<rect x="{left - 60:.1f}" y="{tree_top - 40:.1f}" width="300" height="50" rx="7" fill="#ffffff" stroke="#0f766e" stroke-width="1.5" filter="url(#soft)"/>',
            f'<text x="{left - 44:.1f}" y="{tree_top - 18:.1f}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#0f766e">CACHED · depths 0–2 · {CACHED_NODES} nodes</text>',
            f'<text x="{left - 44:.1f}" y="{tree_top:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#334155">shallow gathers become register vector selects</text>',
            f'<text x="{left - 60:.1f}" y="{y_cut + 21:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#64748b">GATHERED from memory · depths 3–{DEPTH}</text>',
        ]
    )

    # Bracket: depths 0..4 traversed twice.
    bx = left - 78
    yb0, yb4 = node_y(0) - 12, node_y(DRAWN_DEPTH) + 12
    parts.extend(
        [
            f'<path d="M {bx + 9:.1f} {yb0:.1f} H {bx:.1f} V {yb4:.1f} H {bx + 9:.1f}" fill="none" stroke="#9a3412" stroke-width="1.8"/>',
            f'<text x="{bx - 8:.1f}" y="{(yb0 + yb4) / 2:.1f}" transform="rotate(-90 {bx - 8:.1f} {(yb0 + yb4) / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="12.5" font-weight="700" fill="#9a3412">depths 0–{REVISIT_MAX_DEPTH} · traversed 2×</text>',
        ]
    )

    # Collapsed-region label under the wedges.
    parts.append(
        f'<text x="{left + usable / 2:.1f}" y="{baseline_y + 36:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13.5" font-weight="700" fill="#92400e">depths 5–{DEPTH}: {collapsed_nodes:,} cold nodes — always gathered</text>'
    )

    # Right-margin reuse ladder for the drawn depths.
    lxr = right + 64
    parts.append(
        f'<text x="{lxr:.1f}" y="{tree_top - 30:.1f}" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#64748b">ACCESSES / NODE</text>'
    )
    for d in range(DRAWN_DEPTH + 1):
        y = node_y(d)
        color = _heat_color(_t(d))
        tag = " ×2" if _visits(d) == 2 else ""
        parts.extend(
            [
                f'<circle cx="{lxr:.1f}" cy="{y:.1f}" r="7" fill="{color}" stroke="#ffffff" stroke-width="1.4"/>',
                f'<text x="{lxr + 16:.1f}" y="{y + 4:.1f}" font-family="Arial, sans-serif" font-size="12.5" fill="#111827">d{d}: <tspan font-weight="700">{int(_total(d)):,}</tspan>{tag}</text>',
            ]
        )
    # Halving guide down the ladder, parked clear of the node column.
    gx = lxr - 30
    parts.append(
        f'<text x="{gx:.1f}" y="{(node_y(0) + node_y(DRAWN_DEPTH)) / 2:.1f}" transform="rotate(-90 {gx:.1f} {(node_y(0) + node_y(DRAWN_DEPTH)) / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#94a3b8">halves each level ↓</text>'
    )

    # Heat legend (bottom-left).
    lx, ly, lw, lh = 44, height - 58, 320, 14
    parts.extend(
        [
            f'<text x="{lx}" y="{ly - 8}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">Accesses per node over {ROUNDS} rounds</text>',
            f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="3" fill="url(#heat)" stroke="#cbd5e1"/>',
            f'<text x="{lx}" y="{ly + lh + 15}" font-family="Arial, sans-serif" font-size="11" fill="#64748b">&lt;1 (deep leaves)</text>',
            f'<text x="{lx + lw}" y="{ly + lh + 15}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#64748b">512 (root)</text>',
        ]
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def main():
    print(write_svg())


if __name__ == "__main__":
    main()
