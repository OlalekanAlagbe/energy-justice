/* Theme: follow the operating system by default, let an explicit choice override.
   Three states, matching tokens.css:
     no data-theme attribute  ->  follow prefers-color-scheme
     data-theme="light"       ->  forced light
     data-theme="dark"        ->  forced dark
   The choice is stored per browser. Storage can throw in private windows and
   when site data is blocked, so every read and write is guarded. */

(function () {
  "use strict";

  var KEY = "ej-theme";
  var root = document.documentElement;

  function stored() {
    try {
      var v = window.localStorage.getItem(KEY);
      return v === "light" || v === "dark" ? v : null;
    } catch (e) {
      return null;
    }
  }

  function persist(v) {
    try {
      if (v) window.localStorage.setItem(KEY, v);
      else window.localStorage.removeItem(KEY);
    } catch (e) {
      /* no storage, the choice simply does not survive a reload */
    }
  }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  /* What the page is actually showing right now. */
  function active() {
    var explicit = root.getAttribute("data-theme");
    if (explicit === "light" || explicit === "dark") return explicit;
    return systemPrefersDark() ? "dark" : "light";
  }

  function apply(v) {
    if (v) root.setAttribute("data-theme", v);
    else root.removeAttribute("data-theme");
    render();
    window.dispatchEvent(new CustomEvent("ej:themechange", { detail: { theme: active() } }));
  }

  var SUN = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    + '<circle cx="12" cy="12" r="4.5"/><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/></svg>';
  var MOON = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
    + '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>';

  var btn;

  function render() {
    if (!btn) return;
    var now = active();
    var next = now === "dark" ? "light" : "dark";
    btn.innerHTML = (now === "dark" ? SUN : MOON) + "<span>" + next + "</span>";
    btn.setAttribute("aria-label", "Switch to " + next + " theme");
    btn.setAttribute("title", "Switch to " + next + " theme");
  }

  /* Run before first paint so there is no flash of the wrong theme. */
  var initial = stored();
  if (initial) root.setAttribute("data-theme", initial);

  document.addEventListener("DOMContentLoaded", function () {
    btn = document.getElementById("theme-toggle");
    if (!btn) return;
    render();
    btn.addEventListener("click", function () {
      var next = active() === "dark" ? "light" : "dark";
      persist(next);
      apply(next);
    });
  });

  /* If the reader has made no explicit choice, follow the system live. */
  if (window.matchMedia) {
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var onChange = function () {
      if (!stored()) apply(null);
    };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
  }

  window.EJTheme = { active: active };
})();
