"""Dependency scheduling diagram: DAG -> packed schedule, bounded by the
critical path.

Left: a small but faithful slice of one vectorized tree-walk step as a data
dependency graph. Edges are typed:
  RAW (true)   -- reader needs the writer's value; the only edges that extend
                  the critical path.
  WAR (anti)   -- a later write must wait for an earlier read of the same slot.
  WAW (output) -- two writes to the same slot must keep order.
The critical path (longest RAW chain) is highlighted.

Right: the same ops packed into a VLIW schedule (cycles x engines). Independent
ops fill different engine slots in the same cycle; the critical path threads
down the table and sets the 5-cycle floor. WAR/WAW constrain packing order, and
the final tuning checkpoint later relaxes safe WAR timing to pack tighter.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "charts" / "scheduler_diagram.svg"

SANS = "Arial, sans-serif"
MONO = "Menlo, Consolas, 'DejaVu Sans Mono', monospace"

EC = {
    "alu": "#2563eb",
    "valu": "#7c3aed",
    "load": "#0f766e",
    "store": "#dc2626",
    "flow": "#f59e0b",
}
ENGINE_ORDER = [("alu", "ALU"), ("valu", "VALU"), ("load", "LOAD"),
                ("store", "STORE"), ("flow", "FLOW")]

CRIT = "#0f172a"
RAW = "#64748b"
WAR = "#ea580c"
WAW = "#0891b2"

# id: (cx, cy, label, engine)
NODES = {
    "A": (118, 212, "load n", "load"),
    "B": (268, 212, "load x", "load"),
    "K": (500, 212, "q + 8", "alu"),
    "C": (268, 290, "t = x^n", "valu"),
    "D": (268, 368, "h = hash t", "valu"),
    "E": (150, 446, "p = h&1", "valu"),
    "G": (300, 446, "store h", "store"),
    "H": (470, 446, "t = x+n", "valu"),
    "F": (150, 524, "sel child", "flow"),
    "I": (470, 524, "h = t*2", "valu"),
}
CRIT_OPS = {"A", "C", "D", "E", "F"}

# (src, dst, kind)
EDGES = [
    ("A", "C", "crit"), ("B", "C", "raw"),
    ("C", "D", "crit"),
    ("D", "E", "crit"), ("D", "G", "raw"),
    ("E", "F", "crit"),
    ("H", "I", "raw"),
    ("D", "H", "war"), ("G", "I", "war"),
    ("C", "H", "waw"), ("D", "I", "waw"),
]

NW, NH = 102, 36  # node box

# schedule[(cycle, engine)] = [op ids]
SCHEDULE = {
    (1, "load"): ["A", "B"], (1, "alu"): ["K"],
    (2, "valu"): ["C"],
    (3, "valu"): ["D"],
    (4, "valu"): ["E", "H"], (4, "store"): ["G"],
    (5, "valu"): ["I"], (5, "flow"): ["F"],
}
# (cycle, engine) the critical op threads through
CRIT_CELLS = [(1, "load"), (2, "valu"), (3, "valu"), (4, "valu"), (5, "flow")]


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_svg(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 600, 622

    defs = ['<defs>']
    for mid, col in (("crit", CRIT), ("raw", RAW), ("war", WAR), ("waw", WAW)):
        defs.append(
            f'<marker id="m_{mid}" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
            f'<path d="M0,0 L7,3 L0,6 Z" fill="{col}"/></marker>'
        )
    defs.append("</defs>")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        "".join(defs),
        f'<text x="40" y="46" font-family="{SANS}" font-size="25" font-weight="700" fill="#0f172a">Dependency Scheduling: the Critical Path</text>',
        f'<text x="40" y="74" font-family="{SANS}" font-size="15" fill="#475569">Only RAW edges extend the critical path that sets the cycle floor</text>',
    ]

    # ---- Left: dependency graph ------------------------------------------ #
    parts.append(f'<text x="40" y="118" font-family="{SANS}" font-size="13" font-weight="700" fill="#94a3b8">DEPENDENCY GRAPH</text>')

    # hazard legend
    lx = 40
    leg = [("crit", CRIT, "critical path (RAW)"), ("raw", RAW, "RAW (true)"),
           ("war", WAR, "WAR (anti)"), ("waw", WAW, "WAW (output)")]
    lxc = lx
    for kind, col, label in leg:
        dash = ' stroke-dasharray="5 3"' if kind == "war" else (' stroke-dasharray="1 4"' if kind == "waw" else "")
        wsv = 3 if kind == "crit" else 1.8
        parts.append(f'<line x1="{lxc}" y1="134" x2="{lxc + 26}" y2="134" stroke="{col}" stroke-width="{wsv}"{dash}/>')
        parts.append(f'<text x="{lxc + 32}" y="138" font-family="{SANS}" font-size="11.5" fill="#475569">{_esc(label)}</text>')
        lxc += 36 + len(label) * 6.6 + 18

    def n_top(nid):
        cx, cy, *_ = NODES[nid]
        return cx, cy - NH / 2

    def n_bot(nid):
        cx, cy, *_ = NODES[nid]
        return cx, cy + NH / 2

    # edges (under nodes); flow downward so attach source-bottom -> target-top
    for src, dst, kind in EDGES:
        sx, sy = n_bot(src)
        tx, ty = n_top(dst)
        if kind == "crit":
            col, wsv, dash = CRIT, 3, ""
        elif kind == "raw":
            col, wsv, dash = RAW, 1.8, ""
        elif kind == "war":
            col, wsv, dash = WAR, 1.8, ' stroke-dasharray="5 3"'
        else:
            col, wsv, dash = WAW, 1.8, ' stroke-dasharray="1 4"'
        parts.append(
            f'<line x1="{sx:.0f}" y1="{sy:.0f}" x2="{tx:.0f}" y2="{ty - 2:.0f}" stroke="{col}" stroke-width="{wsv}"{dash} marker-end="url(#m_{kind})"/>'
        )

    # nodes
    for nid, (cx, cy, label, eng) in NODES.items():
        col = EC[eng]
        x = cx - NW / 2
        y = cy - NH / 2
        if nid in CRIT_OPS:
            parts.append(f'<rect x="{x - 3:.0f}" y="{y - 3:.0f}" width="{NW + 6}" height="{NH + 6}" rx="9" fill="none" stroke="{CRIT}" stroke-width="2.5"/>')
        parts.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{NW}" height="{NH}" rx="7" fill="#ffffff" stroke="{col}" stroke-width="2"/>')
        parts.append(f'<text x="{cx:.0f}" y="{cy - 3:.0f}" text-anchor="middle" font-family="{MONO}" font-size="12" fill="#1f2937">{_esc(label)}</text>')
        parts.append(f'<text x="{cx:.0f}" y="{cy + 11:.0f}" text-anchor="middle" font-family="{SANS}" font-size="8.5" font-weight="700" fill="{col}">{eng.upper()}</text>')

    # ---- annotation under the graph ------------------------------------- #
    ay = 580
    parts.extend(
        [
            f'<text x="40" y="{ay}" font-family="{SANS}" font-size="14" font-weight="700" fill="#0f172a">Critical chain is 5 deep → 5-cycle floor.</text>',
            f'<text x="40" y="{ay + 20}" font-family="{SANS}" font-size="13" fill="#475569">RAW sets the floor; WAR/WAW constrain order. Stage 10 relaxes WAR (zero-latency).</text>',
        ]
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def main():
    print(write_svg())


if __name__ == "__main__":
    main()
