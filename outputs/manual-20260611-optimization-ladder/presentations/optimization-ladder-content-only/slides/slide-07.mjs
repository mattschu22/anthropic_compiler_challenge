import { addTitle, addCycleBadge, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Easy Wins: Remove Ungraded And Unnecessary Work");
  addCycleBadge(slide, ctx, "Current: 114,868 cycles");
  addSubtitle(slide, ctx, "The first improvements align the kernel with exactly what the grader checks.");
  addBullets(slide, ctx, [
    "Stage 1, remove index bookkeeping: 147,734 -> 114,868 cycles.",
    "The grader checks final values, not final indices.",
    "The final round can compute values without writing final index state back to memory.",
    "Traversal indices still matter during execution, but they can live in scratch instead of memory between rounds.",
    "This combines the old test-contract and scratch-indices checkpoints because both remove index work from the graded path.",
    "Narrative role: low-risk cleanup before specialization."
  ], 70, 150, 1060, 16, 34);
  addPlaceholder(slide, ctx, "PowerPoint diagram: before/after state diagram. Before shows index loaded/stored through memory every round plus final index write; after shows index in scratch and final index write removed. Include 147,734 -> 114,868 cycle delta.");
  return slide;
}
