import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Exposing Independent Work: Temporary Banks");
  addCycleBadge(slide, ctx, "Current: 8,884 cycles");
  addSubtitle(slide, ctx, "The scheduler can only pack operations that look independent in scratch/register space.");
  addBullets(slide, ctx, [
    "Stage 7, temporary banks: 11,825 -> 8,884 cycles.",
    "A fully unrolled vector program has many logically independent vector groups.",
    "If unrelated groups reuse the same scratch names, dependency analysis treats them as serialized.",
    "Multiple temporary banks give independent groups separate scratch names.",
    "This exposes more ready work before global scheduling.",
    "Stage 7 does local packing, but it is not yet the full global VLIW scheduler."
  ]);
  addPlaceholder(slide, ctx, "PowerPoint diagram: false-dependency before/after. Before shows independent vector groups serialized through the same temp names; after shows multiple temp banks exposing parallel lanes of ready work.");
  return slide;
}
