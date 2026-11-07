(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('viz-data').textContent);
  var FIGS = {};
  D.figures.forEach(function (f) { FIGS[f.id] = f; });
  var FONT = "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif";
  var EXPORT_W = 960;
  var FN = /^\s*(function\s*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)/;
  var TOK = /@[a-z][a-z0-9-]*(?::-?[0-9.]+)?(?:\/[0-9.]+)?/g;
  var FORM = /^(@[a-z][a-z0-9-]*)(?::(-?[0-9.]+))?(?:\/([0-9.]+))?$/;

  // ---------------------------------------------------------------- colour tokens

  function hexToRgb(h) {
    h = h.replace('#', '');
    if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
    return [0, 2, 4].map(function (i) { return parseInt(h.slice(i, i + 2), 16); });
  }
  function rgbToHex(c) {
    return '#' + c.map(function (v) {
      return Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0');
    }).join('');
  }
  function toLin(v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  function fromLin(v) { v = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055; return v * 255; }
  function toOklab(rgb) {
    var r = toLin(rgb[0]), g = toLin(rgb[1]), b = toLin(rgb[2]);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function fromOklab(c) {
    var l = Math.pow(c[0] + 0.3963377774 * c[1] + 0.2158037573 * c[2], 3);
    var m = Math.pow(c[0] - 0.1055613458 * c[1] - 0.0638541728 * c[2], 3);
    var s = Math.pow(c[0] - 0.0894841775 * c[1] - 1.2914855480 * c[2], 3);
    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s].map(fromLin);
  }
  function interp(stops, x) {
    x = Math.max(0, Math.min(1, x));
    var n = stops.length - 1, i = Math.min(n - 1, Math.floor(x * n)), f = x * n - i;
    var a = toOklab(hexToRgb(stops[i])), b = toOklab(hexToRgb(stops[i + 1]));
    return rgbToHex(fromOklab([0, 1, 2].map(function (k) { return a[k] + f * (b[k] - a[k]); })));
  }
  function rgba(hex, a) { var c = hexToRgb(hex); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }

  function tokenValue(tok, mode) {
    var m = FORM.exec(tok);
    if (!m) return null;
    var hex;
    if (m[2] !== undefined) {
      var sc = D.theme.scales[m[1].slice(1)];
      if (!sc) return null;
      hex = interp(sc[mode ? 'dark' : 'light'], parseFloat(m[2]));
    } else {
      var v = D.theme.tokens[m[1]];
      if (!v) return null;
      hex = v[mode];
    }
    return m[3] !== undefined ? rgba(hex, parseFloat(m[3])) : hex;
  }

  // Swap tokens for colours and function strings for functions, for one theme (0 light, 1 dark).
  function resolve(n, mode) {
    if (typeof n === 'string') {
      if (n.charCodeAt(0) === 64) { var v = tokenValue(n, mode); if (v !== null) return v; }
      if (FN.test(n)) {
        var src = n.replace(TOK, function (t) { var c = tokenValue(t, mode); return c === null ? t : c; });
        try { return new Function('return (' + src + ')')(); } catch (e) { console.error('viz: bad function string: ' + e.message); return undefined; }
      }
      return n;
    }
    if (Array.isArray(n)) return n.map(function (x) { return resolve(x, mode); });
    if (n && typeof n === 'object') { var o = {}; for (var k in n) o[k] = resolve(n[k], mode); return o; }
    return n;
  }

  // ---------------------------------------------------------------- chart theme

  function themeFor(mode) {
    var t = function (n) { return tokenValue(n, mode); };
    function axis(extra) {
      var base = {
        axisLine: { show: true, lineStyle: { color: t('@ink-axis'), width: 1 } },
        axisTick: { show: false },
        axisLabel: { color: t('@ink-muted'), fontSize: 12, margin: 10 },
        splitLine: { show: true, lineStyle: { color: t('@ink-grid'), width: 1, type: 'solid' } },
        splitArea: { show: false },
        nameTextStyle: { color: t('@ink-secondary'), fontSize: 12, fontWeight: 500 }
      };
      for (var k in extra) base[k] = extra[k];
      return base;
    }
    return {
      color: ['@s0', '@s1', '@s2', '@s3', '@s4', '@s5', '@s6', '@s7'].map(t),
      backgroundColor: 'transparent',
      textStyle: { fontFamily: FONT, color: t('@ink-secondary'), fontSize: 12 },
      legend: {
        icon: 'roundRect', itemWidth: 12, itemHeight: 8, itemGap: 18,
        textStyle: { color: t('@ink-secondary'), fontSize: 12 }, inactiveColor: t('@ink-axis'),
        pageTextStyle: { color: t('@ink-muted') }, pageIconColor: t('@ink-secondary'), pageIconInactiveColor: t('@ink-axis')
      },
      tooltip: {
        backgroundColor: t('@ink-surface'), borderColor: t('@ink-grid'), borderWidth: 1, padding: [8, 12],
        textStyle: { color: t('@ink-primary'), fontSize: 12, fontFamily: FONT },
        extraCssText: 'border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.14);line-height:1.5;'
      },
      categoryAxis: axis({ splitLine: { show: false } }),
      valueAxis: axis({ axisLine: { show: false } }),
      logAxis: axis({ axisLine: { show: false } }),
      timeAxis: axis({}),
      line: { symbol: 'circle', symbolSize: 7, lineStyle: { width: 2 } },
      scatter: { symbolSize: 9 },
      bar: { barMaxWidth: 44 }
    };
  }
  echarts.registerTheme('viz-light', themeFor(0));
  echarts.registerTheme('viz-dark', themeFor(1));

  // ---------------------------------------------------------------- theme mode

  var pref = 'auto';
  try { pref = localStorage.getItem('viz-theme') || 'auto'; } catch (e) { /* private window */ }
  var media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function mode() {
    var a = document.documentElement.getAttribute('data-theme');
    if (a === 'dark') return 1;
    if (a === 'light') return 0;
    return media && media.matches ? 1 : 0;
  }
  function applyPref() {
    if (pref === 'auto') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', pref);
    document.querySelectorAll('#theme button').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.t === pref));
    });
  }

  // ---------------------------------------------------------------- live charts

  var steps = {};
  var live = {};
  function stepOf(f) { return steps[f.id] != null ? steps[f.id] : (f.dial ? (f.dial.initial || 0) : 0); }
  function optionFor(f, step, m) {
    var o = {};
    for (var k in f.option) o[k] = f.option[k];
    if (f.dial && f.dial.frames) { var fr = f.dial.frames[step] || {}; for (var j in fr) o[j] = fr[j]; }
    o = resolve(o, m);
    if (o.graphic) o.graphic = graphicFont(o.graphic);
    return o;
  }
  // Graphic text doesn't inherit the theme's textStyle, so give it the theme font here (figures may not set fonts).
  function graphicFont(g) {
    if (Array.isArray(g)) return g.map(graphicFont);
    if (!g || typeof g !== 'object') return g;
    var c = {};
    for (var k in g) c[k] = g[k];
    if (c.type === 'text') {
      c.style = Object.assign({}, c.style);
      if (!c.style.fontFamily && !c.style.font) c.style.fontFamily = FONT;
    }
    if (c.children) c.children = graphicFont(c.children);
    if (c.elements) c.elements = graphicFont(c.elements);
    return c;
  }
  function mount(el) {
    var f = FIGS[el.dataset.id];
    if (!f) return;
    if (f.kind === 'html') { mountHtml(el, f); return; }
    if (live[f.id]) live[f.id].inst.dispose();
    var m = mode();
    var inst = echarts.init(el, m ? 'viz-dark' : 'viz-light', { renderer: 'canvas' });
    try { inst.setOption(optionFor(f, stepOf(f), m), true); } catch (e) { console.error('viz: ' + f.id + ': ' + e.message); }
    live[f.id] = { inst: inst, el: el };
  }
  function mountHtml(el, f) {
    var fr = el.querySelector('iframe');
    var attr = mode() ? 'dark' : 'light';
    fr.srcdoc = f.html.replace(/<html([^>]*)>/i, function (all, rest) {
      return '<html' + rest.replace(/\sdata-theme="[^"]*"/i, '') + ' data-theme="' + attr + '">';
    });
    live[f.id] = { inst: null, el: el, html: true };
  }
  // A dial figure "glides" when every series in its frames has an id (A05 does): then swapping only the
  // keys the dial changes lets each dot or bar move to its new place. Any other dial figure redraws
  // from scratch, as before, because a series without an id would re-run its entry animation.
  function dialKeys(f) {
    var keys = {};
    ((f.dial && f.dial.frames) || []).forEach(function (fr) { for (var k in fr) keys[k] = true; });
    return Object.keys(keys);
  }
  function glides(f) {
    var frames = (f.dial && f.dial.frames) || [], any = false;
    var ok = frames.every(function (fr) {
      return (fr.series || []).every(function (s) { any = true; return s.id != null; });
    });
    return ok && any;
  }
  function repaint(id) {
    var f = FIGS[id], L = live[id];
    if (!L || L.html) return;
    if (glides(f)) L.inst.setOption(optionFor(f, stepOf(f), mode()), { replaceMerge: dialKeys(f) });
    else L.inst.setOption(optionFor(f, stepOf(f), mode()), true);
  }
  function remountAll() { Object.keys(live).forEach(function (id) { mount(live[id].el); }); }

  // ---------------------------------------------------------------- export

  // Render a figure off screen at the export width, in the given theme.
  function renderAt(f, step, m, renderer) {
    var div = document.createElement('div');
    div.style.cssText = 'position:fixed;left:-30000px;top:0;width:' + EXPORT_W + 'px;height:' + f.height + 'px;';
    document.body.appendChild(div);
    var inst = echarts.init(div, m ? 'viz-dark' : 'viz-light', { renderer: renderer, width: EXPORT_W, height: f.height });
    var o = optionFor(f, step, m);
    o.animation = false;
    o.backgroundColor = tokenValue('@ink-surface', m);
    inst.setOption(o, true);
    return { inst: inst, done: function () { inst.dispose(); div.remove(); } };
  }
  function pngURL(f, step, m, ratio) {
    var r = renderAt(f, step, m, 'canvas');
    try { return r.inst.getDataURL({ type: 'png', pixelRatio: ratio || 2 }); } finally { r.done(); }
  }
  function svgText(f, step, m) {
    var r = renderAt(f, step, m, 'svg');
    try {
      var s = r.inst.renderToSVGString();
      var face = '<defs><style>@font-face{font-family:"Inter";src:url(data:font/woff2;base64,' + D.font +
        ') format("woff2");font-weight:100 900;}</style></defs>';
      return s.replace(/<svg[^>]*>/, function (open) { return open + face; });
    } finally { r.done(); }
  }
  function csv(t) {
    function q(v) {
      if (v === null || v === undefined) return '';
      var s = String(v);
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }
    return [t.columns.map(q).join(',')].concat(t.rows.map(function (r) { return r.map(q).join(','); })).join('\n') + '\n';
  }
  function save(blob, name) {
    var url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 4000);
  }
  function dataURLBlob(u) { return fetch(u).then(function (r) { return r.blob(); }); }
  function fileName(f, step, m) {
    var slug = (f.path || '').split('/').pop() || f.id;
    var dial = f.dial ? '-' + String(f.dial.steps[step]).replace(/[^A-Za-z0-9.]+/g, '') : '';
    return slug + dial + (m ? '-dark' : '');
  }
  // ---------------------------------------------------------------- GIF export

  // A GIF steps through every dial position and back to the start, holding each one. For a figure that
  // glides (see glides()), it also records the movement between positions; others cut straight across.
  var GIF_HOLD = 1600, GIF_TWEEN = 750, GIF_TICK = 50, GIF_RATIO = 1;
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function gifFrames(f, m) {
    var n = f.dial ? f.dial.steps.length : 1;
    var div = document.createElement('div');
    div.style.cssText = 'position:fixed;left:-30000px;top:0;width:' + EXPORT_W + 'px;height:' + f.height + 'px;';
    document.body.appendChild(div);
    var inst = echarts.init(div, m ? 'viz-dark' : 'viz-light',
      { renderer: 'canvas', width: EXPORT_W, height: f.height, devicePixelRatio: GIF_RATIO });
    var bg = tokenValue('@ink-surface', m), keys = dialKeys(f), tween = glides(f), frames = [];
    function opt(step, animate) {
      var o = optionFor(f, step, m);
      o.backgroundColor = bg;
      o.animation = animate;
      o.animationDurationUpdate = GIF_TWEEN;
      o.animationEasingUpdate = o.animationEasingUpdate || 'cubicOut';
      return o;
    }
    function grab(delay) {
      var c = inst.getRenderedCanvas({ pixelRatio: GIF_RATIO, backgroundColor: bg });
      frames.push({ data: c.getContext('2d').getImageData(0, 0, c.width, c.height).data, w: c.width, h: c.height, delay: delay });
    }
    var chain = Promise.resolve().then(function () { inst.setOption(opt(0, false), true); grab(GIF_HOLD); });
    for (var i = 1; i <= n; i++) {
      (function (step, last) {
        chain = chain.then(function () {
          if (!tween) return;
          inst.setOption(opt(step, true), { replaceMerge: keys });
          var t0 = performance.now();
          function tick() {
            return sleep(GIF_TICK).then(function () {
              if (performance.now() - t0 >= GIF_TWEEN) return;
              grab(GIF_TICK);
              return tick();
            });
          }
          return tick();
        }).then(function () {
          if (last) return;   // back at the start: the loop's first frame is the hold
          inst.setOption(opt(step, false), true);   // land exactly on the dial position
          grab(GIF_HOLD);
        });
      })(i % n, i === n);
    }
    return chain.then(function () { return frames; }, function (e) { throw e; })
      .finally(function () { inst.dispose(); div.remove(); });
  }
  function same(a, b) {
    if (a.length !== b.length) return false;
    for (var i = 0; i < a.length; i += 4) { if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) return false; }
    return true;
  }
  function encodeGif(frames) {
    // A chart whose series don't glide repeats the same picture during a transition: fold repeats into one frame.
    var kept = [];
    frames.forEach(function (fr) {
      var prev = kept[kept.length - 1];
      if (prev && same(prev.data, fr.data)) prev.delay += fr.delay;
      else kept.push({ data: fr.data, w: fr.w, h: fr.h, delay: fr.delay });
    });
    var g = gifenc.GIFEncoder();
    kept.forEach(function (fr) {
      var palette = gifenc.quantize(fr.data, 256);
      g.writeFrame(gifenc.applyPalette(fr.data, palette), fr.w, fr.h, { palette: palette, delay: fr.delay, repeat: 0 });
    });
    g.finish();
    return new Blob([g.bytes()], { type: 'image/gif' });
  }
  function gifBlob(f, m) { return gifFrames(f, m).then(encodeGif); }

  function act(id, what) {
    var f = FIGS[id], m = mode(), s = stepOf(f), base = fileName(f, s, m);
    if (what === 'copy') {
      if (!navigator.clipboard || !window.ClipboardItem) { toast('This browser can’t copy images. Use PNG.'); return; }
      // The ClipboardItem is created inside the click, with a promise, which Safari needs.
      var item = new ClipboardItem({ 'image/png': dataURLBlob(pngURL(f, s, m)) });
      navigator.clipboard.write([item]).then(function () { toast('Copied ' + id + ' as an image'); },
        function (e) { toast('Copy failed: ' + (e && e.message ? e.message : e)); });
    } else if (what === 'png') {
      dataURLBlob(pngURL(f, s, m)).then(function (b) { save(b, base + '.png'); });
    } else if (what === 'svg') {
      save(new Blob([svgText(f, s, m)], { type: 'image/svg+xml' }), base + '.svg');
    } else if (what === 'gif') {
      if (!f.dial) { toast(id + ' has no dial to animate'); return; }
      toast('Recording ' + id + ' as a GIF…');
      var gifName = ((f.path || '').split('/').pop() || f.id) + (m ? '-dark' : '') + '.gif';
      gifBlob(f, m).then(function (b) { save(b, gifName); toast('Saved ' + id + ' as a GIF'); },
        function (e) { toast('GIF failed: ' + (e && e.message ? e.message : e)); console.error(e); });
    } else if (what === 'csv') {
      save(new Blob([csv(f.data)], { type: 'text/csv' }), (f.path || id).split('/').pop() + '.csv');
    }
  }

  var toastTimer;
  function toast(msg) {
    var t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove('on'); }, 1800);
  }

  // ---------------------------------------------------------------- checks (used by python -m viz check)

  function textBoxes(inst) {
    var zr = inst.getZr();
    if (zr.refreshImmediately) zr.refreshImmediately();
    var out = [];
    zr.storage.getDisplayList(true).forEach(function (el) {
      if (el.type !== 'tspan' || el.invisible || el.ignore) return;
      var text = el.style && el.style.text;
      if (text === undefined || text === null || !String(text).trim()) return;
      var r = el.getBoundingRect().clone();
      var mt = el.getComputedTransform();
      if (mt) r.applyTransform(mt);
      out.push({ text: String(text), x: r.x, y: r.y, w: r.width, h: r.height, host: el.parent || null });
    });
    return out;
  }
  function words(s) { return (s.match(/[A-Za-z][A-Za-z'’-]*/g) || []).length; }
  function checkOne(f, step, m) {
    var res = { id: f.id, step: step, mode: m ? 'dark' : 'light', errors: [], clipped: [], overlaps: [], long: [], words: 0, texts: 0, png: null };
    var orig = console.error, r = null;
    console.error = function () {
      res.errors.push(Array.prototype.map.call(arguments, String).join(' '));
      orig.apply(console, arguments);
    };
    try { r = renderAt(f, step, m, 'canvas'); } catch (e) { res.errors.push(String(e && e.stack ? e.stack : e)); }
    finally { console.error = orig; }
    if (!r) return res;
    try {
      var W = EXPORT_W, H = f.height, boxes = textBoxes(r.inst);
      res.texts = boxes.length;
      boxes.forEach(function (b) {
        var n = words(b.text);
        res.words += n;
        if (n > 8) res.long.push(b.text);
        if (b.x < -1 || b.y < -1 || b.x + b.w > W + 1 || b.y + b.h > H + 1) res.clipped.push(b.text);
      });
      for (var i = 0; i < boxes.length; i++) {
        for (var j = i + 1; j < boxes.length; j++) {
          var a = boxes[i], b = boxes[j];
          if (a.host && a.host === b.host) continue;
          var ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
          var oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
          if (ox > 2 && oy > 2) res.overlaps.push([a.text, b.text]);
        }
      }
      res.png = r.inst.getDataURL({ type: 'png', pixelRatio: 1 });
    } finally { r.done(); }
    try {
      var svg = svgText(f, step, m);
      if (svg.indexOf('<svg') < 0) res.errors.push('SVG export produced no <svg> element');
    } catch (e) { res.errors.push('SVG export failed: ' + (e && e.message ? e.message : e)); }
    return res;
  }
  function checkAll(ids) {
    var out = [];
    D.figures.forEach(function (f) {
      if (ids && ids.length && ids.indexOf(f.id) < 0) return;
      if (f.kind === 'html') { out.push({ id: f.id, html: true }); return; }
      var n = f.dial ? f.dial.steps.length : 1;
      for (var s = 0; s < n; s++) { out.push(checkOne(f, s, 0)); out.push(checkOne(f, s, 1)); }
    });
    return out;
  }
  // GIF export for the check: resolves to {bytes, frames, w, h}.
  function checkGif(id, dark) {
    var f = FIGS[id];
    return gifFrames(f, dark ? 1 : 0).then(function (fr) {
      return encodeGif(fr).arrayBuffer().then(function (buf) {
        var u = new Uint8Array(buf), s = '';
        for (var i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
        return { gif: btoa(s), frames: fr.length, w: fr[0].w, h: fr[0].h };
      });
    });
  }
  window.__viz = { ready: false, checkAll: checkAll, checkGif: checkGif, setTheme: function (t) { pref = t; applyPref(); remountAll(); } };

  // ---------------------------------------------------------------- page wiring

  function wire() {
    applyPref();
    document.getElementById('theme').addEventListener('click', function (e) {
      var b = e.target.closest('button');
      if (!b) return;
      pref = b.dataset.t;
      try { localStorage.setItem('viz-theme', pref); } catch (err) { /* ignore */ }
      applyPref(); remountAll();
    });
    if (media && media.addEventListener) media.addEventListener('change', function () { if (pref === 'auto') remountAll(); });

    document.querySelector('main').addEventListener('click', function (e) {
      var card = e.target.closest('.fig');
      if (!card) return;
      var id = card.dataset.id;
      var chip = e.target.closest('.chip');
      if (chip) {
        if (navigator.clipboard) navigator.clipboard.writeText(id).then(function () { toast('Copied ' + id); });
        return;
      }
      var stepBtn = e.target.closest('.dial button');
      if (stepBtn) {
        steps[id] = +stepBtn.dataset.step;
        card.querySelectorAll('.dial button').forEach(function (b) { b.setAttribute('aria-pressed', String(b === stepBtn)); });
        repaint(id);
        return;
      }
      var a = e.target.closest('[data-act]');
      if (a) {
        try { act(id, a.dataset.act); } catch (err) { toast('Export failed: ' + err.message); console.error(err); }
      }
    });

    var q = document.getElementById('q');
    q.addEventListener('input', function () {
      var s = q.value.trim().toLowerCase(), any = false;
      document.querySelectorAll('.fig').forEach(function (c) {
        var hit = !s || c.dataset.search.indexOf(s) >= 0;
        c.hidden = !hit; any = any || hit;
      });
      document.querySelectorAll('.sec').forEach(function (sec) { sec.hidden = !sec.querySelector('.fig:not([hidden])'); });
      document.querySelector('.empty').hidden = any;
      Object.keys(live).forEach(function (id) { if (live[id].inst) live[id].inst.resize(); });
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); mount(e.target); } });
    }, { rootMargin: '700px 0px' });
    document.querySelectorAll('.chart').forEach(function (el) { io.observe(el); });

    var navLinks = {};
    document.querySelectorAll('.side li li a').forEach(function (a) { navLinks[a.getAttribute('href').slice(1)] = a; });
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var a = navLinks[e.target.id];
        if (a) a.classList.toggle('on', e.isIntersecting);
      });
    }, { rootMargin: '-45% 0px -45% 0px' });
    document.querySelectorAll('.fig').forEach(function (c) { spy.observe(c); });

    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { Object.keys(live).forEach(function (id) { if (live[id].inst) live[id].inst.resize(); }); }, 120);
    });

    function flash() {
      var el = location.hash && document.getElementById(location.hash.slice(1));
      if (el && el.classList.contains('fig')) { el.classList.add('flash'); setTimeout(function () { el.classList.remove('flash'); }, 1400); }
    }
    window.addEventListener('hashchange', flash);
    flash();
    window.__viz.ready = true;
  }

  var fonts = document.fonts && document.fonts.load
    ? Promise.all(['400', '500', '600', '700'].map(function (w) { return document.fonts.load(w + ' 12px Inter'); }))
    : Promise.resolve();
  fonts.then(wire, wire);
})();
