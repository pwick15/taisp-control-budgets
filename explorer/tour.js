/* The guided tours for the data page, built on shared/tour.js. A first visit opens the main
   tour; the first visit to each of the other two views opens a two-step tour of that view.
   "Take the one-minute tour" replays the tour for whichever view is open. Kept out of app.js
   so the DOM smoke test (dom_smoke.mjs) drives the app exactly as before. */
(function () {
  var KEY = "kota-data-tours";
  var seen = {};
  try { seen = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { seen = {}; }
  function mark(id) { seen[id] = 1; try { localStorage.setItem(KEY, JSON.stringify(seen)); } catch (e) { /* storage blocked */ } }
  function current() { var t = document.querySelector('#tabs .tab[aria-selected="true"]'); return t ? t.getAttribute("data-lens") : "atlas"; }
  function show(id) { var t = document.querySelector('#tabs .tab[data-lens="' + id + '"]'); if (t && current() !== id) t.click(); }
  function firstPanel() { return document.querySelector("#detail .panel"); }

  var TOURS = {
    atlas: [
      { el: null, title: "Welcome to the data",
        body: "<p>These are the scores behind the story: 1,000 programs, each read by twelve of our knights at every setting we ran.</p><p>The tour takes about a minute. You can leave it any time with Esc.</p>" },
      { el: "#tabs", title: "Three ways to look", before: function () { show("atlas"); },
        body: "<p><b>Every program</b> shows each score as a dot. <b>Turn one dial</b> follows programs as one setting changes. <b>Pick a budget</b> ranks the knights at the audit budget you choose.</p>" },
      { el: "#plot", title: "Each row is one knight", pad: 4,
        body: "<p>Each row is one knight at one setting, named on the left. Each dot is one program. Honest programs sit above the row's line and backdoors below it.</p><p>Further right means the knight reasoned for longer before giving its score.</p>" },
      { el: firstPanel, title: "Green is right, red is wrong",
        body: "<p>The colours show whether the knight's call was right at a 2% audit budget.</p><p>Green triangles are backdoors it caught; red ones got past it. Yellow dots are honest programs it flagged by mistake.</p>" },
      { el: "#featured", title: "Start with these four",
        body: "<p>Each card is a program worth reading: a clean one every knight distrusted, two backdoors no knight caught, and one that confessed in a comment.</p><p>Click a card to light it up in every row and read about it on the right.</p>" },
      { el: "#toolbar", title: "Make it yours",
        body: "<p>Show only honest programs or only backdoors, switch the colours, or find a program by its number.</p><p>The knights' names below turn their rows on and off. <b>More filters</b> has the reasoning settings and the rest.</p>" }
    ],
    trajectories: [
      { el: "#plot", title: "One line per program", pad: 4,
        body: "<p>Each column is one setting we tried, in order. Each thin line is one program: follow it to see how the knight's score for that program moved as the setting changed.</p><p>The thick line is the average.</p>" },
      { el: "#toolbar", title: "Choose the dial",
        body: "<p>Pick which setting to change: reasoning effort, the score scale, or whether comments were kept.</p><p>Drag along any column to keep only the lines that pass through that range.</p>" }
    ],
    flightdeck: [
      { el: "#plot", title: "Every knight's catch rate", pad: 4,
        body: "<p>Each step line is one knight at one setting. Moving right, the auditor checks more honest code, and the line shows the share of backdoors that knight would catch.</p><p>The steps are there because a knight can only hit the budgets its scores allow.</p>" },
      { el: "#toolbar", title: "Set your budget",
        body: "<p>Drag the audit budget. The leaderboard on the right re-ranks every knight by how many backdoors it catches at that budget, and shows what each one costs.</p>" }
    ]
  };

  var running = null;
  function start(id) {
    if (running || !window.Tour) return;
    var steps = TOURS[id] || TOURS.atlas;
    running = new window.Tour(steps, { doneLabel: "Start exploring", onEnd: function () { mark(id); running = null; } });
    running.start();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("tour-btn");
    if (btn) btn.addEventListener("click", function () { start(current()); });
    // A shared link opens a chosen view; don't cover it with the tour.
    var shared = location.hash && location.hash.length > 1;
    if (!seen.atlas && !shared && current() === "atlas") setTimeout(function () { start("atlas"); }, 700);
    var tabs = document.getElementById("tabs");
    if (tabs) tabs.addEventListener("click", function () {
      setTimeout(function () { var id = current(); if (!running && id !== "atlas" && !seen[id]) start(id); }, 500);
    });
    // Canvas text is drawn once; redraw after the web font arrives so the charts use it.
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { window.dispatchEvent(new Event("resize")); });
  });
})();
