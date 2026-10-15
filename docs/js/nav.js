/* Side navigation: mark the chapter the reader is currently on.

   Uses IntersectionObserver against a band near the top of the viewport rather
   than a scroll handler, so it costs nothing while scrolling. Falls back to
   marking the first chapter if the browser has no observer. */

(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var links = Array.prototype.slice.call(document.querySelectorAll(".sidenav-link"));
    if (!links.length) return;

    var sections = links
      .map(function (a) {
        var id = a.getAttribute("href");
        return id && id.charAt(0) === "#" ? document.querySelector(id) : null;
      })
      .filter(Boolean);

    function mark(id) {
      links.forEach(function (a) {
        var on = a.getAttribute("href") === "#" + id;
        a.classList.toggle("is-current", on);
        if (on) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
    }

    if (!("IntersectionObserver" in window) || !sections.length) {
      mark(sections.length ? sections[0].id : "");
      return;
    }

    var visible = new Map();

    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) visible.set(e.target.id, e.intersectionRatio);
          else visible.delete(e.target.id);
        });

        if (visible.size) {
          // The chapter occupying the most of the band wins.
          var best = null;
          var bestRatio = -1;
          visible.forEach(function (ratio, id) {
            if (ratio > bestRatio) { bestRatio = ratio; best = id; }
          });
          if (best) mark(best);
        }
      },
      {
        // A band across the upper middle of the viewport. A chapter counts as
        // "current" once its content reaches reading position, not when its
        // bottom edge first appears.
        rootMargin: "-12% 0px -60% 0px",
        threshold: [0, 0.1, 0.25, 0.5, 0.75, 1],
      }
    );

    sections.forEach(function (s) { io.observe(s); });

    /* At the very top of the page nothing has entered the band yet, so mark the
       first chapter rather than leaving the nav with nothing selected. */
    if (!document.querySelector(".sidenav-link.is-current")) {
      mark(sections[0].id);
    }

    // On a narrow screen the nav is a horizontal strip, so keep the current
    // chapter scrolled into view inside it.
    var list = document.querySelector(".sidenav-list");
    if (list) {
      var keepVisible = function () {
        var cur = list.querySelector(".sidenav-link.is-current");
        if (!cur || window.innerWidth > 1024) return;
        var l = cur.offsetLeft, r = l + cur.offsetWidth;
        if (l < list.scrollLeft || r > list.scrollLeft + list.clientWidth) {
          list.scrollTo({ left: l - 16, behavior: "smooth" });
        }
      };
      var mo = new MutationObserver(keepVisible);
      links.forEach(function (a) {
        mo.observe(a, { attributes: true, attributeFilter: ["class"] });
      });
    }
  });
})();
