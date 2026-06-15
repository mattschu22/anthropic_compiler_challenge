import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const ROOT = "/Users/baseb/Documents/Projects/AnthropicPerf/anthropic_compiler_challenge";
const WORKSPACE = `${ROOT}/outputs/manual-20260611-edit-slides/presentations/edit-slides`;
const SOURCE = `${ROOT}/slides/current.pptx`;
const OUT = `${ROOT}/slides/current.pptx`;
const ROOT_COPY = `${ROOT}/current.pptx`;
const ASSET = `${ROOT}/optimization_ladder/results`;
const PREVIEW_DIR = `${WORKSPACE}/preview`;
const LAYOUT_DIR = `${WORKSPACE}/layout/final`;
const CONTACT_SHEET = `${WORKSPACE}/preview/contact-sheet.png`;
const MANIFEST = `${WORKSPACE}/output/current-manifest.json`;

const C = {
  bg: "#f8fafc",
  panel: "#ffffff",
  ink: "#0f172a",
  muted: "#475569",
  faint: "#e2e8f0",
  blue: "#2563eb",
  cyan: "#0891b2",
  green: "#16a34a",
  amber: "#d97706",
  rose: "#be123c",
  violet: "#7c3aed",
  slate: "#334155",
  red: "#dc2626",
};

const engine = {
  ALU: "#2563eb",
  VALU: "#7c3aed",
  LOAD: "#0891b2",
  STORE: "#d97706",
  FLOW: "#16a34a",
};

const stages = [
  ["0", "Baseline", 147734],
  ["1", "Remove index", 114868],
  ["2", "Fixed layout", 110898],
  ["3", "Unroll", 97040],
  ["4", "Vectorize", 12285],
  ["5", "Tree cache", 11856],
  ["6", "Stream I/O", 11825],
  ["7", "Temp banks", 8884],
  ["8", "VLIW", 1291],
  ["9", "Refine", 1184],
];

function slidesFromPresentation(presentation) {
  return Array.from({ length: presentation.slides.count }, (_, index) => presentation.slides.getItem(index));
}

function pos(x, y, w, h) {
  return { left: x, top: y, width: w, height: h };
}

function line(fill = "#00000000", width = 0, style = "solid") {
  return { fill, width, style };
}

function shape(slide, { x, y, w, h, fill = C.panel, stroke = C.faint, strokeWidth = 1, geometry = "rect", name }) {
  return slide.shapes.add({
    geometry,
    name,
    position: pos(x, y, w, h),
    fill,
    line: strokeWidth ? line(stroke, strokeWidth) : line(),
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const s = shape(slide, {
    x,
    y,
    w,
    h,
    fill: opts.fill ?? "#00000000",
    stroke: opts.stroke ?? "#00000000",
    strokeWidth: opts.strokeWidth ?? 0,
    name: opts.name,
  });
  s.text = value;
  s.text.fontSize = opts.size ?? 14;
  s.text.color = opts.color ?? C.ink;
  s.text.bold = Boolean(opts.bold);
  s.text.typeface = opts.font ?? "Aptos";
  s.text.alignment = opts.align ?? "left";
  s.text.verticalAlignment = opts.valign ?? "top";
  s.text.insets = opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 };
  return s;
}

function title(slide, titleText, subtitle, kicker, n) {
  shape(slide, { x: 0, y: 0, w: 1280, h: 720, fill: C.bg, strokeWidth: 0 });
  shape(slide, { x: 0, y: 0, w: 14, h: 720, fill: C.blue, strokeWidth: 0 });
  if (kicker) text(slide, kicker.toUpperCase(), 42, 24, 420, 20, { size: 11, bold: true, color: C.blue, valign: "mid" });
  const longTitle = titleText.length > 68;
  text(slide, titleText, 42, 50, 1110, longTitle ? 68 : 54, { size: longTitle ? 24 : 27, bold: true });
  if (subtitle) text(slide, subtitle, 44, longTitle ? 124 : 108, 1000, 28, { size: 14.5, color: C.muted });
  text(slide, String(n), 1212, 681, 38, 18, { size: 10, color: "#94a3b8", align: "right" });
}

function box(slide, x, y, w, h, opts = {}) {
  return shape(slide, {
    x,
    y,
    w,
    h,
    fill: opts.fill ?? C.panel,
    stroke: opts.stroke ?? C.faint,
    strokeWidth: opts.strokeWidth ?? 1,
  });
}

function bulletList(slide, items, x, y, w, opts = {}) {
  let cy = y;
  const gap = opts.gap ?? 40;
  for (const item of items) {
    shape(slide, { x, y: cy + 7, w: 7, h: 7, fill: opts.color ?? C.blue, strokeWidth: 0 });
    text(slide, item, x + 18, cy, w - 18, gap, { size: opts.size ?? 14, color: opts.textColor ?? C.ink });
    cy += gap;
  }
}

function metric(slide, value, label, x, y, w, h, color = C.blue) {
  box(slide, x, y, w, h);
  text(slide, value, x + 14, y + 13, w - 28, 34, { size: 23, bold: true, color });
  text(slide, label, x + 14, y + 53, w - 28, h - 58, { size: 12, color: C.muted });
}

function arrow(slide, x1, y, x2, color = C.blue, thickness = 6) {
  const w = Math.max(0, x2 - x1 - 18);
  shape(slide, { x: x1, y: y - thickness / 2, w, h: thickness, fill: color, strokeWidth: 0 });
  text(slide, ">", x2 - 22, y - 16, 28, 32, { size: 26, bold: true, color, align: "center", valign: "mid" });
}

function downArrow(slide, x, y1, y2, color = C.blue, thickness = 4) {
  shape(slide, { x: x - thickness / 2, y: y1, w: thickness, h: Math.max(0, y2 - y1 - 18), fill: color, strokeWidth: 0 });
  text(slide, "v", x - 12, y2 - 22, 24, 24, { size: 18, bold: true, color, align: "center", valign: "mid" });
}

async function addImage(slide, rel, x, y, w, h, fit = "contain") {
  const bytes = await fs.readFile(`${ASSET}/${rel}`);
  const blob = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const image = slide.images.add({ blob, fit, alt: rel });
  image.position = pos(x, y, w, h);
  return image;
}

function chip(slide, value, x, y, w, color = C.blue) {
  box(slide, x, y, w, 28, { fill: "#ffffff", stroke: color, strokeWidth: 1.2 });
  text(slide, value, x + 7, y + 6, w - 14, 18, { size: 11, bold: true, color, align: "center", valign: "mid" });
}

function deltaBadge(slide, value, label, x, y, w, color = C.blue) {
  box(slide, x, y, w, 48, { fill: "#ffffff", stroke: color, strokeWidth: 1.2 });
  text(slide, value, x + 10, y + 8, w - 20, 18, { size: 15, bold: true, color, align: "center" });
  text(slide, label, x + 10, y + 28, w - 20, 14, { size: 9.5, color: C.muted, align: "center" });
}

function node(slide, label, x, y, color = C.blue, opts = {}) {
  shape(slide, { x, y, w: opts.w ?? 54, h: opts.h ?? 34, fill: opts.fill ?? "#eff6ff", stroke: color, strokeWidth: 1.2, geometry: opts.geometry ?? "rect" });
  text(slide, label, x + 4, y + 8, (opts.w ?? 54) - 8, 18, { size: opts.size ?? 11, bold: opts.bold ?? true, color: opts.textColor ?? C.ink, align: "center", valign: "mid" });
}

function clear(slide) {
  for (const element of [...slide.elements.items].reverse()) {
    if (typeof element.delete === "function") element.delete();
  }
}

function packetRow(slide, x, y, scale = 1, labelText = "") {
  if (labelText) text(slide, labelText, x, y - 24, 300, 18, { size: 11, bold: true, color: C.muted });
  let cx = x;
  const h = 24 * scale;
  const gap = 3 * scale;
  const slot = 20 * scale;
  const groups = [
    ["ALU", 12, engine.ALU],
    ["VALU", 6, engine.VALU],
    ["LOAD", 2, engine.LOAD],
    ["STORE", 2, engine.STORE],
    ["FLOW", 1, engine.FLOW],
  ];
  for (const [name, count, color] of groups) {
    for (let i = 0; i < count; i++) {
      shape(slide, { x: cx, y, w: slot, h, fill: i % 2 ? `${color}dd` : color, stroke: "#ffffff", strokeWidth: 1 });
      cx += slot + gap;
    }
    if (scale >= 0.9) text(slide, name, cx - count * (slot + gap), y + h + 6, count * (slot + gap) - gap, 16, { size: 8.5, bold: true, color, align: "center" });
    cx += 11 * scale;
  }
}

function miniSparkline(slide, x, y, w, h) {
  const max = Math.log10(stages[0][2]);
  const min = Math.log10(stages.at(-1)[2]);
  const pts = stages.map(([, , cycles], i) => {
    const px = x + (i * w) / (stages.length - 1);
    const t = (Math.log10(cycles) - min) / (max - min);
    const py = y + h - t * h;
    return [px, py, cycles];
  });
  for (let i = 0; i < pts.length - 1; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[i + 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy);
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;
    const seg = shape(slide, { x: cx - len / 2, y: cy - 1.3, w: len, h: 2.6, fill: i === 3 || i === 7 ? C.rose : C.blue, strokeWidth: 0 });
    seg.rotation = (Math.atan2(dy, dx) * 180) / Math.PI;
  }
  pts.forEach(([px, py], i) => {
    const color = i === 4 ? C.violet : i === 8 ? C.rose : C.blue;
    shape(slide, { x: px - 5, y: py - 5, w: 10, h: 10, fill: color, stroke: "#ffffff", strokeWidth: 1.4, geometry: "ellipse" });
    text(slide, stages[i][0], px - 7, y + h + 11, 14, 13, { size: 8, color: C.muted, align: "center" });
  });
}

function slide1(slide) {
  title(slide, "Profiler-guided optimization turns 147,734 cycles into 1,184.", "The win is a systematic ladder: remove work, specialize, vectorize, expose independence, then schedule the machine.", "hero metric", 1);
  text(slide, "147,734 cycles", 92, 210, 265, 60, { size: 34, bold: true, color: C.rose, align: "center" });
  arrow(slide, 374, 240, 846, C.blue, 9);
  text(slide, "1,184 cycles", 860, 210, 240, 60, { size: 34, bold: true, color: C.green, align: "center" });
  text(slide, "124.8x faster", 380, 156, 450, 60, { size: 44, bold: true, color: C.ink, align: "center" });
  text(slide, "fixed grader workload", 458, 286, 300, 24, { size: 14, color: C.muted, align: "center" });
  box(slide, 105, 386, 950, 160);
  miniSparkline(slide, 155, 420, 720, 80);
  chip(slide, "largest drop: stage 4 vectorization", 492, 514, 220, C.violet);
  chip(slide, "stage 8 VLIW scheduling", 790, 514, 180, C.rose);
  metric(slide, "10", "cumulative presentation stages", 1080, 390, 130, 86, C.blue);
  bulletList(slide, [
    "Every checkpoint is cumulative and correctness-preserving.",
    "Trace interpretation drives the next optimization, not a one-off trick.",
  ], 118, 578, 910, { size: 15, gap: 32, color: C.green });
}

function slide2(slide) {
  title(slide, "Batched binary tree traversal is a repeated value/index update.", "Each of 256 inputs walks a perfect tree for 16 rounds and must match the reference final values.", "problem", 2);
  box(slide, 48, 150, 500, 430);
  text(slide, "Perfect binary tree: depth 0 through depth 10", 70, 168, 420, 22, { size: 15, bold: true });
  const levels = [
    [[295, 214, "d0"]],
    [[210, 272, "d1"], [380, 272, "d1"]],
    [[155, 330, "d2"], [265, 330, "d2"], [345, 330, "d2"], [455, 330, "d2"]],
  ];
  const pathNodes = new Set(["295,214", "210,272", "265,330"]);
  for (let li = 0; li < levels.length; li++) {
    for (const [x, y, label] of levels[li]) {
      const hot = pathNodes.has(`${x},${y}`);
      node(slide, label, x - 22, y - 16, hot ? C.rose : C.blue, { w: 44, h: 32, fill: hot ? "#fff1f2" : "#eff6ff" });
    }
  }
  const edgePairs = [
    [295, 230, 210, 256], [295, 230, 380, 256],
    [210, 288, 155, 314], [210, 288, 265, 314],
    [380, 288, 345, 314], [380, 288, 455, 314],
  ];
  for (const [x1, y1, x2, y2] of edgePairs) {
    arrow(slide, x1, y1 + (y2 - y1) / 2, x2, pathNodes.has(`${x2},${y2 + 16}`) ? C.rose : "#94a3b8", 2);
  }
  box(slide, 120, 398, 350, 84, { fill: "#f1f5f9" });
  text(slide, "collapsed lower tree", 190, 414, 210, 18, { size: 13, bold: true, align: "center" });
  text(slide, "depths 3...10 contain the remaining nodes; the slide shows concept, not all 2,047 nodes.", 148, 440, 294, 36, { size: 11.5, color: C.muted, align: "center" });
  text(slide, "highlighted path", 352, 214, 120, 20, { size: 12, bold: true, color: C.rose });
  arrow(slide, 330, 222, 278, C.rose, 3);
  box(slide, 600, 150, 590, 430);
  text(slide, "One round dataflow", 625, 168, 280, 24, { size: 17, bold: true });
  const steps = [
    ["value + index", 632, 232, 108, C.blue],
    ["node lookup", 790, 232, 108, C.cyan],
    ["hash/mix", 948, 232, 96, C.violet],
    ["branch bit", 1094, 232, 86, C.amber],
  ];
  for (let i = 0; i < steps.length; i++) {
    const [label, x, y, w, color] = steps[i];
    box(slide, x, y, w, 66, { fill: "#ffffff", stroke: color, strokeWidth: 1.5 });
    text(slide, label, x + 8, y + 20, w - 16, 24, { size: 13.5, bold: true, color, align: "center" });
    if (i < steps.length - 1) arrow(slide, x + w + 12, y + 33, steps[i + 1][1] - 10, color, 3);
  }
  downArrow(slide, 1136, 306, 372, C.amber, 3);
  box(slide, 760, 382, 265, 58, { fill: "#f0fdf4", stroke: C.green, strokeWidth: 1.4 });
  text(slide, "next index + next value", 782, 402, 220, 20, { size: 14, bold: true, color: C.green, align: "center" });
  arrow(slide, 1026, 411, 1124, C.green, 3);
  chip(slide, "batch_size = 256 independent inputs", 770, 492, 260, C.blue);
  text(slide, "depth sequence: 0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4", 652, 525, 480, 22, { size: 12.5, color: C.muted });
}

function slide3(slide) {
  title(slide, "One cycle issues a bounded VLIW packet across five engines.", "Perfetto traces show which engine slots are busy over time; blank regions are idle capacity or dependency bubbles.", "machine model", 3);
  box(slide, 50, 158, 1180, 210);
  text(slide, "Per-cycle issue packet", 74, 178, 250, 24, { size: 17, bold: true });
  packetRow(slide, 76, 228, 1.26);
  const legend = [
    ["ALU", "scalar arithmetic, comparisons, address math", engine.ALU],
    ["VALU", "vector arithmetic across 8 lanes", engine.VALU],
    ["LOAD", "memory reads", engine.LOAD],
    ["STORE", "memory writes", engine.STORE],
    ["FLOW", "control operations", engine.FLOW],
  ];
  let lx = 85;
  for (const [name, desc, color] of legend) {
    shape(slide, { x: lx, y: 324, w: 16, h: 16, fill: color, strokeWidth: 0 });
    text(slide, `${name}: ${desc}`, lx + 22, 321, 210, 20, { size: 10.5, color: C.muted });
    lx += name === "VALU" ? 250 : 225;
  }
  box(slide, 70, 418, 1060, 116);
  text(slide, "Trace strip: slot filled = issued operation", 92, 434, 280, 20, { size: 14, bold: true });
  const rows = [["ALU", engine.ALU, 460], ["VALU", engine.VALU, 486], ["LOAD", engine.LOAD, 512], ["STORE", engine.STORE, 538]];
  for (const [name, color, y] of rows) {
    text(slide, name, 92, y - 6, 52, 14, { size: 9.5, color: C.muted, align: "right" });
    shape(slide, { x: 160, y, w: 900, h: 1, fill: C.faint, strokeWidth: 0 });
    for (let i = 0; i < 28; i++) {
      if ((i + y) % 5 !== 0) shape(slide, { x: 170 + i * 31, y: y - 5, w: 18 + (i % 3) * 8, h: 10, fill: color, strokeWidth: 0 });
    }
  }
  bulletList(slide, [
    "Dense bars mean useful issue bandwidth.",
    "Blank gaps mean idle engine slots or dependency stalls.",
  ], 774, 570, 390, { size: 13, gap: 30, color: C.blue });
}

async function slide4(slide) {
  title(slide, "The roadmap is cumulative progress, not independent ablations.", "The story moves from removing waste to changing program shape, then scheduling the exposed work.", "roadmap", 4);
  await addImage(slide, "charts/optimization_ladder.png", 60, 145, 820, 430);
  const bands = [
    ["remove work", 105, 526, 150, C.green],
    ["specialize", 270, 526, 150, C.cyan],
    ["vectorize + memory", 442, 526, 178, C.violet],
    ["expose work", 636, 526, 125, C.amber],
    ["schedule", 772, 526, 104, C.rose],
  ];
  for (const [label, x, y, w, color] of bands) chip(slide, label, x, y, w, color);
  metric(slide, "97,040 -> 12,285", "stage 4 vectorization", 920, 172, 230, 84, C.violet);
  metric(slide, "8,884 -> 1,291", "stage 8 VLIW scheduling", 920, 284, 230, 84, C.rose);
  bulletList(slide, [
    "First remove work that the grader does not require.",
    "Then exploit fixed workload shape and SIMD batching.",
    "Finally pack ready operations under engine slot limits.",
  ], 924, 420, 260, { size: 13.2, gap: 38, color: C.blue });
}

async function slide5(slide) {
  title(slide, "The baseline trace shows serialization and unused machine capacity.", "The first trace-reading goal is to separate useful work from bookkeeping, memory traffic, and bubbles.", "baseline", 5);
  await addImage(slide, "trace_visuals/00_baseline.png", 60, 150, 780, 430);
  metric(slide, "147,734", "baseline cycles", 910, 150, 200, 82, C.rose);
  const callouts = [
    ["scalar lane activity", 892, 262, 190, engine.ALU],
    ["idle VALU capacity", 932, 330, 190, engine.VALU],
    ["index memory traffic", 890, 398, 190, engine.LOAD],
    ["dependency/control bubbles", 918, 466, 220, C.amber],
  ];
  for (const [label, x, y, w, color] of callouts) {
    chip(slide, label, x, y, w, color);
    arrow(slide, x - 36, y + 14, x - 8, color, 3);
  }
  text(slide, "The first goal is to remove bookkeeping and memory traffic before deep scheduling.", 75, 602, 760, 28, { size: 15, bold: true, color: C.muted });
}

function flowBox(slide, label, x, y, w, color, opts = {}) {
  box(slide, x, y, w, opts.h ?? 54, { fill: opts.fill ?? "#ffffff", stroke: color, strokeWidth: 1.2 });
  text(slide, label, x + 8, y + 14, w - 16, 24, { size: opts.size ?? 12.5, bold: true, color, align: "center" });
}

function slide6(slide) {
  title(slide, "Index bookkeeping can stay close to compute instead of round-tripping memory.", "Stage 1 combines test-contract cleanup with scratch-resident live traversal indices.", "remove work", 6);
  deltaBadge(slide, "147,734 -> 114,868", "remove ungraded work + scratch index", 916, 130, 250, C.green);
  box(slide, 80, 180, 500, 350);
  text(slide, "Before: memory index traffic every round", 108, 205, 340, 24, { size: 16, bold: true, color: C.rose });
  const before = [["load index from memory", 234], ["compute next index", 326], ["store index to memory", 418]];
  for (let i = 0; i < before.length; i++) {
    flowBox(slide, before[i][0], 190, before[i][1], 220, C.rose);
    if (i < before.length - 1) downArrow(slide, 300, before[i][1] + 58, before[i + 1][1] - 4, C.rose, 3);
  }
  text(slide, "final index write", 200, 504, 190, 20, { size: 12.5, color: C.rose, bold: true, align: "center" });
  shape(slide, { x: 200, y: 517, w: 190, h: 4, fill: C.rose, strokeWidth: 0 });
  box(slide, 650, 180, 500, 350);
  text(slide, "After: live scratch index", 678, 205, 270, 24, { size: 16, bold: true, color: C.green });
  flowBox(slide, "scratch index", 770, 156 + 78, 200, C.green, { fill: "#f0fdf4" });
  downArrow(slide, 870, 292, 342, C.green, 3);
  flowBox(slide, "compute next index", 770, 346, 200, C.green);
  downArrow(slide, 870, 404, 454, C.green, 3);
  flowBox(slide, "scratch index", 770, 458, 200, C.green, { fill: "#f0fdf4" });
  text(slide, "final index write removed", 760, 535, 230, 24, { size: 13, bold: true, color: C.green, align: "center" });
}

function slide7(slide) {
  title(slide, "Fixed benchmark knowledge turns runtime control into a known 16-step strip.", "Specialization and unrolling simplify the kernel while it is still mostly scalar.", "specialize", 7);
  deltaBadge(slide, "114,868 -> 110,898", "fixed layout", 790, 138, 190, C.cyan);
  deltaBadge(slide, "110,898 -> 97,040", "round unrolling", 1000, 138, 190, C.violet);
  box(slide, 72, 190, 430, 330);
  text(slide, "Generic loop", 98, 212, 220, 24, { size: 17, bold: true });
  const generic = ["read layout", "check depth", "loop branch", "compute"];
  generic.forEach((label, i) => {
    flowBox(slide, label, 180, 260 + i * 62, 190, i === 3 ? C.blue : C.slate);
    if (i < generic.length - 1) downArrow(slide, 275, 314 + i * 62, 330 + i * 62, C.slate, 2.5);
  });
  box(slide, 585, 190, 610, 330);
  text(slide, "Specialized emitted strip", 612, 212, 260, 24, { size: 17, bold: true });
  chip(slide, "baked-in pointers / layout constants", 865, 214, 250, C.cyan);
  const depths = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "0", "1", "2", "3", "4"];
  depths.forEach((d, i) => {
    const x = 615 + (i % 8) * 65;
    const y = 288 + Math.floor(i / 8) * 86;
    box(slide, x, y, 48, 42, { fill: i <= 10 ? "#eff6ff" : "#f0fdf4", stroke: i <= 10 ? C.blue : C.green, strokeWidth: 1 });
    text(slide, d, x + 6, y + 10, 36, 18, { size: 15, bold: true, color: i <= 10 ? C.blue : C.green, align: "center" });
    if (i < depths.length - 1 && i % 8 !== 7) arrow(slide, x + 51, y + 21, x + 65, C.muted, 2);
  });
  text(slide, "Tradeoff: instruction file grows, but the score is simulator cycles.", 628, 476, 500, 24, { size: 13, color: C.muted });
}

function slide8(slide) {
  title(slide, "SIMD batching changes 256 scalar walks into 32 vector groups.", "The hash pipeline, value update, branch bit, and many index updates become lane-wise vector operations.", "simd", 8);
  deltaBadge(slide, "97,040 -> 12,285", "stage 4 vectorization", 914, 142, 230, C.violet);
  const tokenY = 225;
  for (let i = 0; i < 8; i++) {
    shape(slide, { x: 70 + i * 56, y: tokenY + (i % 2) * 18, w: 38, h: 38, fill: "#eff6ff", stroke: C.blue, strokeWidth: 1.2, geometry: "ellipse" });
    text(slide, `s${i}`, 76 + i * 56, tokenY + 10 + (i % 2) * 18, 26, 16, { size: 10, bold: true, color: C.blue, align: "center" });
  }
  arrow(slide, 530, tokenY + 38, 650, C.violet, 5);
  box(slide, 670, 190, 285, 145, { fill: "#faf5ff", stroke: C.violet, strokeWidth: 1.5 });
  text(slide, "one 8-lane vector", 710, 207, 200, 22, { size: 16, bold: true, color: C.violet, align: "center" });
  for (let i = 0; i < 8; i++) {
    box(slide, 695 + i * 29, 248, 22, 54, { fill: i % 2 ? "#ede9fe" : "#ffffff", stroke: C.violet, strokeWidth: 1 });
    text(slide, String(i), 699 + i * 29, 268, 14, 14, { size: 9, color: C.violet, bold: true, align: "center" });
  }
  text(slide, "lane 0 ... lane 7", 722, 308, 160, 18, { size: 11, color: C.muted, align: "center" });
  box(slide, 90, 428, 420, 118);
  text(slide, "256 inputs / 8 lanes = 32 vector groups", 118, 448, 330, 24, { size: 17, bold: true });
  for (let r = 0; r < 4; r++) for (let c = 0; c < 8; c++) shape(slide, { x: 124 + c * 42, y: 488 + r * 13, w: 30, h: 7, fill: C.violet, strokeWidth: 0 });
  box(slide, 620, 410, 430, 138, { fill: "#ffffff", stroke: C.violet, strokeWidth: 1.3 });
  text(slide, "vector operation block", 650, 430, 240, 22, { size: 16, bold: true, color: C.violet });
  const ops = ["hash", "value update", "branch bit", "index update"];
  ops.forEach((op, i) => chip(slide, op, 653 + (i % 2) * 170, 470 + Math.floor(i / 2) * 38, 140, C.violet));
  text(slide, "Trace shifts toward VALU as the main engine.", 666, 572, 360, 22, { size: 14, bold: true, color: C.muted });
}

async function slide9(slide) {
  title(slide, "After SIMD, memory pressure moves to hot upper tree nodes.", "Caching the shallow nodes and streaming value I/O produce modest but important bottleneck transitions.", "memory", 9);
  await addImage(slide, "charts/tree_cache_heatmap_rounds.png", 48, 145, 650, 420);
  metric(slide, "12,285 -> 11,856", "tree caching: 7 hottest nodes", 740, 138, 230, 80, C.amber);
  metric(slide, "11,856 -> 11,825", "streaming value I/O", 990, 138, 190, 80, C.green);
  box(slide, 742, 258, 430, 128);
  text(slide, "Hot upper nodes", 765, 276, 180, 20, { size: 15, bold: true });
  flowBox(slide, "LOAD each time", 770, 318, 132, C.rose);
  arrow(slide, 914, 345, 1010, C.amber, 4);
  flowBox(slide, "scratch cache\nvector select", 1022, 312, 122, C.green, { h: 66, size: 11.5, fill: "#f0fdf4" });
  box(slide, 742, 424, 430, 98);
  text(slide, "Streaming value I/O", 765, 442, 190, 20, { size: 15, bold: true });
  text(slide, "before: scattered address recomputation", 765, 474, 220, 18, { size: 12, color: C.rose });
  text(slide, "after: base pointer + stride", 765, 494, 220, 18, { size: 12, bold: true, color: C.green });
  arrow(slide, 1000, 489, 1110, C.green, 3);
}

function slide10(slide) {
  title(slide, "Temporary banks expose independent work to the scheduler.", "A fully unrolled vector program has independent groups, but reused temp names can make them look serialized.", "parallel work", 10);
  deltaBadge(slide, "11,825 -> 8,884", "stage 7 temporary banks", 930, 136, 230, C.rose);
  box(slide, 70, 170, 500, 400);
  text(slide, "Before: false dependency chain", 100, 195, 270, 24, { size: 17, bold: true, color: C.rose });
  for (let i = 0; i < 3; i++) {
    box(slide, 160, 250 + i * 82, 240, 52, { fill: "#fff1f2", stroke: C.rose, strokeWidth: 1.2 });
    text(slide, `vector group ${i + 1}: temp0 -> temp1`, 178, 268 + i * 82, 204, 18, { size: 12.5, bold: true, color: C.rose, align: "center" });
    if (i < 2) downArrow(slide, 280, 304 + i * 82, 332 + i * 82, C.rose, 4);
  }
  text(slide, "same scratch names force order", 155, 508, 250, 22, { size: 13, bold: true, color: C.rose, align: "center" });
  box(slide, 650, 170, 500, 400);
  text(slide, "After: independent temp banks", 680, 195, 300, 24, { size: 17, bold: true, color: C.green });
  const banks = [["temp bank A", 240], ["temp bank B", 340], ["temp bank C", 440]];
  banks.forEach(([bank, y], i) => {
    box(slide, 720, y, 260, 52, { fill: "#f0fdf4", stroke: C.green, strokeWidth: 1.2 });
    text(slide, `group ${i + 1} -> ${bank}`, 740, y + 18, 220, 18, { size: 12.5, bold: true, color: C.green, align: "center" });
    arrow(slide, 990, y + 26, 1085, C.green, 3);
  });
  text(slide, "Rename temps to expose independence.", 740, 512, 300, 22, { size: 14, bold: true, color: C.muted, align: "center" });
}

async function slide11(slide) {
  title(slide, "A dependency-aware scheduler packs ready ops into VLIW slots.", "Each operation has an engine type plus explicit read/write sets; hazards define the legal schedule.", "scheduling", 11);
  deltaBadge(slide, "8,884 -> 1,291", "global VLIW scheduling", 864, 136, 180, C.blue);
  deltaBadge(slide, "1,291 -> 1,184", "final refinements", 1058, 136, 160, C.green);
  box(slide, 54, 170, 340, 325);
  text(slide, "Dependency DAG", 80, 192, 200, 22, { size: 16, bold: true });
  const dagNodes = [
    ["LOAD", 116, 260, engine.LOAD], ["ALU", 230, 236, engine.ALU], ["VALU", 226, 326, engine.VALU],
    ["STORE", 116, 410, engine.STORE], ["ALU", 306, 405, engine.ALU],
  ];
  dagNodes.forEach(([label, x, y, color]) => node(slide, label, x, y, color, { w: 68, h: 38, fill: "#ffffff", textColor: color }));
  arrow(slide, 184, 279, 230, engine.LOAD, 3); text(slide, "RAW", 192, 252, 40, 14, { size: 9, color: engine.LOAD, bold: true });
  arrow(slide, 264, 295, 306, C.amber, 3); text(slide, "WAR", 300, 315, 42, 14, { size: 9, color: C.amber, bold: true });
  arrow(slide, 184, 429, 306, C.rose, 3); text(slide, "WAW", 234, 410, 44, 14, { size: 9, color: C.rose, bold: true });
  box(slide, 426, 170, 220, 325);
  text(slide, "Ready queue", 454, 192, 160, 22, { size: 16, bold: true });
  ["critical path 42", "critical path 37", "critical path 31", "critical path 20"].forEach((item, i) => {
    box(slide, 460, 238 + i * 54, 150, 36, { fill: i < 2 ? "#eff6ff" : "#ffffff", stroke: C.blue, strokeWidth: 1 });
    text(slide, item, 474, 250 + i * 54, 122, 14, { size: 11, color: C.blue, bold: i === 0, align: "center" });
  });
  box(slide, 682, 210, 540, 160);
  text(slide, "Packed VLIW packets", 704, 230, 220, 22, { size: 16, bold: true });
  packetRow(slide, 710, 276, 0.72, "cycle N");
  packetRow(slide, 710, 342, 0.72, "cycle N+1");
  await addImage(slide, "trace_visuals/09_final_refinements.png", 690, 420, 490, 190);
  text(slide, "Inset: dense final trace utilization after safe WAR relaxation and VALU-to-ALU fallback.", 706, 616, 450, 22, { size: 12, bold: true, color: C.muted });
}

async function slide12(slide) {
  title(slide, "The binding constraint moves as each bottleneck is removed.", "Early gains reduce wasted work; late gains are scheduling quality, not just fewer logical operations.", "results", 12);
  await addImage(slide, "charts/optimization_ladder.png", 52, 145, 560, 330);
  await addImage(slide, "charts/utilization_ladder.png", 640, 145, 540, 330);
  chip(slide, "SIMD", 368, 452, 80, C.violet);
  chip(slide, "VLIW scheduling", 462, 452, 138, C.rose);
  metric(slide, "124.8x", "final speedup over baseline", 82, 522, 150, 78, C.green);
  metric(slide, "1,184", "final cycle count", 252, 522, 150, 78, C.blue);
  box(slide, 470, 526, 690, 72);
  const moves = [["serialization", C.rose], ["memory pressure", C.amber], ["exposed independence", C.violet], ["scheduling", C.green]];
  moves.forEach(([label, color], i) => {
    chip(slide, label, 496 + i * 156, 548, 138, color);
    if (i < moves.length - 1) arrow(slide, 636 + i * 156, 562, 652 + i * 156, C.muted, 2);
  });
}

function slide13(slide) {
  title(slide, "The final kernel is fast because it is intentionally specialized.", "The remaining risks are real compiler-engineering tradeoffs, not mystery performance issues.", "limitations", 13);
  const cards = [
    ["Highly specialized workload", "Assumes forest_height = 10, rounds = 16, batch_size = 256, and stable memory layout.", C.blue],
    ["Generated code size increases", "Unrolling and specialization remove runtime overhead but produce a larger instruction stream.", C.rose],
    ["Scheduler is heuristic", "Dependency analysis and priority rules guide packing, but this is not an optimal solver.", C.violet],
    ["Scratch allocation is manually tuned", "Temp banks expose parallelism; a full liveness-aware register-coloring pass is still future work.", C.amber],
    ["Profiler interpretation is still manual", "Perfetto traces guided the path, but bottleneck classification and goodput metrics are not fully automated.", C.green],
  ];
  cards.forEach(([head, body, color], i) => {
    const x = i < 2 ? 70 + i * 570 : 70 + (i - 2) * 380;
    const y = i < 2 ? 170 : 372;
    const w = i < 2 ? 520 : 340;
    box(slide, x, y, w, i < 2 ? 138 : 150);
    shape(slide, { x, y, w: 7, h: i < 2 ? 138 : 150, fill: color, strokeWidth: 0 });
    text(slide, head, x + 24, y + 24, w - 45, 24, { size: 16, bold: true, color });
    text(slide, body, x + 24, y + 64, w - 48, 52, { size: 12.5, color: C.ink });
  });
}

function slide14(slide) {
  title(slide, "Next steps generalize the hand-built ladder into a compiler pipeline.", "The formal dependency graph is the anchor: it supports correctness, allocation, and schedule search.", "next steps", 14);
  const steps = [
    ["trace metrics", "goodput", C.blue],
    ["dependency graph", "hazards", C.rose],
    ["register coloring", "liveness", C.green],
    ["scheduler search", "engine slots", C.violet],
    ["verified VLIW program", "verification", C.amber],
  ];
  let x = 70;
  steps.forEach(([head, sub, color], i) => {
    box(slide, x, 250, 190, 108, { fill: head === "dependency graph" ? "#fff1f2" : "#ffffff", stroke: color, strokeWidth: 1.5 });
    text(slide, head, x + 14, 276, 162, 24, { size: 15, bold: true, color, align: "center" });
    text(slide, sub, x + 14, 314, 162, 20, { size: 12, color: C.muted, align: "center" });
    if (i < steps.length - 1) arrow(slide, x + 198, 304, x + 240, color, 4);
    x += 230;
  });
  text(slide, "feedback from traces", 250, 444, 250, 24, { size: 14, bold: true, color: C.blue, align: "center" });
  shape(slide, { x: 235, y: 430, w: 650, h: 4, fill: C.blue, strokeWidth: 0 });
  text(slide, "<", 220, 414, 28, 32, { size: 26, bold: true, color: C.blue, align: "center" });
  text(slide, ">", 872, 414, 28, 32, { size: 26, bold: true, color: C.blue, align: "center" });
  box(slide, 360, 510, 560, 78, { fill: "#ffffff", stroke: C.rose, strokeWidth: 1.2 });
  text(slide, "Formal dependency model", 386, 528, 240, 20, { size: 16, bold: true, color: C.rose });
  text(slide, "Represent every instruction as a graph node with explicit reads, writes, engine constraints, and RAW/WAR/WAW edges.", 386, 554, 500, 20, { size: 12.5, color: C.ink });
}

async function renderAndSave(presentation, slides) {
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(LAYOUT_DIR, { recursive: true });
  const previewPaths = [];
  for (let i = 0; i < slides.length; i++) {
    const num = String(i + 1).padStart(2, "0");
    const png = await presentation.export({ slide: slides[i], format: "png", scale: 1 });
    const pngPath = `${PREVIEW_DIR}/slide-${num}.png`;
    await fs.writeFile(pngPath, Buffer.from(await png.arrayBuffer()));
    previewPaths.push(pngPath);
    const layout = await presentation.export({ slide: slides[i], format: "layout" });
    await fs.writeFile(`${LAYOUT_DIR}/slide-${num}.layout.json`, await layout.text(), "utf8");
  }
  const python = "/Users/baseb/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
  const contact = spawnSync(python, [
    "/Users/baseb/.codex/plugins/cache/openai-primary-runtime/presentations/26.601.10930/skills/presentations/scripts/make_contact_sheet.py",
    "--output",
    CONTACT_SHEET,
    ...previewPaths,
  ], { encoding: "utf8" });
  if (contact.status !== 0) throw new Error(`contact sheet failed\n${contact.stdout}\n${contact.stderr}`);
  return previewPaths;
}

async function main() {
  await fs.mkdir(`${WORKSPACE}/output`, { recursive: true });
  const originalCopy = `${WORKSPACE}/output/source-current-before-edit.pptx`;
  await fs.copyFile(SOURCE, originalCopy);
  const presentation = await PresentationFile.importPptx(await FileBlob.load(SOURCE));
  const slides = slidesFromPresentation(presentation);
  if (slides.length !== 14) throw new Error(`Expected 14 slides in source deck, got ${slides.length}`);
  for (const slide of slides) clear(slide);
  slide1(slides[0]);
  slide2(slides[1]);
  slide3(slides[2]);
  await slide4(slides[3]);
  await slide5(slides[4]);
  slide6(slides[5]);
  slide7(slides[6]);
  slide8(slides[7]);
  await slide9(slides[8]);
  slide10(slides[9]);
  await slide11(slides[10]);
  await slide12(slides[11]);
  slide13(slides[12]);
  slide14(slides[13]);
  const previews = await renderAndSave(presentation, slides);
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(OUT);
  await fs.copyFile(OUT, ROOT_COPY);
  const outStat = await fs.stat(OUT);
  await fs.writeFile(MANIFEST, `${JSON.stringify({
    source: SOURCE,
    originalCopy,
    output: OUT,
    rootCopy: ROOT_COPY,
    outputBytes: outStat.size,
    slideCount: slides.length,
    previews,
    contactSheet: CONTACT_SHEET,
  }, null, 2)}\n`);
  console.log(JSON.stringify({ output: OUT, rootCopy: ROOT_COPY, outputBytes: outStat.size, slideCount: slides.length, contactSheet: CONTACT_SHEET }, null, 2));
}

main().then(() => setTimeout(() => process.exit(0), 100)).catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
