/* A small step-by-step walkthrough. Each step points at one part of the page, dims the rest, and
   explains it in a card with Back and Next. Used by the game and the data page.

     var t = new Tour([{ el: "#plot", title: "...", body: "<p>...</p>", before: fn, pad: 8 }], { onEnd: fn });
     t.start();

   `el` is a selector or a function returning an element (or null for a centred card with no
   spotlight). `before` runs when the step opens, for example to switch a tab; `wait` (ms) gives the
   page time to redraw before the spotlight is measured. Esc closes; the arrow keys step. */
(function () {
  function Tour(steps, opts) {
    this.steps = steps; this.opts = opts || {}; this.i = -1;
    this._onKey = this.onKey.bind(this);
    this._onMove = this.schedule.bind(this);
  }
  Tour.prototype.start = function (at) {
    if (this.i >= 0) return;
    this.lastFocus = document.activeElement;
    this.block = mk("div", "tour-block");
    this.hole = mk("div", "tour-hole");
    this.pop = mk("div", "tour-pop");
    this.pop.setAttribute("role", "dialog");
    this.pop.setAttribute("aria-modal", "true");
    this.pop.setAttribute("aria-labelledby", "tour-title");
    document.body.appendChild(this.block); document.body.appendChild(this.hole); document.body.appendChild(this.pop);
    document.addEventListener("keydown", this._onKey, true);
    window.addEventListener("resize", this._onMove);
    window.addEventListener("scroll", this._onMove, true);
    this.go(at || 0);
  };
  Tour.prototype.go = function (n) {
    var self = this, s = this.steps[n];
    if (!s) { this.end(true); return; }
    this.i = n;
    if (s.before) { try { s.before(); } catch (e) { /* a step's setup failing should not trap the reader */ } }
    var last = n === this.steps.length - 1;
    this.pop.innerHTML =
      "<button class='textbtn tour-skip' type='button' data-act='end'>" + (last ? "Close" : "Skip tour") + "</button>" +
      "<h3 id='tour-title'>" + s.title + "</h3>" + s.body +
      "<div class='tour-foot'><span class='tour-count'>" + (n + 1) + " of " + this.steps.length + "</span>" +
      (n > 0 ? "<button class='btn small' type='button' data-act='back'>Back</button>" : "") +
      "<button class='btn small primary' type='button' data-act='next'>" + (last ? (this.opts.doneLabel || "Done") : "Next") + "</button></div>";
    this.pop.querySelectorAll("[data-act]").forEach(function (b) {
      b.addEventListener("click", function () {
        var a = b.getAttribute("data-act");
        if (a === "next") self.go(self.i + 1); else if (a === "back") self.go(self.i - 1); else self.end(false);
      });
    });
    this.pop.style.visibility = "hidden";
    setTimeout(function () {
      if (self.i !== n) return;
      var t = target(s);
      if (t) bringIntoView(t);
      setTimeout(function () {
        if (self.i !== n) return;
        self.place();
        self.pop.style.visibility = "";
        var nx = self.pop.querySelector("[data-act='next']"); if (nx) nx.focus({ preventScroll: true });
      }, t ? 260 : 0);
    }, s.wait || 30);
  };
  Tour.prototype.schedule = function () {
    var self = this; if (this.raf) return;
    this.raf = requestAnimationFrame(function () { self.raf = 0; if (self.i >= 0) self.place(); });
  };
  Tour.prototype.place = function () {
    var s = this.steps[this.i]; if (!s) return;
    var t = target(s), vw = window.innerWidth, vh = window.innerHeight, pad = s.pad == null ? 8 : s.pad;
    var pop = this.pop, hole = this.hole;
    pop.style.left = pop.style.top = "";
    if (!t) {
      hole.className = "tour-hole none"; hole.style.left = (vw / 2) + "px"; hole.style.top = (vh / 2) + "px"; hole.style.width = hole.style.height = "0px";
      pop.style.left = Math.max(12, (vw - pop.offsetWidth) / 2) + "px";
      pop.style.top = Math.max(12, (vh - pop.offsetHeight) / 2) + "px";
      return;
    }
    hole.className = "tour-hole";
    var r = t.getBoundingClientRect();
    var L = Math.max(4, r.left - pad), T = Math.max(4, r.top - pad);
    var R = Math.min(vw - 4, r.right + pad), B = Math.min(vh - 4, r.bottom + pad);
    hole.style.left = L + "px"; hole.style.top = T + "px";
    hole.style.width = Math.max(0, R - L) + "px"; hole.style.height = Math.max(0, B - T) + "px";
    if (vw <= 640) return;   // the card docks to the bottom on phones (see site.css)
    var pw = pop.offsetWidth, ph = pop.offsetHeight, gap = 14, x, y;
    var place = s.placement || (vh - B > ph + gap + 8 ? "bottom" : T > ph + gap + 8 ? "top" : vw - R > pw + gap ? "right" : L > pw + gap ? "left" : "over");
    if (place === "bottom") { y = B + gap; x = L; }
    else if (place === "top") { y = T - gap - ph; x = L; }
    else if (place === "right") { x = R + gap; y = T; }
    else if (place === "left") { x = L - gap - pw; y = T; }
    else { x = R - pw - 12; y = B - ph - 12; }
    pop.style.left = Math.min(Math.max(12, x), vw - pw - 12) + "px";
    pop.style.top = Math.min(Math.max(12, y), vh - ph - 12) + "px";
  };
  Tour.prototype.onKey = function (e) {
    if (this.i < 0) return;
    if (e.key === "Escape") { e.preventDefault(); this.end(false); }
    else if (e.key === "ArrowRight") { e.preventDefault(); this.go(this.i + 1); }
    else if (e.key === "ArrowLeft" && this.i > 0) { e.preventDefault(); this.go(this.i - 1); }
    else if (e.key === "Tab") {   // keep focus inside the card
      var f = this.pop.querySelectorAll("button, a[href]"); if (!f.length) return;
      var first = f[0], lastEl = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); lastEl.focus(); }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); first.focus(); }
      else if (!this.pop.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    }
  };
  Tour.prototype.end = function (finished) {
    if (this.i < 0) return;
    this.i = -1;
    document.removeEventListener("keydown", this._onKey, true);
    window.removeEventListener("resize", this._onMove);
    window.removeEventListener("scroll", this._onMove, true);
    [this.block, this.hole, this.pop].forEach(function (n) { if (n && n.parentNode) n.parentNode.removeChild(n); });
    if (this.lastFocus && this.lastFocus.focus) { try { this.lastFocus.focus({ preventScroll: true }); } catch (e) { /* element gone */ } }
    if (this.opts.onEnd) this.opts.onEnd(!!finished);
  };

  function mk(tag, cls) { var n = document.createElement(tag); n.className = cls; return n; }
  function target(s) {
    var t = typeof s.el === "function" ? s.el() : (s.el ? document.querySelector(s.el) : null);
    return t && t.getClientRects().length ? t : null;
  }
  function bringIntoView(t) {
    var r = t.getBoundingClientRect(), vh = window.innerHeight, head = 64;
    var phone = window.innerWidth <= 640, room = phone ? vh * 0.5 : vh - 40;
    if (r.top >= head && r.bottom <= (phone ? vh * 0.55 : vh - 24)) return;
    var y = window.scrollY + r.top - head - 12;
    if (!phone && r.height < room - head) y = window.scrollY + r.top - (vh - r.height) / 2;
    var html = document.documentElement, prev = html.style.scrollBehavior;
    html.style.scrollBehavior = "auto";   // jump, so the spotlight can be measured straight after
    window.scrollTo(0, Math.max(0, y));
    html.style.scrollBehavior = prev;
  }
  window.Tour = Tour;
})();
