import { addTitle, addSubtitle, addBullets } from "./common.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Background: A Compiler Challenge, Not Python Tuning");
  addSubtitle(slide, ctx, "Python emits a low-level kernel for a simulated CPU; the score is total simulator cycles.");
  addBullets(slide, ctx, [
    "The take-home asks candidates to generate a correct kernel for a fixed workload and minimize cycle count.",
    "Correctness is checked against the reference problem; performance is measured by the simulator cycle counter.",
    "The core work is compiler work: code generation, specialization, memory placement, vectorization, dependency analysis, and scheduling.",
    "Anthropic speed thresholds in submission_tests.py: baseline, 18,532, 2,164, 1,790, 1,579, 1,548, 1,487, and 1,363 cycles.",
    "This project reaches 1,184 cycles and beats every listed speed threshold."
  ]);
  return slide;
}
