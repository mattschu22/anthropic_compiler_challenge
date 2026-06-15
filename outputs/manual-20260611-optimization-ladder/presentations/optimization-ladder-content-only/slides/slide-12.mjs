import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide12(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "A Better Scheduler: Pack Independent Ops Into VLIW Slots");
  addCycleBadge(slide, ctx, "Current: 1,184 cycles");
  addSubtitle(slide, ctx, "The final major gain comes from dependency-aware cross-engine scheduling.");
  addBullets(slide, ctx, [
    "Stage 8, VLIW scheduling: 8,884 -> 1,291 cycles.",
    "Stage 9, final refinements: 1,291 -> 1,184 cycles.",
    "The scheduler assigns every operation an engine type and read/write sets.",
    "RAW hazard: a consumer reads a value after a producer writes it.",
    "WAW hazard: two writes to the same target must stay ordered.",
    "WAR hazard: a later write must not clobber an earlier read; final refinements relax safe same-cycle WAR cases because reads happen at cycle start and writes commit at cycle end.",
    "Ready operations are prioritized by critical path and packed under engine slot limits."
  ], 70, 150, 1060, 15, 32);
  addPlaceholder(slide, ctx, "PowerPoint diagram + codebase inset: draw dependency graph with RAW/WAR/WAW edges feeding a VLIW packing table; include small trace_visuals/09_final_refinements.png inset only as proof of dense engine utilization.");
  return slide;
}
