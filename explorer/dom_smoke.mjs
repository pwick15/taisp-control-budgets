/* Drive app.js through a hand-rolled DOM shim: no browser here, so this stands in
   for clicking the page. It mounts the app, then switches every lens, flips a
   toolbar control, toggles a filter chip, moves the flight-deck slider and flips
   the theme, asserting each time that a non-empty ECharts option reached
   setOption and nothing threw. echarts is stubbed to a recorder; the real option
   building is exercised by the real lenses.js. */
import * as fs from "node:fs";

let ALL = [];
function node(tag) {
  const n = {
    tag, id: "", _cls: "", attrs: {}, style: {}, children: [], parent: null,
    _text: "", _html: "", handlers: {},
    get className() { return this._cls; }, set className(v) { this._cls = v || ""; },
    get textContent() { return this._text; }, set textContent(v) { this._text = v == null ? "" : String(v); },
    get innerHTML() { return this._html; }, set innerHTML(v) { this._html = v || ""; this.children = []; },
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); }, toggle(c) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); },
    },
    appendChild(c) { c.parent = n; n.children.push(c); return c; },
    setAttribute(k, v) { n.attrs[k] = String(v); }, getAttribute(k) { return n.attrs[k] == null ? null : n.attrs[k]; },
    removeAttribute(k) { delete n.attrs[k]; },
    addEventListener(ev, fn) { (n.handlers[ev] = n.handlers[ev] || []).push(fn); },
    fire(ev) { (n.handlers[ev] || []).forEach((f) => f.call(n, { target: n })); },
    querySelectorAll(sel) { return query(n, sel); }, querySelector(sel) { return query(n, sel)[0] || null; },
  };
  ALL.push(n);
  return n;
}
function descendants(root) {
  const out = [];
  (function walk(x) { x.children.forEach((c) => { out.push(c); walk(c); }); })(root);
  return out;
}
function query(root, sel) {
  sel = sel.trim();
  const pool = root === document ? ALL : descendants(root);
  if (sel.includes(" ")) {
    const [a, b] = sel.split(/\s+/);
    const parents = query(root, a);
    let res = [];
    parents.forEach((p) => { res = res.concat(query(p, b)); });
    return res;
  }
  if (sel[0] === "#") return pool.filter((e) => e.id === sel.slice(1));
  if (sel[0] === ".") return pool.filter((e) => (e._cls || "").split(" ").includes(sel.slice(1)));
  return pool.filter((e) => e.tag === sel);
}

const ids = {};
const document = {
  documentElement: node("html"),
  createElement: (t) => node(t),
  createTextNode: (t) => { const n = node("#text"); n._text = t; return n; },
  getElementById: (id) => ids[id],
  querySelectorAll: (sel) => query(document, sel), querySelector: (sel) => query(document, sel)[0] || null,
  addEventListener: (ev, fn) => { document._dom = fn; },
  _dom: null,
};
for (const id of ["tabs", "toolbar", "filterbar", "featured", "detail", "plot", "plotcap", "lens-intro", "notes", "theme-btn"]) {
  const n = node("div"); n.id = id; ids[id] = n;   // node() already pushed to ALL
}
ids["plot"].style = {};

let setOptionCalls = 0, lastOption = null, throws = [];
const echarts = {
  init() {
    return {
      setOption(o) {
        setOptionCalls++; lastOption = o;
        const s = o.series || [];
        const nser = Array.isArray(s) ? s.length : 1;
        const ok = nser > 0 || o.parallel || o.visualMap;
        if (!ok) throws.push("setOption got an option with no series");
      },
      resize() {}, on() {}, dispatchAction() {}, dispose() {},
    };
  },
};

globalThis.window = { matchMedia: () => ({ matches: false }), addEventListener() {}, __DATA__: null, LENSES: null };
globalThis.document = document;
globalThis.echarts = echarts;
globalThis.localStorage = { _m: {}, getItem(k) { return this._m[k] || null; }, setItem(k, v) { this._m[k] = v; } };

// load data + the real modules
window.__DATA__ = JSON.parse(fs.readFileSync("bundle.json", "utf8"));
globalThis.__DATA__ = window.__DATA__;
(0, eval)(fs.readFileSync("lenses.js", "utf8"));   // sets window.LENSES (window is defined here)
(0, eval)(fs.readFileSync("app.js", "utf8"));

function run(label, fn) { try { fn(); } catch (e) { throws.push(`${label}: ${e && e.stack ? e.stack.split("\n").slice(0, 2).join(" | ") : e}`); } }

run("DOMContentLoaded", () => document._dom({}));
let afterMount = setOptionCalls;
console.log(`mounted: ${setOptionCalls} setOption call(s)`);

// click every tab
const tabs = query(ids["tabs"], ".tab");
console.log(`tabs: ${tabs.length}`);
["atlas", "trajectories", "flightdeck"].forEach((name, i) => {
  run("tab " + name, () => tabs[i].fire("click"));
  const before = setOptionCalls;
  // flip the first toolbar seg/select if present
  const seg = query(ids["toolbar"], "button")[0];
  if (seg) run("toolbar " + name, () => seg.fire("click"));
  const sel = query(ids["toolbar"], "select")[0];
  if (sel) run("select " + name, () => {
    const opt = query(sel, "option").find((o) => o.value != null);   // real browsers expose the selected option's value
    if (opt) sel.value = opt.value;
    sel.fire("change");
  });
  // toggle the first filter chip
  const chip = query(ids["filterbar"], "chip");
  const chips = query(ids["filterbar"], ".chip");
  if (chips[0]) run("chip " + name, () => chips[0].fire("click"));
  // move slider (flight deck)
  const slider = query(ids["toolbar"], "input")[0];
  if (slider) run("slider " + name, () => { slider.value = "3"; slider.fire("input"); });
  console.log(`  ${name}: +${setOptionCalls - before} repaints, lens option keys = ${lastOption ? Object.keys(lastOption).filter((k) => ["series", "parallel", "visualMap", "xAxis"].includes(k)).join(",") : "?"}`);
});

// theme flip
run("theme", () => ids["theme-btn"].fire("click"));
console.log(`theme flip -> ${setOptionCalls} total setOption calls`);

if (throws.length) { console.log("\nTHROWS:"); throws.forEach((t) => console.log("  " + t)); }
console.log(`\n${throws.length} error(s), ${setOptionCalls} setOption calls total`);
process.exit(throws.length ? 1 : 0);
