import { addTitle, addFooter, box, colors, label } from "./common.mjs";

export async function slide15(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Next Steps", "Turn the one-kernel optimization into a more systematic compiler pipeline.", "next steps");

  const items = [
    ["Register coloring", "Use liveness analysis to assign scratch locations systematically, reducing false dependencies without hand-tuned temp-bank counts."],
    ["Goodput calculator", "Compute useful work per cycle, engine utilization, idle slots, memory pressure, and stall categories directly from traces."],
    ["Profiler/tooling automation", "Automatically identify bubbles, saturated engines, load/store bottlenecks, and before/after deltas instead of relying on visual inspection alone."],
    ["Automated schedule search", "Explore scheduler priorities, tie-breaks, and packing choices programmatically rather than hand-tuning heuristics."],
    ["Formalized dependency model", "Represent every instruction as a graph node with explicit reads, writes, engine constraints, and RAW/WAR/WAW edges. Use the graph to prove schedule correctness and search for better VLIW packing."]
  ];

  items.forEach((it, i) => {
    const y = 142 + i * 100;
    const accent = [colors.blue, colors.green, colors.amber, colors.violet, colors.rose][i];
    box(slide, ctx, { x: 68, y, w: 1050, h: 78 });
    ctx.addShape(slide, { x: 68, y, w: 8, h: 78, fill: accent, line: { fill: accent, width: 0 } });
    label(slide, ctx, it[0], 96, y + 16, 260, 24, { size: 18, bold: true, color: accent });
    label(slide, ctx, it[1], 376, y + 15, 700, 42, { size: 13.5, color: colors.ink });
  });

  addFooter(slide, ctx, 15);
  return slide;
}
