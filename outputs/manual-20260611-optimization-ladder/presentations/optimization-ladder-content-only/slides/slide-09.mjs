import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Leveraging SIMD: 256 Scalar Walks Become 32 Vector Groups");
  addCycleBadge(slide, ctx, "Current: 12,285 cycles");
  addSubtitle(slide, ctx, "Vectorization is the first structural change that dramatically changes the cycle curve.");
  addBullets(slide, ctx, [
    "Stage 4, vectorization: 97,040 -> 12,285 cycles.",
    "SIMD vector width is 8.",
    "batch_size = 256, so the kernel processes 32 vector groups.",
    "The hash pipeline, value update, branch-bit calculation, and many index updates operate lane-wise.",
    "The trace shifts from scalar bookkeeping toward the VALU engine as the main workhorse.",
    "Narrative role: this is where the program stops acting like 256 scalar traversals and starts acting like a vector kernel."
  ]);
  addPlaceholder(slide, ctx, "PowerPoint diagram: SIMD batching. Eight scalar inputs collapse into one 8-lane vector group; 256 inputs become 32 vector groups; show value/hash/index operations applied lane-wise.");
  return slide;
}
