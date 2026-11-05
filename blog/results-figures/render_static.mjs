// Static copies of every figure: static/<id>.svg (vector, via ECharts server-side rendering)
// and static/<id>.png (2x, via a headless Chromium browser screenshot of the SVG).
//
//   node blog/results-figures/render_static.mjs
//
// Uses the light theme and each figure's default dial setting. Run build.py first.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const echarts = require(join(HERE, "assets", "echarts-5.5.1.min.js"));
const { theme, figures } = JSON.parse(readFileSync(join(HERE, "figures.json"), "utf8"));
const OUT = join(HERE, "static");
mkdirSync(OUT, { recursive: true });
const WIDTH = 960;

const FN = /^\s*(function\s*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)/;
function resolve(n) {
  if (typeof n === "string") {
    if (theme[n]) return theme[n][0];
    if (FN.test(n)) { try { return new Function("return (" + n + ")")(); } catch { return n; } }
    return n;
  }
  if (Array.isArray(n)) return n.map(resolve);
  if (n && typeof n === "object") {
    return Object.fromEntries(Object.entries(n).map(([k, v]) =>
      // Double quotes in a font stack end up inside an SVG style attribute and break the XML.
      [k, k === "fontFamily" && typeof v === "string" ? v.replace(/"/g, "'") : resolve(v)]));
  }
  return n;
}

const BROWSERS = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
];
const browser = BROWSERS.find((b) => existsSync(b));
if (!browser) console.warn("No Chromium-based browser found: writing SVG only.");

for (const f of figures) {
  let opt = { ...f.option };
  if (f.dial) Object.assign(opt, f.dial.frames[f.dial.initial] || {});
  opt = resolve(opt);
  opt.animation = false;
  opt.backgroundColor = "#ffffff";
  if (opt.legend && !Array.isArray(opt.legend)) opt.legend = { ...opt.legend, type: "plain" };
  const height = f.height || 440;
  const chart = echarts.init(null, null, { renderer: "svg", ssr: true, width: WIDTH, height });
  chart.setOption(opt);
  const svg = chart.renderToSVGString();
  chart.dispose();
  const svgPath = join(OUT, `${f.id}.svg`);
  writeFileSync(svgPath, svg);
  if (browser) {
    execFileSync(browser, [
      "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
      `--window-size=${WIDTH},${height}`, `--screenshot=${join(OUT, `${f.id}.png`)}`, pathToFileURL(svgPath).href,
    ], { stdio: "ignore", timeout: 60000 });
  }
  console.log(`${f.id}: svg${browser ? " + png" : ""}`);
}
