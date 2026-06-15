import { addTitle, addSubtitle, addBullets } from "./common.mjs";

export async function slide14(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Limitations");
  addSubtitle(slide, ctx, "The final kernel is fast because it is intentionally specialized; that creates real engineering tradeoffs.");
  addBullets(slide, ctx, [
    "Highly specialized workload: the generated kernel assumes forest_height = 10, rounds = 16, batch_size = 256, and a stable memory layout.",
    "Generated code size increases: unrolling and specialization remove runtime overhead but produce a larger instruction stream.",
    "Scheduler is heuristic: it uses dependency analysis and priority rules, but it is not an optimal solver.",
    "Scratch allocation is manually tuned: temp banks expose parallelism, but the current allocator is not a full liveness-aware register coloring pass.",
    "Profiler interpretation is still manual: Perfetto traces guided the optimization path, but bottleneck classification and goodput metrics are not fully automated."
  ], 70, 150, 1060, 16, 52);
  return slide;
}
