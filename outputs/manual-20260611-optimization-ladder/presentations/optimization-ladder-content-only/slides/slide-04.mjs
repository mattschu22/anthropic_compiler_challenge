import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Machine Model And Perfetto Tooling");
  addSubtitle(slide, ctx, "The simulator behaves like a restricted VLIW/SIMD machine with separate execution engines.");
  addBullets(slide, ctx, [
    "VLIW means multiple independent operations can issue in the same cycle if their engines have open slots.",
    "SIMD means one vector instruction applies the same operation across multiple lanes; here the vector width is 8.",
    "Engine slot limits per cycle: alu = 12, valu = 6, load = 2, store = 2, flow = 1.",
    "alu handles scalar arithmetic, comparisons, and address math.",
    "valu handles vector arithmetic across eight lanes.",
    "load/store handle memory reads and writes; flow handles control operations.",
    "Perfetto traces show engine activity over time. Dense bars mean busy slots; blank gaps are idle capacity or dependency bubbles."
  ], 70, 150, 1060, 16, 34);
  addPlaceholder(slide, ctx, "PowerPoint diagram: VLIW/SIMD machine model with one issue-packet row: 12 ALU slots, 6 VALU slots, 2 LOAD, 2 STORE, 1 FLOW; small legend explaining that Perfetto is supporting evidence.");
  return slide;
}
