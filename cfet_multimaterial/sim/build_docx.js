// Build paper/manuscript.docx from paper/docx_build/spec.json (IEEE two-column layout).
// Run: node sim/build_docx.js
const fs = require("fs"), path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType,
        HeadingLevel, SectionType, BorderStyle, TabStopType, ShadingType, Footer, PageNumber, VerticalAlign } = D;
const HERE = path.resolve(__dirname, "..");
const spec = JSON.parse(fs.readFileSync(path.join(HERE, "paper", "docx_build", "spec.json"), "utf8"));
const FONT = "Times New Roman";
const PAGE = { width: 12240, height: 15840, margin: { top: 1080, bottom: 1080, left: 900, right: 900 } }; // US Letter, 0.75/0.625 in
const TEXT_W = 12240 - 900 - 900;   // 10440 DXA
const COL_GAP = 360; const COL_W = (TEXT_W - COL_GAP) / 2;  // 5040 DXA = 3.5 in

function runs(rs, extra = {}) {
  return rs.map(r => new TextRun({ text: r.text, bold: !!r.b || !!extra.bold, italics: !!r.i || !!extra.italics,
    subScript: !!r.sub, superScript: !!r.sup, font: r.mono ? "Courier New" : FONT, size: extra.size || 20 }));
}
function para(rs, opts = {}) {
  return new Paragraph({ children: runs(rs, opts), alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { after: opts.after ?? 0, before: opts.before ?? 0, line: 240 }, indent: opts.noindent ? undefined : { firstLine: 200 }, keepNext: opts.keepNext });
}
function heading(rs, level) {
  const text = rs.map(r => r.text).join("");
  if (level === 1) {
    subCount = 0; subsubCount = 0;
    return new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { before: 240, after: 120 },
      children: [new TextRun({ text: `${roman(++secCount)}. ${text.toUpperCase()}`, font: FONT, size: 20, bold: false })], keepNext: true });
  }
  if (level === 2) {
    subCount++; subsubCount = 0;
    return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 160, after: 80 },
      children: [new TextRun({ text: `${String.fromCharCode(64 + subCount)}. `, font: FONT, size: 20, italics: true }), ...runs(rs, { italics: true })], keepNext: true });
  }
  subsubCount++;
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 100, after: 40 },
    children: [new TextRun({ text: `${subsubCount}) `, font: FONT, size: 20, italics: true }), ...runs(rs, { italics: true }), new TextRun({ text: ":", font: FONT, size: 20 })], keepNext: true });
}
function roman(n) { return ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][n - 1]; }
let secCount = 0, subCount = 0, subsubCount = 0;

function imageParagraph(file, maxWdxa, maxHdxa, align = AlignmentType.CENTER) {
  const buf = fs.readFileSync(file);
  // PNG header: width/height at bytes 16..24
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const maxWpx = maxWdxa / 15, maxHpx = maxHdxa / 15;        // 1 px = 15 DXA at 96 dpi
  const sc = Math.min(maxWpx / w, maxHpx / h);
  return new Paragraph({ alignment: align, spacing: { before: 60, after: 60 },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(w * sc), height: Math.round(h * sc) } })] });
}
function caption(prefix, rs) {
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 },
    children: [new TextRun({ text: prefix, font: FONT, size: 16 }), ...runs(rs, { size: 16 })] });
}
function tableBlock(b, widthDxa) {
  const ncol = Math.max(...b.rows.map(r => r.length));
  const colW = Array(ncol).fill(Math.floor(widthDxa / ncol));
  const first = widthDxa - colW.slice(1).reduce((a, c) => a + c, 0); colW[0] = first;
  const border = { style: BorderStyle.SINGLE, size: 4, color: "000000" }, none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const rows = b.rows.map((r, ri) => new TableRow({ children: Array.from({ length: ncol }, (_, ci) => new TableCell({
    width: { size: colW[ci], type: WidthType.DXA }, verticalAlign: VerticalAlign.CENTER,
    borders: { top: ri === 0 ? border : none, bottom: (ri === 0 || ri === b.rows.length - 1 || (ri === 1 && b.rows[1].every(c => c.length === 0 || /\(.*\)/.test(c.map(x => x.text).join("")) || c.map(x => x.text).join("").trim() === ""))) ? border : none, left: none, right: none },
    margins: { top: 20, bottom: 20, left: 40, right: 40 },
    children: [new Paragraph({ alignment: ci === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, spacing: { after: 0 }, children: runs(r[ci] || [], { size: 14 }) })] })) }));
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 }, keepNext: true,
      children: [new TextRun({ text: `TABLE ${b.num}`, font: FONT, size: 16 })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, keepNext: true, children: runs(b.caption, { size: 16 }).map(x => x) }),
    new Table({ width: { size: widthDxa, type: WidthType.DXA }, columnWidths: colW, rows, alignment: AlignmentType.CENTER }),
    new Paragraph({ spacing: { after: 120 }, children: [] }),
  ];
}
function equation(b) {
  const buf = fs.readFileSync(b.png); const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const px = w / 400 * 96 * 0.95, ph = h / 400 * 96 * 0.95;   // rendered at 400 dpi; 0.95 scale ~ 10 pt
  const sc = Math.min(1, (COL_W - 700) / 15 / px);
  return new Paragraph({ spacing: { before: 60, after: 60 }, tabStops: [{ type: TabStopType.RIGHT, position: COL_W }],
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(px * sc), height: Math.round(ph * sc) } }),
               new TextRun({ text: `\t${b.num}`, font: FONT, size: 20 })] });
}

// ---- assemble sections: 2-column text, continuous 1-column breaks for wide floats ----
const sections = []; let cur = []; let twoCol = true;
function pushSection(children, cols) {
  if (!children.length) return;
  sections.push({ properties: { type: SectionType.CONTINUOUS, page: PAGE, column: cols === 2 ? { count: 2, space: COL_GAP, equalWidth: true } : { count: 1 } },
    children });
}
// header block (single column)
const head = [];
head.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 200 }, children: runs(spec.title, { size: 36 }) }));
head.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: [new TextRun({ text: spec.author, font: FONT, size: 22 })] }));
head.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: spec.affiliation, font: FONT, size: 18, italics: true })] }));
pushSection(head, 1);

for (const b of spec.blocks) {
  if (b.type === "abstract") {
    cur.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 120 }, children: [new TextRun({ text: "Abstract—", font: FONT, size: 18, bold: true, italics: true }), ...runs(b.runs, { size: 18, bold: true })] }));
  } else if (b.type === "keywords") {
    cur.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 200 }, children: [new TextRun({ text: "Index Terms—", font: FONT, size: 18, bold: true, italics: true }), ...runs(b.runs, { size: 18, bold: true })] }));
  } else if (b.type === "h1") cur.push(heading(b.runs, 1));
  else if (b.type === "h2") cur.push(heading(b.runs, 2));
  else if (b.type === "h3") cur.push(heading(b.runs, 3));
  else if (b.type === "p") cur.push(para(b.runs, { after: 0 }));
  else if (b.type === "eq") cur.push(equation(b));
  else if (b.type === "fig") {
    const items = [];
    if (b.imgs.length === 1) items.push(imageParagraph(b.imgs[0], b.wide ? TEXT_W : COL_W, b.wide ? 7000 : 5200));
    else {
      // side-by-side sub-figures in a borderless table
      const n = b.imgs.length, w = Math.floor((b.wide ? TEXT_W : COL_W) / n);
      items.push(new Table({ width: { size: w * n, type: WidthType.DXA }, columnWidths: Array(n).fill(w), alignment: AlignmentType.CENTER,
        rows: [new TableRow({ children: b.imgs.map((im, k) => new TableCell({ width: { size: w, type: WidthType.DXA },
          borders: { top: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, bottom: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, left: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" }, right: { style: BorderStyle.NONE, size: 0, color: "FFFFFF" } },
          children: [imageParagraph(im, w - 100, 4000), new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `(${"abcdef"[k]})`, font: FONT, size: 16 })] })] })) })] }));
    }
    items.push(caption(`Fig. ${b.num}. `, b.caption));
    if (b.wide) { pushSection(cur, 2); cur = []; pushSection(items, 1); } else cur.push(...items);
  } else if (b.type === "tab") {
    const items = tableBlock(b, b.wide ? TEXT_W : COL_W);
    if (b.wide) { pushSection(cur, 2); cur = []; pushSection(items, 1); } else cur.push(...items);
  }
}
// references
cur.push(new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { before: 240, after: 120 }, children: [new TextRun({ text: "REFERENCES", font: FONT, size: 20 })] }));
spec.references.forEach((r, i) => cur.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 40 }, indent: { left: 400, hanging: 400 },
  children: [new TextRun({ text: `[${i + 1}] `, font: FONT, size: 16 }), new TextRun({ text: r, font: FONT, size: 16 })] })));
pushSection(cur, 2);

const doc = new Document({
  creator: spec.author, title: spec.title.map(r => r.text).join(""),
  styles: { default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 20, bold: false, color: "000000" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 20, italics: true, bold: false, color: "000000" }, paragraph: { outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 20, italics: true, bold: false, color: "000000" }, paragraph: { outlineLevel: 2 } }] },
  sections: sections.map((s, i) => ({ ...s, footers: i === 0 ? { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16 })] })] }) } : undefined })),
});
Packer.toBuffer(doc).then(buf => { const out = path.join(HERE, "paper", "manuscript.docx"); fs.writeFileSync(out, buf); console.log("wrote", out, (buf.length / 1e6).toFixed(1), "MB,", sections.length, "sections"); });
