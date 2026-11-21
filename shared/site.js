/* Shared behaviour for every page: the light/dark switch in the header. The choice is stored
   under one key, so it follows the reader from page to page. A page that repaints charts on a
   theme change (the data page) sets data-own-theme on <html> and handles the button itself. */
(function () {
  var KEY = "kota-theme";
  var root = document.documentElement;
  var MOON = "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'/></svg>";
  var SUN = "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><circle cx='12' cy='12' r='4'/><path d='M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4'/></svg>";

  function current() {
    var t = root.getAttribute("data-theme");
    if (t === "light" || t === "dark") return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  function paintButton(btn, t) {
    btn.innerHTML = t === "dark" ? SUN : MOON;
    var label = t === "dark" ? "Switch to light theme" : "Switch to dark theme";
    btn.setAttribute("aria-label", label); btn.title = label;
  }
  window.SiteTheme = { current: current, paint: function (t) { var b = document.getElementById("theme-btn"); if (b) paintButton(b, t); }, key: KEY };

  if (root.hasAttribute("data-own-theme")) return;
  var btn = document.getElementById("theme-btn");
  if (!btn) return;
  paintButton(btn, current());
  btn.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) { /* storage blocked: the switch still works for this visit */ }
    paintButton(btn, next);
    document.dispatchEvent(new CustomEvent("site:theme", { detail: next }));
  });
})();
