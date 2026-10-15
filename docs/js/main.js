/* Wiring: mount every chart once, then rebuild them when the theme changes so
   they pick up the new tokens. */

(function () {
  "use strict";

  var CHARTS = [
    // element id,        builder,      data key
    ["ch1-map",           "ch1Map",     "ch1_coverage_map"],
    ["ch1-growth",        "ch1Growth",  "ch1_panel_growth"],
    ["ch2-map",           "ch2Map",     "ch2_demand_map"],
    ["ch2-income",        "ch2Income",  "ch2_income_groups"],
    ["ch3-scatter",       "ch3Scatter", "ch3_amount_vs_mix"],
    ["ch3-fossil",        "ch3Fossil",  "ch3_world_fossil"],
    ["ch4-scatter",       "ch4Scatter", "ch4_production_vs_power"],
    ["ch5-output",        "ch5Output",  "ch5_nigeria_output"],
    ["ch5-mix",           "ch5Mix",     "ch5_nigeria_mix"],
    ["ch5-peers",         "ch5Peers",   "ch5_peer_growth"],
    ["ch5-mix-table",     "ch5MixTable", "ch5_nigeria_mix"]
  ];

  function fillFigures() {
    /* Any element with data-fig="<id>" is replaced by the value held in
       key_figures.json, so prose numbers come from the same build as the
       charts. If the key is missing the element keeps its written fallback,
       which keeps the page readable rather than showing "undefined". */
    var figs = (window.EJ_DATA || {}).key_figures;
    if (!figs || !figs.figures) return;
    document.querySelectorAll("[data-fig]").forEach(function (el) {
      var f = figs.figures[el.getAttribute("data-fig")];
      if (!f) return;
      el.textContent = f.display !== undefined ? f.display : f.value;
      if (f.column) el.setAttribute("title", f.column + (f.year ? ", " + f.year : ""));
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof Plotly === "undefined") {
      document.querySelectorAll(".plot").forEach(function (el) {
        el.innerHTML = '<p class="fig-sub">Charts need vendor/plotly-geo-3.0.1.min.js.</p>';
      });
      return;
    }

    fillFigures();
    CHARTS.forEach(function (c) { window.EJCharts.mount(c[0], c[1], c[2]); });

    var pending = null;
    window.addEventListener("ej:themechange", function () {
      /* The attribute flip and the CSS recalculation are not synchronous, so
         read tokens on the next frame or the charts pick up the old palette. */
      if (pending) cancelAnimationFrame(pending);
      pending = requestAnimationFrame(function () {
        pending = null;
        window.EJCharts.redrawAll();
      });
    });
  });
})();
