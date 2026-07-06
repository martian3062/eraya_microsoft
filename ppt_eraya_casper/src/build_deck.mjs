import { mkdir, readFile, writeFile, copyFile } from "node:fs/promises";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const OUT = "output/output.pptx";
const ROOT_COPY = "../ERAYA_Casper_7_slide_deck.pptx";
const PREVIEW_DIR = "scratch/rendered-pptx";
const LAYOUT_DIR = "scratch/layouts";

const W = 1920;
const H = 1080;

const C = {
  ink: "#101820",
  ink2: "#17232C",
  cream: "#F5F1EA",
  muted: "#B8C2CC",
  line: "#31424E",
  casper: "#E45845",
  redDark: "#8E2F2C",
  teal: "#14B8A6",
  tealDark: "#0E766E",
  gold: "#E7B657",
  green: "#74D680",
  white: "#FFFFFF",
};

const FONT = {
  display: "Aptos Display",
  body: "Aptos",
  mono: "Cascadia Mono",
};

const api = {
  mode: "demo/testnet",
  wallets: 4,
  x402: true,
  portfolioValue: "$820K",
  pnl: "+1.82%",
  risk: "0.41",
  transactions: 3,
  threats: 4,
  quorum: "75%",
  txCheck: "tx=3",
  threatCheck: "threats=4",
  liveUrl: "http://35.255.196.78/eraya",
  defiUrl: "http://35.255.196.78/eraya/defi/portfolio",
  apiUrl: "http://35.255.196.78/eraya_api/api/domains/casper_defi/dashboard/",
  services: "backend 8022 / frontend 3022",
};

function fill(color) {
  return { type: "solid", color };
}

function line(color, width = 1, style = "solid") {
  return { style, fill: color, width };
}

function bg(slide, color = C.ink) {
  const s = slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: W, height: H },
    fill: fill(color),
    line: line(color, 0),
  });
  s.name = "background";
  s.sendToBack();
  return s;
}

function rect(slide, name, left, top, width, height, color, opts = {}) {
  const s = slide.shapes.add({
    geometry: opts.geometry ?? "rect",
    position: { left, top, width, height },
    fill: fill(color),
    line: line(opts.lineColor ?? color, opts.lineWidth ?? 0, opts.lineStyle ?? "solid"),
  });
  s.name = name;
  if (opts.radius) s.geometry = "roundRect";
  return s;
}

function textBox(slide, name, value, left, top, width, height, style = {}) {
  const s = slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
  });
  s.name = name;
  s.text.style = {
    typeface: style.typeface ?? FONT.body,
    fontSize: style.fontSize ?? 28,
    color: style.color ?? C.cream,
    bold: style.bold ?? false,
    italic: style.italic ?? false,
    alignment: style.alignment ?? "left",
    verticalAlignment: style.verticalAlignment ?? "top",
  };
  if (style.lineSpacing) s.text.lineSpacing = style.lineSpacing;
  s.text = value;
  return s;
}

function label(slide, name, value, left, top, width, height, color = C.muted) {
  return textBox(slide, name, value.toUpperCase(), left, top, width, height, {
    typeface: FONT.mono,
    fontSize: 17,
    bold: true,
    color,
  });
}

function chip(slide, name, value, left, top, width, color = C.ink2, textColor = C.cream) {
  rect(slide, `${name}-shape`, left, top, width, 42, color, {
    geometry: "roundRect",
    lineColor: color,
  });
  return textBox(slide, `${name}-text`, value, left + 16, top + 8, width - 32, 28, {
    typeface: FONT.mono,
    fontSize: 15,
    bold: true,
    color: textColor,
    alignment: "center",
    verticalAlignment: "middle",
  });
}

function circle(slide, name, cx, cy, r, color, opts = {}) {
  const s = slide.shapes.add({
    geometry: "ellipse",
    position: { left: cx - r, top: cy - r, width: r * 2, height: r * 2 },
    fill: fill(color),
    line: line(opts.lineColor ?? color, opts.lineWidth ?? 0),
  });
  s.name = name;
  return s;
}

function connector(slide, name, from, to, color = C.line, width = 3) {
  const c = slide.shapes.add({
    geometry: "connector",
    from,
    to,
    fromIdx: 3,
    toIdx: 1,
    kind: "straight",
    line: line(color, width),
  });
  c.name = name;
  return c;
}

function segment(slide, name, left, top, width, height, color, rotation = 0) {
  const s = rect(slide, name, left, top, width, height, color);
  if (rotation) s.position.merge({ rotation });
  return s;
}

function footer(slide, n, dark = true) {
  const color = dark ? "#7F94A1" : "#5C6A72";
  textBox(slide, `footer-${n}`, `ERAYA Casper DeFi Swarm / ${n} of 7`, 78, 1014, 520, 28, {
    typeface: FONT.mono,
    fontSize: 13,
    color,
  });
}

function title(slide, eyebrow, headline, subhead, light = true) {
  const main = light ? C.cream : C.ink;
  const secondary = light ? C.muted : "#52606A";
  label(slide, "eyebrow", eyebrow, 78, 70, 900, 28, light ? C.teal : C.redDark);
  textBox(slide, "title", headline, 78, 112, 1120, 144, {
    typeface: FONT.display,
    fontSize: 56,
    bold: true,
    color: main,
  });
  if (subhead) {
    textBox(slide, "subtitle", subhead, 80, 262, 1080, 76, {
      fontSize: 25,
      color: secondary,
    });
  }
}

function addMetric(slide, name, labelText, value, left, top, width, accent = C.teal) {
  textBox(slide, `${name}-value`, value, left, top, width, 66, {
    typeface: FONT.display,
    fontSize: 52,
    bold: true,
    color: C.cream,
  });
  segment(slide, `${name}-rule`, left, top + 74, Math.min(width, 190), 5, accent);
  textBox(slide, `${name}-label`, labelText, left, top + 92, width, 46, {
    typeface: FONT.mono,
    fontSize: 15,
    bold: true,
    color: C.muted,
  });
}

function slide1(p) {
  const slide = p.slides.add();
  bg(slide, C.ink);

  segment(slide, "cover-red-spine", 0, 0, 34, H, C.casper);
  segment(slide, "cover-teal-spine", 36, 0, 10, H, C.teal);
  circle(slide, "orbit-outer", 1450, 510, 300, C.ink, { lineColor: "#29424B", lineWidth: 4 });
  circle(slide, "orbit-mid", 1450, 510, 205, C.ink, { lineColor: "#38545B", lineWidth: 3 });
  circle(slide, "orbit-core", 1450, 510, 92, C.casper, { lineColor: C.gold, lineWidth: 3 });
  textBox(slide, "core-label", "CASPER\nDEFI", 1364, 466, 172, 92, {
    typeface: FONT.mono,
    fontSize: 22,
    bold: true,
    color: C.white,
    alignment: "center",
    verticalAlignment: "middle",
  });

  const nodes = [
    ["Perceiver", 1210, 310, C.teal],
    ["Planner", 1656, 322, C.gold],
    ["Recoverer", 1660, 710, C.green],
    ["Guardian", 1210, 720, C.casper],
  ];
  for (const [name, x, y, color] of nodes) {
    const n = circle(slide, `cover-${name.toLowerCase()}-node`, x, y, 48, color, {
      lineColor: C.white,
      lineWidth: 2,
    });
    connector(slide, `cover-${name.toLowerCase()}-link`, n, slide.shapes.getItem("orbit-core"), "#516B75", 3);
    textBox(slide, `cover-${name.toLowerCase()}-label`, name, x - 86, y + 64, 172, 32, {
      typeface: FONT.mono,
      fontSize: 16,
      bold: true,
      color: C.cream,
      alignment: "center",
    });
  }

  label(slide, "cover-eyebrow", "MICROSOFT BUILD AI HACKATHON 2026 / CASPER BRANCH", 92, 96, 900, 28, C.teal);
  textBox(slide, "cover-title", "ERAYA Casper\nDeFi Swarm", 88, 172, 920, 210, {
    typeface: FONT.display,
    fontSize: 76,
    bold: true,
    color: C.cream,
  });
  textBox(
    slide,
    "cover-subtitle",
    "A self-healing, security-first multi-agent treasury system: quorum before execution, KAVACHA before damage, x402 inside the agent economy.",
    94,
    424,
    880,
    132,
    { fontSize: 30, color: C.muted },
  );
  chip(slide, "cover-live", api.liveUrl, 96, 870, 540, C.ink2, C.cream);
  chip(slide, "cover-branch", "branch: caspr / deployed under /eraya", 658, 870, 410, C.redDark, C.cream);
  footer(slide, 1);
}

function slide2(p) {
  const slide = p.slides.add();
  bg(slide, C.cream);
  title(
    slide,
    "WHY THIS EXISTS",
    "DeFi does not fail politely.",
    "A solo agent can trade. A resilient treasury needs agents that can disagree, recover, and prove why they acted.",
    false,
  );

  textBox(slide, "problem-big", "Most agent demos optimize the happy path.", 96, 410, 760, 180, {
    typeface: FONT.display,
    fontSize: 62,
    bold: true,
    color: C.ink,
  });
  segment(slide, "problem-rule", 98, 625, 320, 6, C.casper);
  textBox(slide, "problem-note", "On-chain systems punish missing failure paths with real loss, not just a bad log line.", 100, 656, 660, 92, {
    fontSize: 30,
    color: "#42505A",
  });

  const items = [
    ["No on-chain agent identity", "AgentCards vanish on restart and cannot be independently verified."],
    ["Free inter-agent calls", "No economic signal for useful planning, vetoes, or recovery work."],
    ["One-agent decisions", "Critical DeFi moves need quorum and adversarial review."],
    ["Reactive security", "Threats should be hunted before a bad deploy lands."],
  ];
  let y = 382;
  items.forEach((it, idx) => {
    const accent = [C.casper, C.teal, C.gold, C.redDark][idx];
    circle(slide, `problem-dot-${idx}`, 1024, y + 18, 13, accent);
    textBox(slide, `problem-head-${idx}`, it[0], 1060, y, 650, 34, {
      typeface: FONT.display,
      fontSize: 29,
      bold: true,
      color: C.ink,
    });
    textBox(slide, `problem-body-${idx}`, it[1], 1062, y + 44, 650, 58, {
      fontSize: 22,
      color: "#52606A",
    });
    segment(slide, `problem-sep-${idx}`, 1024, y + 118, 600, 2, "#D5D0C7");
    y += 142;
  });
  footer(slide, 2, false);
}

function slide3(p) {
  const slide = p.slides.add();
  bg(slide, C.ink);
  title(
    slide,
    "SOLUTION",
    "ERAYA turns a DeFi treasury into an immune system.",
    "Four agent archetypes share context, vote on high-stakes moves, and degrade through a 3-tier cascade instead of failing closed.",
  );

  const core = circle(slide, "solution-core", 960, 590, 110, C.casper, { lineColor: C.gold, lineWidth: 4 });
  textBox(slide, "solution-core-label", "TREASURY\nSTATE", 860, 538, 200, 108, {
    typeface: FONT.mono,
    fontSize: 25,
    bold: true,
    color: C.white,
    alignment: "center",
    verticalAlignment: "middle",
  });

  const agents = [
    ["Perceiver", "Reads Casper DeFi signals and risk features", 540, 410, C.teal],
    ["Planner", "Generates risk-adjusted rebalance actions", 1380, 410, C.gold],
    ["Recoverer", "Keeps rollback and retry paths ready", 1380, 770, C.green],
    ["Guardian", "Blocks unsafe actions with KAVACHA rules", 540, 770, C.casper],
  ];
  for (const [name, copy, x, y, color] of agents) {
    const n = circle(slide, `solution-${name.toLowerCase()}`, x, y, 78, color, {
      lineColor: C.white,
      lineWidth: 2,
    });
    connector(slide, `solution-link-${name}`, n, core, "#4C6570", 4);
    textBox(slide, `solution-agent-${name}`, name, x - 120, y + 98, 240, 38, {
      typeface: FONT.display,
      fontSize: 31,
      bold: true,
      color: C.cream,
      alignment: "center",
    });
    textBox(slide, `solution-copy-${name}`, copy, x - 190, y + 142, 380, 64, {
      fontSize: 21,
      color: C.muted,
      alignment: "center",
    });
  }

  chip(slide, "solution-cascade", "3-tier cascade: GPU/LLM -> CPU models -> deterministic rules", 612, 950, 696, C.ink2);
  footer(slide, 3);
}

function slide4(p) {
  const slide = p.slides.add();
  bg(slide, C.cream);
  title(
    slide,
    "ARCHITECTURE",
    "The deployed path is product, swarm, and Casper layer in one loop.",
    "Operator actions and live domain telemetry flow through Django Channels into the ERAYA core, then out to Casper-aware tools.",
    false,
  );

  const y = 470;
  const blocks = [
    ["Next.js console", "DeFi portfolio\nThreat radar\nConsensus UI", 94, C.ink],
    ["Django + Channels", "REST / WebSocket\nAudit log\nDomain registry", 486, C.tealDark],
    ["ERAYA swarm core", "Perceiver\nPlanner\nRecoverer\nGuardian", 878, C.casper],
    ["Casper layer", "MCP facades\nCSPR.click wallet\nx402 + reputation", 1270, C.redDark],
  ];
  const shapes = [];
  for (const [head, body, x, color] of blocks) {
    const r = rect(slide, `arch-${head}`, x, y, 300, 265, color, {
      geometry: "roundRect",
      lineColor: C.ink,
      lineWidth: 2,
    });
    shapes.push(r);
    textBox(slide, `arch-head-${head}`, head, x + 26, y + 28, 248, 42, {
      typeface: FONT.display,
      fontSize: 28,
      bold: true,
      color: C.white,
      alignment: "center",
    });
    textBox(slide, `arch-body-${head}`, body, x + 34, y + 98, 232, 118, {
      typeface: FONT.mono,
      fontSize: 20,
      color: "#F8FBFB",
      alignment: "center",
      verticalAlignment: "middle",
    });
  }
  for (let i = 0; i < shapes.length - 1; i += 1) {
    connector(slide, `arch-arrow-${i}`, shapes[i], shapes[i + 1], "#5C6A72", 5);
  }

  segment(slide, "arch-base", 166, 808, 1420, 4, "#C5BDB3");
  const baseItems = [
    ["A2A", "HMAC signed messages"],
    ["ErayaGraph", "Shared context memory"],
    ["KAVACHA", "Policy and injection defense"],
    ["OTel", "Trace every tier"],
  ];
  let x = 212;
  baseItems.forEach(([a, b], i) => {
    circle(slide, `arch-small-${i}`, x, 858, 16, [C.casper, C.teal, C.gold, C.green][i]);
    textBox(slide, `arch-small-head-${i}`, a, x + 30, 840, 250, 30, {
      typeface: FONT.display,
      fontSize: 24,
      bold: true,
      color: C.ink,
    });
    textBox(slide, `arch-small-body-${i}`, b, x + 30, 876, 250, 28, {
      fontSize: 18,
      color: "#52606A",
    });
    x += 354;
  });
  footer(slide, 4, false);
}

function styleTable(table) {
  table.fill = fill(C.cream);
  table.styleOptions = { headerRow: false, bandedRows: false };
  for (let c = 0; c < table.columnCount; c += 1) {
    const cell = table.getCell(0, c);
    cell.fill = fill("#E9DCCA");
    cell.textStyle.color = C.ink;
    cell.textStyle.bold = true;
    cell.textStyle.fontSize = 16;
  }
  for (let r = 1; r < table.rowCount; r += 1) {
    for (let c = 0; c < table.columnCount; c += 1) {
      const cell = table.getCell(r, c);
      cell.fill = fill(r % 2 === 0 ? "#F5F1EA" : "#FFF9F0");
      cell.textStyle.fontSize = c === 0 ? 16 : 14;
      cell.textStyle.color = "#16232C";
      cell.margins = { left: 10, right: 10, top: 8, bottom: 8 };
    }
    table.getCell(r, 0).textStyle.bold = true;
  }
}

function slide5(p) {
  const slide = p.slides.add();
  bg(slide, C.ink);
  title(
    slide,
    "CASPER FEATURE MAP",
    "The branch connects Casper-native ideas to ERAYA's existing safety spine.",
    "Each feature lands in the codebase as a demo-safe facade today, with provider URLs ready for live endpoints.",
  );

  const values = [
    ["Casper move", "ERAYA implementation", "Demo surface"],
    ["DeFi adapter", "casper_defi domain: portfolio, yield, risk, tx log", "/defi/portfolio"],
    ["Agent wallets", "CSPR.click-shaped AgentWallet per archetype", "4 testnet wallets"],
    ["x402 economy", "X402EnabledBus prices high-value A2A requests", "x402 enabled"],
    ["Swarm quorum", "4-agent vote before high-stakes rebalance", "75% approval"],
    ["KAVACHA R004-R008", "Treasury, swap, APY, slippage, rug-pull rules", "4 open threats"],
    ["Reputation", "EMA score plus on-chain-anchor-shaped batches", "reputation panel"],
  ];
  rect(slide, "feature-table-backdrop", 104, 385, 1580, 470, C.cream, {
    lineColor: "#D9CFC3",
    lineWidth: 1,
  });
  const table = slide.tables.add({
    rows: values.length,
    columns: 3,
    left: 104,
    top: 385,
    width: 1580,
    height: 470,
    values,
  });
  styleTable(table);
  table.columnWidths = [330, 850, 400];

  textBox(slide, "feature-note", "Why judges notice: this is not a single DEX-calling agent. It is a priced, audited, voting swarm with defined failure behavior.", 112, 890, 1410, 52, {
    typeface: FONT.display,
    fontSize: 30,
    bold: true,
    color: C.cream,
  });
  segment(slide, "feature-note-rule", 112, 958, 410, 5, C.casper);
  footer(slide, 5);
}

function slide6(p) {
  const slide = p.slides.add();
  bg(slide, C.cream);
  title(
    slide,
    "LIVE PROOF",
    "The `/eraya` deployment is serving the Casper DeFi console now.",
    "Public smoke checks hit the frontend, DeFi route, static bundle, and Casper dashboard API.",
    false,
  );

  rect(slide, "proof-hero", 104, 360, 620, 430, C.ink, { geometry: "roundRect", lineColor: C.ink });
  textBox(slide, "proof-url", api.defiUrl, 142, 398, 538, 48, {
    typeface: FONT.mono,
    fontSize: 18,
    bold: true,
    color: C.teal,
  });
  addMetric(slide, "proof-value", "portfolio value", api.portfolioValue, 144, 486, 178, C.teal);
  addMetric(slide, "proof-pnl", "24h P&L", api.pnl, 350, 486, 205, C.green);
  addMetric(slide, "proof-risk", "risk score", api.risk, 586, 486, 120, C.gold);
  textBox(slide, "proof-services", `systemd: eraya-backend.service + eraya-frontend.service\n${api.services}\nNginx routes: /eraya, /eraya_api, /eraya_ws`, 144, 676, 500, 94, {
    typeface: FONT.mono,
    fontSize: 18,
    color: C.muted,
  });

  const chart = slide.charts.add("bar", {
    categories: ["CSPR", "USDC", "LP", "Escrow"],
    series: [{ name: "Allocation %", values: [56.4, 22.9, 15.7, 5.0] }],
    title: "Portfolio Allocation",
    titleTextStyle: { fontSize: 20, bold: true, color: C.ink },
    hasLegend: false,
    dataLabels: { showValue: true },
    chartFill: fill(C.cream),
    plotAreaFill: fill("#FFF9F0"),
    xAxis: { title: "Asset", visible: true },
    yAxis: { title: "%", visible: true },
    barOptions: { overlap: 0, gapWidth: 65 },
  });
  chart.frame = { left: 820, top: 386, width: 760, height: 372 };

  const checks = [
    ["Frontend", "/eraya -> 200"],
    ["DeFi route", "/eraya/defi/portfolio -> 200"],
    ["API", `${api.txCheck} / ${api.threatCheck}`],
    ["Guardrail", "/eryaa stays 404"],
  ];
  let y = 790;
  checks.forEach(([a, b], i) => {
    circle(slide, `proof-check-dot-${i}`, 842, y + 18, 12, [C.teal, C.green, C.gold, C.casper][i]);
    textBox(slide, `proof-check-${i}`, `${a}: ${b}`, 870, y, 680, 38, {
      typeface: FONT.mono,
      fontSize: 20,
      bold: true,
      color: C.ink,
    });
    y += 48;
  });
  footer(slide, 6, false);
}

function slide7(p) {
  const slide = p.slides.add();
  bg(slide, C.ink);
  title(
    slide,
    "NEXT SPRINT",
    "Turn the demo-safe Casper layer into real testnet execution.",
    "The deck lands the current build; the roadmap makes the next investor/judge question easy to answer.",
  );

  const lanes = [
    ["1", "Wire live providers", "Set CSPR.cloud, Casper MCP, CSPR.trade MCP, and CSPR.click URLs; keep deterministic fallback for stage demos.", C.teal],
    ["2", "Deploy Odra contracts", "Agent registry, treasury, governance, and reputation contracts on Casper testnet with explorer links.", C.gold],
    ["3", "Record real outcomes", "Flush reputation batches, x402 payments, quorum votes, and KAVACHA vetoes to chain-visible transactions.", C.casper],
  ];
  let x = 122;
  lanes.forEach(([num, head, body, color], i) => {
    circle(slide, `road-num-${i}`, x + 58, 430, 48, color, { lineColor: C.white, lineWidth: 2 });
    textBox(slide, `road-num-text-${i}`, num, x + 20, 396, 76, 70, {
      typeface: FONT.display,
      fontSize: 48,
      bold: true,
      color: C.white,
      alignment: "center",
      verticalAlignment: "middle",
    });
    segment(slide, `road-line-${i}`, x + 116, 429, 310, 4, color);
    textBox(slide, `road-head-${i}`, head, x, 512, 420, 48, {
      typeface: FONT.display,
      fontSize: 34,
      bold: true,
      color: C.cream,
    });
    textBox(slide, `road-body-${i}`, body, x, 584, 430, 130, {
      fontSize: 23,
      color: C.muted,
    });
    x += 560;
  });

  segment(slide, "road-ask-line", 120, 832, 540, 6, C.teal);
  textBox(slide, "road-ask", "Ask: use the live `/eraya` build as the demo spine, then swap demo facades for Casper testnet endpoints during the final integration pass.", 122, 858, 1340, 86, {
    typeface: FONT.display,
    fontSize: 34,
    bold: true,
    color: C.cream,
  });
  chip(slide, "road-live-chip", api.apiUrl, 122, 950, 930, C.ink2, C.muted);
  footer(slide, 7);
}

function build() {
  const presentation = Presentation.create({
    slideSize: { width: W, height: H },
  });
  slide1(presentation);
  slide2(presentation);
  slide3(presentation);
  slide4(presentation);
  slide5(presentation);
  slide6(presentation);
  slide7(presentation);
  return presentation;
}

async function saveBlob(blob, path) {
  if (typeof blob.save === "function") {
    await blob.save(path);
    return;
  }
  await writeFile(path, Buffer.from(await blob.arrayBuffer()));
}

async function renderSavedDeck(path) {
  const bytes = await readFile(path);
  const saved = await PresentationFile.importPptx(bytes);
  const previewPaths = [];
  for (let i = 0; i < saved.slides.count; i += 1) {
    const slide = saved.slides.getItem(i);
    const png = await saved.export({ slide, format: "png", scale: 1 });
    const pngPath = `${PREVIEW_DIR}/slide-${String(i + 1).padStart(2, "0")}.png`;
    await saveBlob(png, pngPath);
    previewPaths.push(pngPath);

    const layout = await saved.export({ slide, format: "layout" });
    await writeFile(`${LAYOUT_DIR}/slide-${String(i + 1).padStart(2, "0")}.json`, JSON.stringify(layout, null, 2));
  }
  return previewPaths;
}

async function main() {
  await mkdir("output", { recursive: true });
  await mkdir(PREVIEW_DIR, { recursive: true });
  await mkdir(LAYOUT_DIR, { recursive: true });

  const presentation = build();
  const pptx = await PresentationFile.exportPptx(presentation);
  await saveBlob(pptx, OUT);
  await copyFile(OUT, ROOT_COPY);

  const previewPaths = await renderSavedDeck(OUT);
  await writeFile(
    "scratch/build-report.json",
    JSON.stringify(
      {
        deck: OUT,
        rootCopy: ROOT_COPY,
        slideCount: presentation.slides.count,
        previews: previewPaths,
        source: "README.md, ERAYA_Casper_Advancement_Plan.md, live dashboard API",
      },
      null,
      2,
    ),
  );
  console.log(`Wrote ${OUT}`);
  console.log(`Copied ${ROOT_COPY}`);
  console.log(`Rendered ${previewPaths.length} saved-PPTX previews under ${PREVIEW_DIR}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
