import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Baseline: The Trace Shows Serialization And Waste");
  addCycleBadge(slide, ctx, "Current: 147,734 cycles");
  addSubtitle(slide, ctx, "The starting point does correct work, but leaves most available machine capacity unused.");
  addBullets(slide, ctx, [
    "Baseline cycle count: 147,734.",
    "The trace shows mostly scalar-style execution.",
    "Vector lanes are largely unused.",
    "Index state repeatedly moves through memory even though it is only needed to choose future nodes.",
    "Loop/control overhead and address recomputation occur before useful tree-walk work.",
    "Interpretation: the first goal should be removing bookkeeping and memory traffic before deep scheduling."
  ]);
  addPlaceholder(slide, ctx, "Codebase image + PowerPoint callouts: use trace_visuals/00_baseline.svg, then annotate scalar lane activity, idle VALU capacity, index memory traffic, and dependency/control bubbles. This is the main trace-reading teaching slide.");
  return slide;
}
