import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Specialization: Make The Fixed Workload Explicit");
  addCycleBadge(slide, ctx, "Current: 97,040 cycles");
  addSubtitle(slide, ctx, "Known benchmark shape lets the generated program remove general-purpose control and layout handling.");
  addBullets(slide, ctx, [
    "Stage 2, specialized fixed layout: 114,868 -> 110,898 cycles.",
    "Stable memory pointers and workload dimensions become constants instead of runtime setup.",
    "Stage 3, round unrolling: 110,898 -> 97,040 cycles.",
    "The kernel emits the exact operation stream for all 16 known rounds instead of a runtime loop.",
    "The deterministic depth sequence exposes known leaf reset behavior.",
    "Tradeoff: instruction file size grows, but the benchmark scores execution cycles."
  ]);
  addPlaceholder(slide, ctx, "PowerPoint diagram: specialization comparison. Left side generic loop with runtime layout/depth checks; right side fixed 16-step strip showing depths 0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4 and baked-in memory layout.");
  return slide;
}
