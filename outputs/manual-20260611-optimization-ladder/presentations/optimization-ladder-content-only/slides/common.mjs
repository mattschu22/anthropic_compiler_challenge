export function addTitle(slide, ctx, title) {
  ctx.addText(slide, {
    text: title,
    x: 48,
    y: 36,
    w: 1120,
    h: 52,
    fontSize: 28,
    bold: true,
    color: "#000000",
  });
}

export function addCycleBadge(slide, ctx, text) {
  ctx.addText(slide, {
    text,
    x: 930,
    y: 38,
    w: 270,
    h: 28,
    fontSize: 14,
    bold: true,
    color: "#000000",
    align: "right",
  });
}

export function addSubtitle(slide, ctx, text) {
  ctx.addText(slide, {
    text,
    x: 50,
    y: 92,
    w: 1120,
    h: 42,
    fontSize: 16,
    color: "#000000",
  });
}

export function addBullets(slide, ctx, bullets, x = 70, y = 150, w = 1050, fontSize = 16, gap = 38) {
  let cy = y;
  for (const bullet of bullets) {
    ctx.addText(slide, {
      text: `• ${bullet}`,
      x,
      y: cy,
      w,
      h: Math.max(gap, 34),
      fontSize,
      color: "#000000",
    });
    cy += gap;
  }
}

export function addTextBlock(slide, ctx, text, x = 70, y = 150, w = 1050, h = 120, fontSize = 16) {
  ctx.addText(slide, {
    text,
    x,
    y,
    w,
    h,
    fontSize,
    color: "#000000",
  });
}

export function addPlaceholder(slide, ctx, text, x = 70, y = 548, w = 1050, h = 92) {
  ctx.addText(slide, {
    text: `[Placeholder: ${text}]`,
    x,
    y,
    w,
    h,
    fontSize: 12,
    color: "#000000",
  });
}
