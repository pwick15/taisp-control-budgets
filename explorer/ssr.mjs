/* Headless render of every lens at a few states, both themes, through the
   vendored ECharts. Stands in for looking at the page: a lens that throws or
   draws almost nothing is the failure no one here can see. */
import * as fs from "node:fs";

const echarts = await import("./vendor/echarts-5.5.1.min.js");
const EC = echarts.default ?? globalThis.echarts ?? echarts;

const bundle = JSON.parse(fs.readFileSync("bundle.json", "utf8"));
(0, eval)(fs.readFileSync("lenses.js", "utf8"));
const LENSES = globalThis.LENSES;
const THEME = bundle.theme;

function makeC(idx) { return (tok) => (THEME[tok] ? THEME[tok][idx] : tok); }
function defaultRuns() {
  return bundle.runs.filter((r) => r.scale === 10 && r.comments === "stripped" && r.batch === "b1");
}

const CASES = [
  ["atlas", { mode: "both", sort: "monitor" }],
  ["atlas", { mode: "attack", sort: "auc" }],
  ["atlas", { mode: "both", sort: "resolution", noTok: true }],
  ["atlas", { mode: "both", sort: "monitor", color: "verdict" }],
  ["trajectories", { ladder: pickLadder("effort"), mode: "both", mean: true }],
  ["trajectories", { ladder: pickLadder("scale"), mode: "attack", mean: false }],
  ["trajectories", { ladder: pickLadder("comments"), mode: "both", mean: true }],
  ["flightdeck", { metric: "recall", budget: 2 }],
  ["flightdeck", { metric: "safety", budget: 2 }],
];
function pickLadder(kind) {
  let best = -1, bi = 0;
  bundle.ladders.forEach((L, i) => { if (L.kind === kind && L.runs.length > best) { best = L.runs.length; bi = i; } });
  return bi;
}

let fail = 0, warn = 0;
for (const idx of [0, 1]) {
  for (const [lens, state] of CASES) {
    let runs = defaultRuns();
    if (lens === "atlas") {
      const withTok = runs.filter((r) => r.has_rtok);
      runs = state.noTok ? withTok.concat(runs.filter((r) => !r.has_rtok)) : withTok;
    }
    const ctx = { D: bundle, C: makeC(idx), themeIdx: idx, runs, state, filters: {} };
    const label = `${lens}:${JSON.stringify(state)} th=${idx}`;
    let svg = "", err = null, h = 0;
    try {
      const built = LENSES[lens](ctx);
      h = built.height || 600;
      const chart = EC.init(null, null, { renderer: "svg", ssr: true, width: 1200, height: h });
      chart.setOption(built.option);
      svg = chart.renderToSVGString();
      chart.dispose();
    } catch (e) { err = String(e && e.stack ? e.stack.split("\n").slice(0, 3).join(" | ") : e); }
    if (err) { fail++; console.log(`  [FAIL] ${label}: ${err}`); continue; }
    const marks = (svg.match(/<(path|rect|circle|polyline|polygon|image|line)\b/g) || []).length;
    const texts = (svg.match(/<text\b/g) || []).length;
    if (marks < 8) { warn++; console.log(`  [EMPTY?] ${label}: ${marks} marks, ${texts} texts`); }
    else console.log(`  [ok]    ${label}: ${marks} marks, ${texts} texts, ${(svg.length / 1024).toFixed(0)} kB, h=${h}`);
  }
}
console.log(`\n${CASES.length} cases x 2 themes: ${fail} failed, ${warn} suspiciously empty`);
process.exit(fail > 0 ? 1 : 0);
