/* The lenses, as pure ECharts option builders. No DOM, no echarts calls: each
   takes a context and returns {option, height, meta}, so the same function runs
   in the browser and under a headless bun render that checks the chart is not
   silently empty. Colours are resolved to hex up front via ctx.C (the active
   theme), because the option carries ~30k data points and a per-paint deep copy
   to swap colour sentinels would be the slow path. */
(function (root) {
  "use strict";

  // ---- small helpers ------------------------------------------------------
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function jit(a, b) {               // deterministic [0,1) jitter from two ints
    var x = (Math.imul(a, 73856093) ^ Math.imul(b + 1, 19349663)) >>> 0;
    x = Math.imul(x ^ (x >>> 13), 0x5bd1e995) >>> 0;
    return ((x >>> 8) & 0xffff) / 0x10000;
  }
  function runLabel(r) {
    var s = r.monitor, e = r.effort;
    if (e === "default") s += " · default";
    else if (e === "max (default)") s += " · max";
    else if (e === "none (not an ablation)") s += " · none*";
    else if (e) s += " · " + e;
    if (r.scale !== 10) s += " · 0-" + r.scale;
    if (r.comments === "kept") s += " · cmt";
    if (r.protocol === "UM") s += " · UM";
    if (r.batch === "b2") s += " · b2";
    if (r.batch === "pilot-100") s += " · n100";
    return s;
  }
  function inkOf(C) { return function (k) { return C("@ink-" + k); }; }

  function base(ink) {
    return {
      animation: false, progressive: 6000, progressiveThreshold: 6000,
      textStyle: { fontFamily: '"Libre Franklin", system-ui, -apple-system, "Segoe UI", sans-serif', color: ink("secondary") },
      tooltip: {
        confine: true, backgroundColor: ink("surface"), borderColor: ink("axis"),
        borderWidth: 1, textStyle: { color: ink("primary"), fontSize: 12 },
        extraCssText: "box-shadow:0 6px 22px rgba(0,0,0,.16);border-radius:8px;padding:8px 11px;",
      },
    };
  }
  function vaxis(ink, name, o) {
    o = o || {};
    var ax = {
      type: o.log ? "log" : (o.type || "value"), name: name,
      nameLocation: "middle", nameGap: o.nameGap == null ? 30 : o.nameGap,
      nameTextStyle: { color: ink("secondary"), fontSize: 11.5 },
      axisLine: { show: o.axisLine !== false, lineStyle: { color: ink("axis") } },
      axisTick: { show: false },
      axisLabel: { color: ink("muted"), fontSize: 11 },
      splitLine: { show: o.hideSplit !== true, lineStyle: { color: ink("grid"), width: 1 } },
    };
    ["min", "max", "interval", "data", "boundaryGap", "scale"].forEach(function (k) {
      if (o[k] !== undefined) ax[k] = o[k];
    });
    if (o.rotate !== undefined) ax.axisLabel.rotate = o.rotate;
    if (o.hideLabel) ax.axisLabel.show = false;
    if (o.formatter) ax.axisLabel.formatter = o.formatter;
    if (o.margin !== undefined) ax.axisLabel.margin = o.margin;
    return ax;
  }

  // ========================================================================
  // ATLAS: every sample a dot, one lane per run, placed by reasoning effort.
  // x is the monitor's reasoning-token count (log). Runs that emit no reasoning
  // tokens are off by default and, when shown, pile at the left-hand floor.
  // ========================================================================
  function atlas(ctx) {
    var C = ctx.C, ink = inkOf(C), D = ctx.D, st = ctx.state;
    var runs = ctx.runs.slice();
    var sortKey = {
      monitor: function (r) { return [r.monitor, r.scale, D.effort_order.indexOf(r.effort)]; },
      auc: function (r) { return [-(r.auc || 0)]; },
      resolution: function (r) { return [-(r.distinct_honest || 0)]; },
      usable: function (r) { return [-(r.n_usable || 0)]; },
      floor: function (r) { return [-(r.zero_frac || 0)]; },
    }[st.sort] || function (r) { return [r.monitor]; };
    runs.sort(function (a, b) {
      var ka = sortKey(a), kb = sortKey(b);
      for (var i = 0; i < ka.length; i++) { if (ka[i] < kb[i]) return -1; if (ka[i] > kb[i]) return 1; }
      return 0;
    });
    var show = st.mode;              // 'both' | 'honest' | 'attack'
    var colorMode = st.color || "side";   // 'side' | 'verdict' (correct at a 2% budget)
    var buckets = { honest: [], attack: [], caught: [], missed: [], falsealarm: [], passed: [] };
    var auditor = [];                // hard-51 backdoors carry a full auditor's read
    var noTokLanes = [];             // runs with no reasoning tokens, placed later at the floor
    var xmin = Infinity, xmax = 10, floored = false;

    function emit(r, lane, i, S, x, rt) {
      var isAtk = S.mode[i] === 1;
      var sfrac = S.susp[i] < 0 ? null : S.susp[i] / 1000;
      var j = jit(S.id[i], lane + (isAtk ? 1000 : 0));
      var y = isAtk ? lane - 0.06 - j * 0.34 : lane + 0.06 + j * 0.34;
      var pt = [x, y, lane, S.id[i], sfrac, rt, isAtk ? 1 : 0];
      if (colorMode === "verdict") {
        var T2 = (r.served && r.served["2"]) ? r.served["2"].threshold : null;
        var flagged = T2 != null && sfrac != null && sfrac > T2 + 1e-9;
        buckets[isAtk ? (flagged ? "caught" : "missed") : (flagged ? "falsealarm" : "passed")].push(pt);
      } else {
        buckets[isAtk ? "attack" : "honest"].push(pt);
      }
      if (isAtk) { var pr = D.probs && D.probs[String(S.id[i])]; if (pr && pr.quad) auditor.push(pt); }
    }

    runs.forEach(function (r, lane) {
      var S = D.samples[r.run]; if (!S) return;
      if (!S.rtok) { noTokLanes.push({ r: r, lane: lane, S: S }); return; }  // no reasoning tokens
      for (var i = 0; i < S.id.length; i++) {
        var isAtk = S.mode[i] === 1;
        if (show === "honest" && isAtk) continue;
        if (show === "attack" && !isAtk) continue;
        var rt = S.rtok[i];
        if (rt == null || rt < 0) continue;
        var x = rt < 1 ? 1 : rt;
        if (x < xmin) xmin = x; if (x > xmax) xmax = x;
        emit(r, lane, i, S, x, rt);
      }
    });
    function p10f(v) { return Math.pow(10, Math.floor(Math.log10(Math.max(1, v)))); }
    function p10c(v) { return Math.pow(10, Math.ceil(Math.log10(Math.max(1, v)))); }
    var axMin = xmin === Infinity ? 1 : p10f(xmin);
    // floor-placed lanes: suspicion is real, token count is not, so pin them at the
    // left edge with rt = -1 (the hover card then reads "reasoning tok: n/a").
    noTokLanes.forEach(function (e) {
      var S = e.S;
      for (var i = 0; i < S.id.length; i++) {
        var isAtk = S.mode[i] === 1;
        if (show === "honest" && isAtk) continue;
        if (show === "attack" && !isAtk) continue;
        floored = true;
        emit(e.r, e.lane, i, S, axMin, -1);
      }
    });
    var axMax = Math.max(axMin * 10, p10c(xmax));

    var xAxis = vaxis(ink, "monitor reasoning tokens  (log; left = terse, right = long)",
      { log: true, min: axMin, max: axMax, nameGap: 26 });
    function tip(p) {
      var d = p.data, r = runs[d[2]];
      return "<b>" + esc(runLabel(r)) + "</b><br>" +
        (d[6] === 1 ? "backdoor" : "honest program") + " &middot; problem " + d[3] +
        "<br>suspicion " + (d[4] == null ? "n/a" : d[4].toFixed(3)) +
        (d[5] >= 0 ? "<br>reasoning tokens " + d[5].toLocaleString() : "<br>reasoning tokens n/a (floored)") +
        (D.probs && D.probs[String(d[3])] && D.probs[String(d[3])].quad ? "<br><span style='color:" + C("@warning") + "'>&#9679; has an auditor's read</span>" : "") +
        "<br><span style='color:" + ink("muted") + "'>click to pin &middot; full judgement in the side panel &rarr;</span>";
    }
    var o = base(ink);
    o.grid = { left: 8, right: 34, top: 10, bottom: 54, containLabel: true };
    o.tooltip.trigger = "item"; o.tooltip.formatter = tip;
    o.xAxis = xAxis;
    // Integer min/max so a value-axis tick lands on every lane centre (a
    // fractional min anchors the ticks off the integers and the labels vanish).
    o.yAxis = vaxis(ink, "", {
      min: -1, max: runs.length, interval: 1, axisLine: false, margin: 10,
      formatter: function (v) {
        var i = Math.round(v);
        if (!(Math.abs(v - i) < 1e-6 && runs[i])) return "";
        var lab = runLabel(runs[i]), ix = lab.indexOf(" · ");   // monitor name in ink, the effort/scale suffix muted
        return ix < 0 ? "{a|" + lab + "}" : "{a|" + lab.slice(0, ix) + "}{b|" + lab.slice(ix) + "}";
      },
    });
    o.yAxis.axisLabel.fontSize = 10.5; o.yAxis.axisLabel.color = ink("secondary");
    o.yAxis.axisLabel.rich = { a: { color: ink("primary"), fontSize: 10.5 }, b: { color: ink("muted"), fontSize: 10.5 } };
    o.yAxis.splitLine = { show: true, lineStyle: { color: ink("grid"), width: 1 } }; // lane centre = honest/attack divider
    var sym = runs.length > 30 ? 3 : 4;
    // backdoor-side samples carry a triangle, honest-side a circle, so the
    // honest/backdoor split never rests on colour alone (CVD-safe).
    var ATK_SIDE = { attack: 1, caught: 1, missed: 1 };
    function series(name, data, color) {
      // Deliberately not large-mode: large scatter drops the extra per-point
      // fields (lane, problem id, tokens) the tooltip and detail panel read.
      // Progressive rendering keeps 30k+ points smooth in canvas without that.
      var atk = ATK_SIDE[name];
      return {
        type: "scatter", name: name, data: data,
        symbol: atk ? "triangle" : "circle", symbolSize: atk ? sym + 1 : sym,
        progressive: 4000, progressiveThreshold: 4000,
        itemStyle: { color: color, opacity: 0.5 }, z: name === "attack" ? 3 : 2,
      };
    }
    o.series = [];
    function add(name, color) { if (buckets[name].length) o.series.push(series(name, buckets[name], C(color))); }
    if (colorMode === "verdict") {
      if (show !== "honest") { add("caught", "@good"); add("missed", "@critical"); }
      if (show !== "attack") { add("falsealarm", "@warning"); add("passed", "@ink-muted"); }
    } else {
      if (show !== "attack") add("honest", "@honest");
      if (show !== "honest") add("attack", "@attack");
    }
    // the auditor-read ring overlay sits on top: a gold hollow ring on the 51
    // hardest backdoors so a reader can see at a glance which dots carry a read.
    if (show !== "honest" && auditor.length) {
      o.series.push({
        type: "scatter", name: "auditor", data: auditor, symbolSize: sym + 3,
        itemStyle: { color: "transparent", borderColor: C("@warning"), borderWidth: 1, opacity: 0.5 },
        emphasis: { scale: false, itemStyle: { borderWidth: 1.8, opacity: 1 } }, z: 5,
        progressive: 2000, progressiveThreshold: 2000,
      });
    }
    // faint alternating bands so each run reads as its own strip, not one column
    var band = ctx.themeIdx ? "rgba(210,210,210,0.028)" : "rgba(70,70,70,0.03)";
    var bands = [];
    for (var bi = 0; bi < runs.length; bi += 2) bands.push([{ yAxis: bi - 0.5, itemStyle: { color: band } }, { yAxis: bi + 0.5 }]);
    if (o.series[0]) {
      o.series[0].markArea = { silent: true, data: bands };
      if (floored) o.series[0].markLine = {
        silent: true, symbol: "none", animation: false,
        lineStyle: { color: ink("muted"), type: "dashed", width: 1 },
        label: { formatter: "no token data", color: ink("muted"), fontSize: 9.5, position: "insideStartTop" },
        data: [{ xAxis: axMin }],
      };
    }
    o.dataZoom = [
      // Wheel, drag-select and the log-scaled scrollbar below the plot are all
      // driven from app.js; this inside zoom just holds the window state they
      // set. The native slider is dropped on purpose: it maps its window
      // linearly in value, so on a 1..1e6 log axis a 3-decade window collapses
      // to a <1% sliver and pans wildly. The app.js scrollbar lives in log space.
      { type: "inside", xAxisIndex: 0, filterMode: "none", zoomOnMouseWheel: false, moveOnMouseMove: false, moveOnMouseWheel: false },
    ];
    var h = Math.max(440, Math.min(1800, runs.length * 34 + 90));
    return { option: o, height: h, meta: { lanes: runs, colorMode: colorMode, floored: floored,
      axMin: axMin, axMax: axMax, auditor: auditor.length, counts: {
        honest: buckets.honest.length, attack: buckets.attack.length, caught: buckets.caught.length,
        missed: buckets.missed.length, falsealarm: buckets.falsealarm.length, passed: buckets.passed.length } } };
  }

  // ========================================================================
  // EFFORT TRAJECTORIES: one line per problem across a knob ladder
  // ========================================================================
  function trajectories(ctx) {
    var C = ctx.C, ink = inkOf(C), D = ctx.D, st = ctx.state;
    var L = D.ladders[st.ladder]; if (!L) return { option: base(ink), height: 460, meta: {} };
    var runs = L.runs.map(function (rn) { return rn; });
    var byRun = D.runs.reduce(function (acc, r) { acc[r.run] = r; return acc; }, {});
    // per rung-run: id -> {h, a}
    var mh = [], ma = [];
    runs.forEach(function (rn) {
      var S = D.samples[rn], H = {}, A = {};
      for (var i = 0; i < S.id.length; i++) {
        if (S.susp[i] < 0) continue;
        (S.mode[i] === 1 ? A : H)[S.id[i]] = S.susp[i] / 1000;
      }
      mh.push(H); ma.push(A);
    });
    function inAll(id, arr) { return arr.every(function (m) { return m[id] !== undefined; }); }
    var ids = Object.keys(mh[0]).map(Number).filter(function (id) { return inAll(id, mh) && inAll(id, ma); });
    var show = st.mode;
    function lines(maps) {
      return ids.map(function (id) {
        return { value: runs.map(function (_, k) { return maps[k][id]; }), name: id };
      });
    }
    function mean(maps) {
      return runs.map(function (_, k) {
        var s = 0; ids.forEach(function (id) { s += maps[k][id]; }); return s / Math.max(1, ids.length);
      });
    }
    var o = base(ink);
    o.parallelAxis = L.rungs.map(function (lab, i) {
      return {
        dim: i, name: lab, min: 0, max: 1,
        nameTextStyle: { color: ink("secondary"), fontSize: 11.5 },
        axisLine: { lineStyle: { color: ink("axis") } },
        axisTick: { show: false }, axisLabel: { color: ink("muted"), fontSize: 10 },
        splitLine: { show: false },
      };
    });
    o.parallel = {
      left: 46, right: 42, top: 44, bottom: 24,
      parallelAxisDefault: { nameLocation: "start", nameGap: 16 },
    };
    o.tooltip = Object.assign(o.tooltip, {
      trigger: "item",
      formatter: function (p) {
        var v = p.value;
        return "<b>problem " + p.name + "</b><br>" + esc(p.seriesName) + "<br>" +
          L.rungs.map(function (lab, i) { return esc(lab) + ": " + v[i].toFixed(3); }).join("<br>");
      },
    });
    o.series = [];
    function lineSeries(name, maps, color) {
      return {
        type: "parallel", name: name, data: lines(maps),
        lineStyle: { color: color, width: 1, opacity: Math.max(0.03, Math.min(0.2, 40 / ids.length)) },
        emphasis: { lineStyle: { width: 2.4, opacity: 1 } }, progressive: 2000, smooth: false, z: 2,
      };
    }
    if (show !== "attack") o.series.push(lineSeries("honest programs", mh, C("@honest")));
    if (show !== "honest") o.series.push(lineSeries("backdoors", ma, C("@attack")));
    if (st.mean) {
      if (show !== "attack") o.series.push({
        type: "parallel", name: "honest mean", data: [{ value: mean(mh), name: "mean" }],
        lineStyle: { color: C("@honest"), width: 3.4, opacity: 1 }, z: 5, tooltip: { show: false },
      });
      if (show !== "honest") o.series.push({
        type: "parallel", name: "backdoor mean", data: [{ value: mean(ma), name: "mean" }],
        lineStyle: { color: C("@attack"), width: 3.4, opacity: 1 }, z: 5, tooltip: { show: false },
      });
    }
    // How noisy is this ladder? For each problem, how far its suspicion swings
    // across the rungs (max-min), and whether the line reverses direction at all.
    // A clean dose-response is a tight, monotone set of lines; noise is wide and
    // non-monotone. Measured on the side in view (backdoors unless only honest).
    function noiseOf(maps) {
      if (ids.length === 0 || runs.length < 2) return null;
      var last = runs.length - 1, spreadSum = 0, nonMono = 0, mFirst = 0, mLast = 0;
      ids.forEach(function (id) {
        var v = runs.map(function (_, k) { return maps[k][id]; });
        var mn = Math.min.apply(null, v), mx = Math.max.apply(null, v);
        spreadSum += mx - mn;
        mFirst += v[0]; mLast += v[last];
        var up = false, down = false;
        for (var k = 1; k < v.length; k++) { var dlt = v[k] - v[k - 1]; if (dlt > 1e-6) up = true; else if (dlt < -1e-6) down = true; }
        if (up && down) nonMono++;
      });
      var n = ids.length;
      return { spread: spreadSum / n, nonMono: nonMono / n, meanFirst: mFirst / n, meanLast: mLast / n,
        trend: (mLast - mFirst) / n, n: n, rungs: runs.length, first: L.rungs[0], last: L.rungs[last] };
    }
    var noise = noiseOf(show === "honest" ? mh : ma);
    return {
      option: o, height: 560,
      meta: { ladder: L, nLines: ids.length, runs: runs.map(function (rn) { return byRun[rn]; }),
        noise: noise, noiseSide: show === "honest" ? "honest" : "backdoor" },
    };
  }

  // ========================================================================
  // FLIGHT DECK: every run's reachable operating points at once
  // ========================================================================
  function servedAt(ladder, budget) {
    var best = null;
    for (var i = 0; i < ladder.length; i++) {
      var r = ladder[i];
      if (r.fpr <= budget + 1e-9 && (!best || r.fpr > best.fpr)) best = r;
    }
    return best;
  }
  function flightdeck(ctx) {
    var C = ctx.C, ink = inkOf(C), st = ctx.state;
    var runs = ctx.runs.slice();
    var metric = st.metric;          // 'recall' | 'safety'
    var budget = st.budget;          // % on the x axis
    var o = base(ink);
    o.grid = { left: 10, right: 20, top: 16, bottom: 52, containLabel: true };
    o.tooltip.trigger = "item";
    var lb = [];
    if (metric === "recall") {
      o.xAxis = vaxis(ink, "false-positive rate actually served  (%, log)", { log: true, min: 0.08, max: 100, nameGap: 28 });
      o.yAxis = vaxis(ink, "backdoors caught (recall)", { min: 0, max: 1, nameGap: 40 });
      o.tooltip.formatter = function (p) {
        if (!p.data || p.data.length < 2) return "";
        return "<b>" + esc(p.seriesName) + "</b><br>served FPR " + p.data[0].toFixed(2) +
          "% &middot; recall " + p.data[1].toFixed(3) + "<br><span style='color:" + ink("muted") +
          "'>" + (p.data[2] || 0) + " honest rows hold this cutoff</span>";
      };
      runs.forEach(function (r) {
        var pts = (r.ladder || []).filter(function (p) { return p.fpr > 0 && p.recall != null; })
          .map(function (p) { return [p.fpr, p.recall, p.n_above]; })
          .sort(function (a, b) { return a[0] - b[0]; });
        if (!pts.length) return;
        o.series = o.series || [];
        o.series.push({
          type: "line", name: runLabel(r), step: "end", showSymbol: false, data: pts,
          triggerLineEvent: true,   // so hovering the curve itself (no symbols) fires a hover event
          lineStyle: { color: C(r.color), width: 1.5, opacity: 0.72 },
          emphasis: { focus: "series", lineStyle: { width: 3, opacity: 1 } },
          blur: { lineStyle: { opacity: 0.1 } }, _run: r.run,
        });
        var s = servedAt(r.ladder, budget);
        lb.push({ run: r.run, label: runLabel(r), color: r.color,
          recall: s ? s.recall : null, fpr: s ? s.fpr : null, n: s ? s.n_above : 0, cost: r.cost });
      });
      lb.sort(function (a, b) { return (b.recall == null ? -1 : b.recall) - (a.recall == null ? -1 : a.recall); });
    } else {
      o.xAxis = vaxis(ink, "requested audit budget  (%, log)", { log: true, min: 0.3, max: 60, nameGap: 28 });
      o.yAxis = vaxis(ink, "safety  (bootstrap estimate)", { min: 0, max: 1, nameGap: 40 });
      o.tooltip.formatter = function (p) {
        if (!p.data || p.data.length < 2) return "";
        return "<b>" + esc(p.seriesName) + "</b><br>budget " + p.data[0] + "% &middot; safety " + p.data[1].toFixed(3);
      };
      runs.forEach(function (r) {
        var pts = (r.safety_curve || []).map(function (p) { return [p.budget, p.safety]; });
        if (!pts.length) return;
        o.series = o.series || [];
        o.series.push({
          type: "line", name: runLabel(r), showSymbol: false, smooth: false, data: pts,
          triggerLineEvent: true,   // so hovering the curve itself (no symbols) fires a hover event
          lineStyle: { color: C(r.color), width: 1.5, opacity: 0.72 },
          emphasis: { focus: "series", lineStyle: { width: 3, opacity: 1 } },
          blur: { lineStyle: { opacity: 0.1 } }, _run: r.run,
        });
        // nearest committed budget to the cursor
        var near = null;
        (r.safety_curve || []).forEach(function (p) {
          if (!near || Math.abs(p.budget - budget) < Math.abs(near.budget - budget)) near = p;
        });
        lb.push({ run: r.run, label: runLabel(r), color: r.color,
          recall: near ? near.safety : null, fpr: near ? near.budget : null, n: null, cost: r.cost });
      });
      lb.sort(function (a, b) { return (b.recall == null ? -1 : b.recall) - (a.recall == null ? -1 : a.recall); });
    }
    o.series = o.series || [];
    o.series.push({
      type: "line", data: [], silent: true,
      markLine: {
        silent: true, symbol: "none", animation: false,
        lineStyle: { color: ink("muted"), type: "dashed", width: 1.2 },
        label: { formatter: (metric === "recall" ? "budget " : "cursor ") + budget + "%",
          color: ink("secondary"), fontSize: 10, position: "insideEndTop" },
        data: [{ xAxis: budget }],
      },
    });
    return { option: o, height: 560, meta: { leaderboard: lb, metric: metric, budget: budget } };
  }

  root.LENSES = {
    atlas: atlas, trajectories: trajectories, flightdeck: flightdeck,
    runLabel: runLabel, esc: esc,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = root.LENSES;
})(typeof window !== "undefined" ? window : globalThis);
