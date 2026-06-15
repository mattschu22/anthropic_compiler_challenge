"""Round-unrolling diagram: rolled generic loop -> unrolled fixed schedule.

Left: the generic loop, which each round recomputes depth (r % 11), reloads the
memory layout from the header, and branches on leaf vs. non-leaf.

Right: the unrolled 16-step schedule. depth = r % (forest_height + 1) with
forest_height = 10, so the 16 rounds have the known depth sequence
0..10, 0..4 -- one full root->leaf descent plus a partial second descent.
Memory-layout pointers become compile-time constants (10/16/256 workload):
forest_values @ 7, indices @ 7+2047 = 2054, values @ 2054+256 = 2310.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "charts" / "unroll_diagram.svg"

FOREST_HEIGHT = 10
ROUNDS = 16
DEPTHS = [r % (FOREST_HEIGHT + 1) for r in range(ROUNDS)]  # 0..10, 0..4

SANS = "Arial, sans-serif"
MONO = "Menlo, Consolas, 'DejaVu Sans Mono', monospace"

DARK = (30, 64, 175)     # #1e40af  (root, depth 0)
LIGHT = (191, 219, 254)  # #bfdbfe  (leaf, depth 10)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _depth_fill(d: int) -> str:
    t = d / FOREST_HEIGHT
    r = round(DARK[0] + (LIGHT[0] - DARK[0]) * t)
    g = round(DARK[1] + (LIGHT[1] - DARK[1]) * t)
    b = round(DARK[2] + (LIGHT[2] - DARK[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _depth_text(d: int) -> str:
    return "#ffffff" if d / FOREST_HEIGHT < 0.5 else "#1e3a8a"


def write_svg(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1340, 446

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="56" y="50" font-family="{SANS}" font-size="28" font-weight="700" fill="#0f172a">Round Unrolling: Expose the Fixed Depth Sequence</text>',
        f'<text x="56" y="80" font-family="{SANS}" font-size="15" fill="#475569">16 rounds over a height-10 tree (depth = r % 11) compile to a constant, branch-free schedule</text>',
        '<defs><marker id="ar" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#334155"/></marker>'
        '<marker id="arw" markerWidth="9" markerHeight="9" refX="6.5" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#b45309"/></marker></defs>',
    ]

    # ---- Left panel: rolled generic loop ---------------------------------- #
    lx, ly, lw, lh = 56, 132, 470, 280
    parts.extend(
        [
            f'<text x="{lx}" y="{ly - 12}" font-family="{SANS}" font-size="13" font-weight="700" fill="#94a3b8">GENERIC LOOP · runtime checks</text>',
            f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="11" fill="#ffffff" stroke="#e6eaf0" stroke-width="1.2"/>',
        ]
    )
    code_x = lx + 28
    code_lines = [
        ("for r in range(16):", None),
        ("    depth = r % 11", "runtime %"),
        ("    fp, ip, vp = header(mem)", "layout load"),
        ("    if depth == 10:  reset", "branch / round"),
        ("    else:            descend", None),
    ]
    cy = ly + 52
    tag_x = lx + lw - 132
    for text, tag in code_lines:
        parts.append(
            f'<text x="{code_x}" y="{cy:.0f}" font-family="{MONO}" font-size="14" fill="#1f2328" xml:space="preserve">{_esc(text)}</text>'
        )
        if tag:
            parts.extend(
                [
                    f'<rect x="{tag_x}" y="{cy - 14:.0f}" width="116" height="20" rx="5" fill="#fee2e2"/>',
                    f'<text x="{tag_x + 58}" y="{cy:.0f}" text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="700" fill="#b91c1c">{_esc(tag)}</text>',
                ]
            )
        cy += 34
    # loop-back arrow on the far left of the box
    ax = lx + 12
    parts.append(
        f'<path d="M {ax} {ly + 64} q -10 0 -10 12 v 120 q 0 12 10 12" fill="none" stroke="#94a3b8" stroke-width="1.6" marker-end="url(#ar)"/>'
    )
    parts.append(
        f'<text x="{lx + 16}" y="{ly + 250:.0f}" font-family="{SANS}" font-size="12" fill="#64748b">repeated every round — work the compiler can do once</text>'
    )

    # ---- Center unroll arrow --------------------------------------------- #
    mid_y = ly + lh / 2
    parts.extend(
        [
            f'<line x1="{lx + lw + 12}" y1="{mid_y}" x2="{lx + lw + 60}" y2="{mid_y}" stroke="#334155" stroke-width="2.4" marker-end="url(#ar)"/>',
            f'<text x="{lx + lw + 38}" y="{mid_y - 12:.0f}" text-anchor="middle" font-family="{SANS}" font-size="13" font-weight="700" fill="#334155">unroll</text>',
        ]
    )

    # ---- Right panel: unrolled fixed schedule ---------------------------- #
    rx, rw = 600, width - 56 - 600
    ry, rh = ly, lh
    parts.extend(
        [
            f'<text x="{rx}" y="{ry - 12}" font-family="{SANS}" font-size="13" font-weight="700" fill="#94a3b8">UNROLLED · 16 fixed steps</text>',
            f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="11" fill="#ffffff" stroke="#e6eaf0" stroke-width="1.2"/>',
        ]
    )

    # depth strip
    cell_w, cell_h, gap, wrap_gap = 33, 48, 5, 16
    strip_x0 = rx + 26
    strip_y = ry + 92
    xs = []
    x = strip_x0
    for i in range(ROUNDS):
        if i == FOREST_HEIGHT + 1:  # extra gap at the wrap (after depth 10)
            x += wrap_gap
        xs.append(x)
        x += cell_w + gap

    parts.append(
        f'<text x="{strip_x0}" y="{strip_y - 30:.0f}" font-family="{SANS}" font-size="12" font-weight="700" fill="#64748b">step depth (precomputed)</text>'
    )

    for i, d in enumerate(DEPTHS):
        cx = xs[i]
        fill = _depth_fill(d)
        leaf = d == FOREST_HEIGHT
        stroke = ' stroke="#f59e0b" stroke-width="2.4"' if leaf else ' stroke="#ffffff" stroke-width="1"'
        parts.append(
            f'<rect x="{cx:.0f}" y="{strip_y}" width="{cell_w}" height="{cell_h}" rx="4" fill="{fill}"{stroke}/>'
        )
        parts.append(
            f'<text x="{cx + cell_w / 2:.0f}" y="{strip_y + cell_h / 2 + 6:.0f}" text-anchor="middle" font-family="{SANS}" font-size="16" font-weight="700" fill="{_depth_text(d)}">{d}</text>'
        )
        parts.append(
            f'<text x="{cx + cell_w / 2:.0f}" y="{strip_y + cell_h + 16:.0f}" text-anchor="middle" font-family="{MONO}" font-size="10.5" fill="#94a3b8">r{i}</text>'
        )

    # leaf-reset label on the depth-10 cell
    leaf_i = FOREST_HEIGHT
    parts.append(
        f'<text x="{xs[leaf_i] + cell_w / 2:.0f}" y="{strip_y - 10:.0f}" text-anchor="middle" font-family="{SANS}" font-size="10.5" font-weight="700" fill="#b45309">leaf · reset</text>'
    )
    # wrap arrow from depth-10 cell to the next depth-0 cell
    x_from = xs[leaf_i] + cell_w
    x_to = xs[leaf_i + 1]
    arc_y = strip_y + cell_h + 30
    parts.append(
        f'<path d="M {x_from:.0f} {strip_y + cell_h - 6} q {wrap_gap + 6} 18 {(x_to - x_from):.0f} 0" fill="none" stroke="#b45309" stroke-width="1.6" marker-end="url(#arw)"/>'
    )
    parts.append(
        f'<text x="{(x_from + x_to) / 2:.0f}" y="{arc_y + 8:.0f}" text-anchor="middle" font-family="{SANS}" font-size="10.5" fill="#b45309">wrap</text>'
    )

    # pass brackets above the strip
    def bracket(i0, i1, label):
        bx0 = xs[i0]
        bx1 = xs[i1] + cell_w
        by = strip_y - 50
        return [
            f'<path d="M {bx0:.0f} {by + 8} V {by} H {bx1:.0f} V {by + 8}" fill="none" stroke="#cbd5e1" stroke-width="1.3"/>',
            f'<text x="{(bx0 + bx1) / 2:.0f}" y="{by - 5:.0f}" text-anchor="middle" font-family="{SANS}" font-size="11" font-weight="700" fill="#64748b">{_esc(label)}</text>',
        ]

    parts.extend(bracket(0, FOREST_HEIGHT, "full descent: root → leaf"))
    parts.extend(bracket(FOREST_HEIGHT + 1, ROUNDS - 1, "partial second descent"))

    # baked-in memory layout
    by = strip_y + cell_h + 70
    parts.append(
        f'<text x="{strip_x0}" y="{by:.0f}" font-family="{SANS}" font-size="13" font-weight="700" fill="#0f766e">Memory layout baked in (constants, no header reads):</text>'
    )
    chips = ["forest_values @ 7", "indices @ 2054", "values @ 2310"]
    chx = strip_x0
    chy = by + 14
    for c in chips:
        w = len(c) * 7.6 + 22
        parts.extend(
            [
                f'<rect x="{chx:.0f}" y="{chy:.0f}" width="{w:.0f}" height="26" rx="5" fill="#ecfdf5" stroke="#0f766e" stroke-opacity="0.4"/>',
                f'<text x="{chx + w / 2:.0f}" y="{chy + 17:.0f}" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="#0f766e">{_esc(c)}</text>',
            ]
        )
        chx += w + 12

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def main():
    print(write_svg())


if __name__ == "__main__":
    main()
