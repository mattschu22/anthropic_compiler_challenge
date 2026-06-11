const ROOT = "/Users/baseb/Documents/Projects/AnthropicPerf/anthropic_compiler_challenge";
export const ASSET = `${ROOT}/optimization_ladder/results`;

export const colors = {
  bg: "#f8fafc",
  ink: "#0f172a",
  muted: "#475569",
  faint: "#e2e8f0",
  panel: "#ffffff",
  dark: "#111827",
  blue: "#2563eb",
  cyan: "#0891b2",
  green: "#16a34a",
  amber: "#d97706",
  rose: "#be123c",
  violet: "#7c3aed",
};

export function addBackground(slide, ctx, section = "") {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: colors.bg });
  ctx.addShape(slide, { x: 0, y: 0, w: 14, h: ctx.H, fill: colors.blue });
  if (section) {
    ctx.addText(slide, {
      text: section.toUpperCase(),
      x: 42, y: 28, w: 420, h: 20,
      fontSize: 12, bold: true, color: colors.blue,
      typeface: ctx.fonts.body,
    });
  }
}

export function addTitle(slide, ctx, title, subtitle = "", section = "") {
  addBackground(slide, ctx, section);
  ctx.addText(slide, {
    text: title,
    x: 42, y: 52, w: 760, h: subtitle ? 46 : 64,
    fontSize: 32, bold: true, color: colors.ink,
    typeface: ctx.fonts.title,
  });
  if (subtitle) {
    ctx.addText(slide, {
      text: subtitle,
      x: 44, y: 98, w: 1000, h: 34,
      fontSize: 16, color: colors.muted,
      typeface: ctx.fonts.body,
    });
  }
}

export function addFooter(slide, ctx, n) {
  ctx.addText(slide, {
    text: `${n}`,
    x: 1215, y: 682, w: 36, h: 22,
    fontSize: 11, color: "#94a3b8", align: "right",
  });
}

export function box(slide, ctx, { x, y, w, h, fill = colors.panel, line = colors.faint }) {
  return ctx.addShape(slide, {
    x, y, w, h,
    fill,
    line: { fill: line, width: 1, style: "solid" },
  });
}

export function label(slide, ctx, text, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text, x, y, w, h,
    fontSize: opts.size ?? 14,
    bold: opts.bold ?? false,
    color: opts.color ?? colors.ink,
    fill: opts.fill ?? "#00000000",
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    typeface: opts.mono ? ctx.fonts.mono : ctx.fonts.body,
  });
}

export function bulletList(slide, ctx, items, x, y, w, opts = {}) {
  let cy = y;
  const size = opts.size ?? 17;
  const gap = opts.gap ?? 42;
  const bulletColor = opts.bulletColor ?? colors.blue;
  for (const item of items) {
    ctx.addShape(slide, { x, y: cy + 8, w: 7, h: 7, fill: bulletColor, line: { fill: bulletColor, width: 0 } });
    ctx.addText(slide, {
      text: item,
      x: x + 18, y: cy, w, h: gap,
      fontSize: size, color: opts.color ?? colors.ink,
      typeface: ctx.fonts.body,
    });
    cy += gap;
  }
}

export function metric(slide, ctx, value, labelText, x, y, w, h, color = colors.blue) {
  box(slide, ctx, { x, y, w, h, fill: "#ffffff" });
  ctx.addText(slide, {
    text: value,
    x: x + 16, y: y + 14, w: w - 32, h: 40,
    fontSize: 28, bold: true, color,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    text: labelText,
    x: x + 16, y: y + 58, w: w - 32, h: 38,
    fontSize: 13, color: colors.muted,
    typeface: ctx.fonts.body,
  });
}

export async function image(slide, ctx, relPath, x, y, w, h, alt = "") {
  return ctx.addImage(slide, {
    path: `${ASSET}/${relPath}`,
    x, y, w, h,
    fit: "contain",
    alt,
  });
}

export function stageMiniTable(slide, ctx, rows, x, y, w, h) {
  box(slide, ctx, { x, y, w, h, fill: "#ffffff" });
  const rowH = h / rows.length;
  rows.forEach((r, i) => {
    const yy = y + i * rowH;
    if (i > 0) ctx.addShape(slide, { x, y: yy, w, h: 1, fill: colors.faint, line: { fill: colors.faint, width: 0 } });
    label(slide, ctx, r[0], x + 12, yy + 8, w * 0.34, rowH - 8, { size: 12, bold: true, color: r[3] || colors.blue });
    label(slide, ctx, r[1], x + w * 0.38, yy + 8, w * 0.34, rowH - 8, { size: 12, color: colors.ink });
    label(slide, ctx, r[2], x + w * 0.74, yy + 8, w * 0.22, rowH - 8, { size: 12, color: colors.muted, align: "right" });
  });
}

export function pill(slide, ctx, text, x, y, w, color = colors.blue) {
  ctx.addShape(slide, {
    x, y, w, h: 28,
    fill: "#ffffff",
    line: { fill: color, width: 1.2, style: "solid" },
  });
  label(slide, ctx, text, x + 8, y + 6, w - 16, 18, { size: 11, bold: true, color, align: "center" });
}
