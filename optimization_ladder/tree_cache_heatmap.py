"""Why tree caching (stage 6) works: reuse is top-heavy.

A complete binary tree of depth 10 (2,047 nodes). Every one of the 256 inputs
walks one node per level, so a node at depth d is traversed by 256 / 2**d
inputs. Reuse therefore halves at every level: 256x at the root, down to <1x at
the leaves. Stage 6 caches exactly the top three levels (7 nodes, the hottest
0.34% of the tree) and turns those shallow memory gathers into register-level
vector selects. This chart heat-maps that reuse onto the tree.

Grounded in optimization_ladder/builders.py:
    cached_node_count = 7   (depths 0,1,2)
    gather -> vselect for depth <= 2
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "charts" / "tree_cache_heatmap.svg"

DEPTH = 10            # forest_height
INPUTS = 256          # batch_size
CACHED_DEPTH = 2      # depths 0..2 are cached (7 nodes)
TOTAL_NODES = 2 ** (DEPTH + 1) - 1
CACHED_NODES = 2 ** (CACHED_DEPTH + 1) - 1

# YlOrRd sequential heat ramp (cold pale yellow -> hot dark red).
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
    return f"#{_RAMP[-1][1][0]:02x}{_RAMP[-1][1][1]:02x}{_RAMP[-1][1][2]:02x}"


def _reuse(d: int) -> float:
    """Inputs traversing each node at depth d (per tree pass)."""
    return INPUTS / (2 ** d)


def _t(d: int) -> float:
    """Normalised heat: log2(reuse) over [0, 8]."""
    import math

    return max(0.0, min(1.0, math.log2(_reuse(d)) / 8.0)) if _reuse(d) > 0 else 0.0


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_svg(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1232, 838

    tree_left, tree_right = 60, 1018
    usable = tree_right - tree_left
    tree_top, tree_bottom = 156, 742
    level_h = (tree_bottom - tree_top) / DEPTH

    def node_x(d: int, i: int) -> float:
        return tree_left + usable * (i + 0.5) / (2 ** d)

    def node_y(d: int) -> float:
        return tree_top + d * level_h

    def radius(d: int) -> float:
        return max(0.5, min(13.0, 0.45 * usable / (2 ** d)))

    y_cut = node_y(CACHED_DEPTH) + level_h / 2  # between cached and gathered

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="36" y="48" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#111827">Tree Caching: Reuse Concentrates at Shallow Depths</text>',
        f'<text x="36" y="78" font-family="Arial, sans-serif" font-size="15" fill="#475569">Depth {DEPTH} · heat = inputs traversing each node · reuse halves every level deeper</text>',
    ]

    # Shade the cached region behind the tree.
    parts.append(
        f'<rect x="{tree_left - 40:.1f}" y="{tree_top - 34:.1f}" width="{usable + 80:.1f}" height="{y_cut - (tree_top - 34):.1f}" fill="#0f766e" opacity="0.07"/>'
    )

    # Edges (structure only) for the levels where they are visible.
    for d in range(0, 7):
        opacity = max(0.05, 0.42 - d * 0.06)
        w = max(0.3, min(1.8, radius(d + 1) * 0.35))
        for i in range(2 ** d):
            px, py = node_x(d, i), node_y(d)
            for child in (2 * i, 2 * i + 1):
                cx, cy = node_x(d + 1, child), node_y(d + 1)
                parts.append(
                    f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{cx:.1f}" y2="{cy:.1f}" stroke="#94a3b8" stroke-width="{w:.2f}" opacity="{opacity:.2f}"/>'
                )

    # Nodes, deepest first so the hot shallow nodes draw on top.
    for d in range(DEPTH, -1, -1):
        color = _heat_color(_t(d))
        r = radius(d)
        stroke = ' stroke="#ffffff" stroke-width="1.2"' if r >= 6 else ""
        y = node_y(d)
        count = 2 ** d
        # Past depth 8 nodes are sub-pixel; draw a thin heat band instead of
        # thousands of invisible circles.
        if count > 256:
            parts.append(
                f'<rect x="{tree_left:.1f}" y="{y - 2.5:.1f}" width="{usable:.1f}" height="5" rx="2" fill="{color}" stroke="#f0c000" stroke-width="0.6" opacity="0.95"/>'
            )
            continue
        for i in range(count):
            parts.append(
                f'<circle cx="{node_x(d, i):.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{color}"{stroke}/>'
            )

    # Cache cut line + region labels.
    parts.extend(
        [
            f'<line x1="{tree_left - 40:.1f}" y1="{y_cut:.1f}" x2="{tree_right + 40:.1f}" y2="{y_cut:.1f}" stroke="#0f766e" stroke-width="2" stroke-dasharray="8 5"/>',
            # Cached badge (upper-left, above the cut, in open space).
            f'<rect x="{tree_left - 40:.1f}" y="{tree_top - 30:.1f}" width="288" height="48" rx="6" fill="#ffffff" stroke="#0f766e" stroke-width="1.5"/>',
            f'<text x="{tree_left - 26:.1f}" y="{tree_top - 9:.1f}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#0f766e">CACHED · depths 0–2 · {CACHED_NODES} nodes</text>',
            f'<text x="{tree_left - 26:.1f}" y="{tree_top + 9:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#334155">shallow gathers become register vector selects</text>',
            # Gathered label just below the cut.
            f'<text x="{tree_left - 40:.1f}" y="{y_cut + 20:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#64748b">GATHERED from memory · depths 3–{DEPTH} · {TOTAL_NODES - CACHED_NODES:,} nodes</text>',
        ]
    )

    # Per-level reuse annotations down the right margin.
    parts.append(
        f'<text x="{tree_right + 30:.1f}" y="{tree_top - 22:.1f}" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#64748b">DEPTH · NODES · REUSE</text>'
    )
    for d in range(DEPTH + 1):
        y = node_y(d)
        color = _heat_color(_t(d))
        reuse = _reuse(d)
        reuse_str = f"{int(reuse):,}× reuse" if reuse >= 1 else "&lt;1× (cold)"
        parts.extend(
            [
                f'<circle cx="{tree_right + 36:.1f}" cy="{y:.1f}" r="6" fill="{color}" stroke="#ffffff" stroke-width="1"/>',
                f'<text x="{tree_right + 50:.1f}" y="{y + 4:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#111827">d{d} · {2 ** d:,} · {reuse_str}</text>',
            ]
        )

    # Summary callout (upper-right open space).
    bx, by, bw, bh = 706, tree_top - 30, 300, 66
    parts.extend(
        [
            f'<rect x="{bx}" y="{by:.1f}" width="{bw}" height="{bh}" rx="6" fill="#fff7ed" stroke="#f59e0b" stroke-width="1.5"/>',
            f'<text x="{bx + 14}" y="{by + 22:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#9a3412">7 nodes = 0.34% of the tree …</text>',
            f'<text x="{bx + 14}" y="{by + 40:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#7c2d12">… but they carry the three most-reused</text>',
            f'<text x="{bx + 14}" y="{by + 56:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#7c2d12">levels: 256× / 128× / 64× per node.</text>',
        ]
    )

    # Heat legend (colorbar) along the bottom.
    lx, ly, lw, lh = 60, tree_bottom + 36, 360, 16
    stops = "".join(
        f'<stop offset="{p * 100:.0f}%" stop-color="{_heat_color(p)}"/>' for p, _ in _RAMP
    )
    parts.extend(
        [
            f'<defs><linearGradient id="heat" x1="0%" y1="0%" x2="100%" y2="0%">{stops}</linearGradient></defs>',
            f'<text x="{lx}" y="{ly - 8}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">Computation per node = inputs traversing it</text>',
            f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="3" fill="url(#heat)" stroke="#cbd5e1"/>',
            f'<text x="{lx}" y="{ly + lh + 16}" font-family="Arial, sans-serif" font-size="11" fill="#64748b">&lt;1× (deep leaves)</text>',
            f'<text x="{lx + lw}" y="{ly + lh + 16}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#64748b">256× (root)</text>',
        ]
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def main():
    print(write_svg())


if __name__ == "__main__":
    main()
