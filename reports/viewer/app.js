// Tooltips for chart marks and the light/dark toggle. No dependencies.
(function () {
  var tip = document.createElement("div");
  tip.className = "tip";
  tip.setAttribute("role", "tooltip");
  document.body.appendChild(tip);

  function show(target, x, y) {
    // data-tip holds lines separated by "|". The first line is the value, the rest explain it.
    // textContent only, so labels from data can never inject markup.
    var lines = target.getAttribute("data-tip").split("|");
    tip.replaceChildren();
    lines.forEach(function (line, i) {
      var el = document.createElement(i === 0 ? "strong" : "span");
      el.textContent = line;
      tip.appendChild(el);
      if (i > 0 && i < lines.length - 1) tip.appendChild(document.createElement("br"));
    });
    tip.classList.add("on");
    var pad = 14;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(x + pad, window.innerWidth - w - 8);
    var top = y + pad + h > window.innerHeight ? y - h - pad : y + pad;
    tip.style.left = Math.max(8, left) + "px";
    tip.style.top = Math.max(8, top) + "px";
  }

  document.addEventListener("pointermove", function (e) {
    var t = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (t) show(t, e.clientX, e.clientY);
    else tip.classList.remove("on");
  });
  document.addEventListener("pointerleave", function () { tip.classList.remove("on"); });

  var button = document.querySelector("button.theme");
  if (!button) return;
  var order = ["auto", "light", "dark"];
  function apply(mode) {
    if (mode === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", mode);
    button.textContent = "Theme: " + mode;
  }
  var mode = "auto";
  try { mode = localStorage.getItem("report-theme") || "auto"; } catch (e) {}
  apply(mode);
  button.addEventListener("click", function () {
    mode = order[(order.indexOf(mode) + 1) % order.length];
    try { localStorage.setItem("report-theme", mode); } catch (e) {}
    apply(mode);
  });
})();
