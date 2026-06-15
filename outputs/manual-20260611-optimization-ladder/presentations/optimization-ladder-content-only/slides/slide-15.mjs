import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide15(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Next Steps");
  addSubtitle(slide, ctx, "Turn the one-kernel optimization into a more systematic compiler pipeline.");
  addBullets(slide, ctx, [
    "Register coloring: use liveness analysis to assign scratch locations systematically and reduce false dependencies.",
    "Goodput calculator: compute useful work per cycle, engine utilization, idle slots, memory pressure, and stall categories directly from traces.",
    "Profiler/tooling automation: automatically identify bubbles, saturated engines, load/store bottlenecks, and before/after deltas.",
    "Automated schedule search: explore scheduler priorities, tie-breaks, and packing choices programmatically.",
    "Formalized dependency model: represent every instruction as a graph node with explicit reads, writes, engine constraints, and RAW/WAR/WAW edges. Use the graph to prove schedule correctness and search for better VLIW packing."
  ], 70, 150, 1060, 16, 56);
  addPlaceholder(slide, ctx, "PowerPoint diagram: compiler pipeline roadmap: trace metrics -> dependency graph -> register coloring -> scheduler search -> verified VLIW program.");
  return slide;
}
