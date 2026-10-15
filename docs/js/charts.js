/* Charts.

   Every colour and face comes out of tokens.css at runtime via
   getComputedStyle, so the Plotly figures and the page can never drift apart.
   On a theme change the charts are rebuilt from the same data with freshly read
   tokens, which is why there is no second hard-coded dark palette here.

   Plotly build: vendor/plotly-geo-3.0.1.min.js, the partial "geo" bundle.
   It carries choropleth, scattergeo and scatter. It has no bar trace, so bar
   charts on this site are plain CSS, which also keeps them identical to the
   figures in the research memo. */

(function () {
  "use strict";

  /* ---- tokens ----------------------------------------------------------- */

  function tokens() {
    var s = getComputedStyle(document.documentElement);
    var get = function (n) { return s.getPropertyValue(n).trim(); };
    return {
      surface: get("--surface"),
      surface2: get("--surface-2"),
      ground: get("--ground"),
      ink: get("--ink"),
      inkSoft: get("--ink-soft"),
      inkMute: get("--ink-mute"),
      rule: get("--rule"),
      ruleFirm: get("--rule-firm"),
      teal: get("--teal"),
      amber: get("--amber"),
      seq: [1, 2, 3, 4, 5, 6, 7].map(function (i) { return get("--seq-" + i); }),
      stateYes: get("--state-yes"),
      stateNo: get("--state-no"),
      cat: [1, 2, 3, 4].map(function (i) { return get("--cat-" + i); }),
      mapNoData: get("--map-nodata"),
      regionFill: get("--region-fill"),
      markMute: get("--mark-mute"),
      grid: get("--grid"),
      axis: get("--axis"),
      tooltipBg: get("--tooltip-bg"),
      tealWash: get("--teal-wash"),
      tooltipFg: get("--tooltip-fg"),
      mono: get("--font-mono") || "monospace",
      body: get("--font-body") || "sans-serif"
    };
  }

  /* ---- shared layout ---------------------------------------------------- */

  function baseLayout(t) {
    return {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: t.mono, size: 11, color: t.inkMute },
      margin: { l: 48, r: 16, t: 8, b: 36 },
      showlegend: false,
      hoverlabel: {
        bgcolor: t.tooltipBg,
        bordercolor: t.tooltipBg,
        font: { family: t.mono, size: 12, color: t.tooltipFg },
        align: "left"
      },
      dragmode: false
    };
  }

  function axis(t, extra) {
    var a = {
      color: t.inkMute,
      gridcolor: t.grid,
      zeroline: false,
      linecolor: t.rule,
      tickfont: { family: t.mono, size: 10, color: t.inkMute },
      title: { font: { family: t.mono, size: 10, color: t.inkMute } },
      automargin: true
    };
    return Object.assign(a, extra || {});
  }

  var CONFIG = {
    displayModeBar: false,
    responsive: true,
    scrollZoom: false,
    doubleClick: false
  };

  /* ---- chapter 1, choropleth of what is measured ------------------------ */

  function ch1Map(el, data) {
    var t = tokens();
    var rows = data.rows;

    var groups = [
      { on: 1, color: t.stateYes, label: "Energy mix published" },
      { on: 0, color: t.stateNo, label: "No energy mix published" }
    ];

    var traces = groups.map(function (g) {
      var r = rows.filter(function (d) { return d.measured === g.on; });
      return {
        type: "choropleth",
        locationmode: "ISO-3",
        locations: r.map(function (d) { return d.iso; }),
        z: r.map(function () { return 1; }),
        text: r.map(function (d) { return d.country; }),
        customdata: r.map(function (d) {
          return [
            d.total_energy_twh === null ? "not reported" : fmt(d.total_energy_twh) + " TWh",
            g.on ? "published" : "not published"
          ];
        }),
        colorscale: [[0, g.color], [1, g.color]],
        showscale: false,
        marker: { line: { color: t.surface, width: 0.5 } },
        hovertemplate:
          "<b>%{text}</b><br>" +
          "Energy mix: %{customdata[1]}<br>" +
          "Total energy supply: %{customdata[0]}" +
          "<extra></extra>"
      };
    });

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 0, r: 0, t: 0, b: 0 },
      geo: {
        bgcolor: "rgba(0,0,0,0)",
        showframe: false,
        showcoastlines: false,
        showland: true,
        landcolor: t.mapNoData,
        showocean: false,
        showlakes: false,
        projection: { type: "natural earth" },
        lataxis: { range: [-56, 84] },
        lonaxis: { range: [-170, 180] },
        domain: { x: [0, 1], y: [0, 1] }
      }
    });

    return Plotly.newPlot(el, traces, layout, CONFIG);
  }

  /* ---- chapter 1, how many countries the data can describe -------------- */

  function ch1Growth(el, data) {
    var t = tokens();
    var rows = data.rows;
    var years = rows.map(function (d) { return d.year; });

    var series = [
      {
        key: "with_total",
        label: "Total energy supply",
        color: t.markMute,
        dash: "solid",
        width: 2
      },
      {
        key: "with_electricity",
        label: "Electricity generation",
        color: t.markMute,
        dash: "dot",
        width: 2
      },
      {
        key: "with_mix",
        label: "Energy mix by source",
        color: t.teal,
        dash: "solid",
        width: 2.5
      }
    ];

    var traces = series.map(function (s) {
      return {
        type: "scatter",
        mode: "lines",
        x: years,
        y: rows.map(function (d) { return d[s.key]; }),
        name: s.label,
        line: { color: s.color, width: s.width, dash: s.dash, shape: "spline", smoothing: 0.4 },
        hovertemplate: "<b>%{x}</b><br>" + s.label + ": %{y} countries<extra></extra>"
      };
    });

    /* Direct labels at the right edge, so identity never rests on colour. */
    var last = rows[rows.length - 1];
    var annotations = series.map(function (s) {
      return {
        x: last.year,
        y: last[s.key],
        xanchor: "left",
        yanchor: "middle",
        xshift: 6,
        text: last[s.key],
        showarrow: false,
        font: { family: t.mono, size: 11, color: s.color === t.teal ? t.teal : t.inkMute }
      };
    });

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 44, r: 34, t: 8, b: 34 },
      xaxis: axis(t, { dtick: 10, range: [years[0], last.year + 1] }),
      yaxis: axis(t, { rangemode: "tozero", title: { text: "countries", standoff: 8 } }),
      annotations: annotations
    });

    return Plotly.newPlot(el, traces, layout, CONFIG);
  }

  /* ---- chapter 2, choropleth of electricity demand per person ----------- */

  function ch2Map(el, data) {
    var t = tokens();
    var rows = data.rows;
    var nBands = data.breaks.length;

    /* A stepped colorscale, so the map reads as seven named bands rather than a
       continuous wash. z sits mid-band so a value never lands on a boundary. */
    var scale = [];
    for (var i = 0; i < nBands; i++) {
      scale.push([i / nBands, t.seq[i]]);
      scale.push([(i + 1) / nBands, t.seq[i]]);
    }

    var trace = {
      type: "choropleth",
      locationmode: "ISO-3",
      locations: rows.map(function (d) { return d.iso; }),
      z: rows.map(function (d) { return d.band + 0.5; }),
      zmin: 0,
      zmax: nBands,
      text: rows.map(function (d) { return d.country; }),
      customdata: rows.map(function (d) {
        return [fmt(d.demand_pc_kwh), data.band_labels[d.band]];
      }),
      colorscale: scale,
      showscale: false,
      marker: { line: { color: t.surface, width: 0.5 } },
      hovertemplate:
        "<b>%{text}</b><br>" +
        "%{customdata[0]} kWh per person<br>" +
        "band: %{customdata[1]}" +
        "<extra></extra>"
    };

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 0, r: 0, t: 0, b: 0 },
      geo: {
        bgcolor: "rgba(0,0,0,0)",
        showframe: false,
        showcoastlines: false,
        showland: true,
        landcolor: t.mapNoData,
        showocean: false,
        showlakes: false,
        projection: { type: "natural earth" },
        lataxis: { range: [-56, 84] },
        lonaxis: { range: [-170, 180] },
        domain: { x: [0, 1], y: [0, 1] }
      }
    });

    /* The band legend is built from the same data as the map, so the breaks,
       the colours and the counts can never disagree with what is drawn. */
    var legend = document.getElementById("ch2-legend");
    if (legend) {
      legend.innerHTML = data.band_labels.map(function (lab, i) {
        return '<span class="legend-item">'
          + '<span class="legend-swatch" style="background:' + t.seq[i] + ';"></span>'
          + lab + ' <span style="color:' + t.inkMute + '">(' + data.band_counts[i] + ')</span>'
          + "</span>";
      }).join("");
      legend.setAttribute("aria-label",
        "Colour bands, kilowatt-hours per person, with the number of countries in each");
    }

    return Plotly.newPlot(el, [trace], layout, CONFIG);
  }

  /* ---- chapter 2, the four income groups -------------------------------- */

  function ch2Income(el, data) {
    var t = tokens();
    var S = data.series;
    var sum = data.summary;

    /* Income groups have an inherent order, so they take ordered steps from the
       sequential ramp rather than four unrelated hues. seq-7 is the end of the
       ramp furthest from the surface in either theme, so the ordering reads the
       same way in light and dark. */
    var shade = [t.seq[3], t.seq[4], t.seq[5], t.seq[6]];

    var traces = S.map(function (s, i) {
      return {
        type: "scatter",
        mode: "lines",
        x: s.points.map(function (p) { return p.year; }),
        y: s.points.map(function (p) { return p.kwh_pc; }),
        name: s.group,
        line: { color: shade[i], width: 2.2, shape: "spline", smoothing: 0.4 },
        hovertemplate: "<b>%{x}</b><br>" + s.short + ": %{y:,.0f} kWh per person<extra></extra>"
      };
    });

    /* Direct labels, so identity never rests on colour alone. */
    var annotations = S.map(function (s, i) {
      var last = s.points[s.points.length - 1];
      return {
        x: last.year, y: Math.log10(last.kwh_pc),
        xanchor: "left", yanchor: "middle", xshift: 7,
        text: s.short, showarrow: false,
        font: { family: t.mono, size: 10, color: shade[i] }
      };
    });

    /* The ratio is stated in a strip under the chart rather than drawn inside it.
       A span annotation between the top and bottom lines has to cross the two
       middle series, and masking a data line with a label to make room is not a
       trade worth making. The parallel lines already carry the argument. */

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 52, r: 86, t: 10, b: 34 },
      xaxis: axis(t, { dtick: 5, range: [sum.first_year - 0.5, sum.last_year + 0.5] }),
      yaxis: axis(t, {
        type: "log",
        range: [Math.log10(95), Math.log10(16000)],
        tickvals: [200, 500, 1000, 2000, 5000, 10000],
        ticktext: ["200", "500", "1,000", "2,000", "5,000", "10,000"],
        title: { text: "kWh per person, log scale", standoff: 10 }
      }),
      annotations: annotations
    });

    return Plotly.newPlot(el, traces, layout, CONFIG);
  }

  /* ---- chapter 3, amount against mix ------------------------------------ */

  function ch3Scatter(el, data) {
    var t = tokens();
    var rows = data.rows;

    var others = rows.filter(function (d) { return !d.highlight; });
    var nigeria = rows.filter(function (d) { return d.highlight; });

    function pointTrace(r, color, size) {
      return {
        type: "scatter",
        mode: "markers",
        x: r.map(function (d) { return d.demand_pc_kwh; }),
        y: r.map(function (d) { return d.low_carbon_pct; }),
        text: r.map(function (d) { return d.country; }),
        marker: {
          color: color, size: size, opacity: color === t.markMute ? 0.85 : 1,
          line: { color: t.surface, width: 1.5 }
        },
        hovertemplate:
          "<b>%{text}</b><br>" +
          "%{x:,.0f} kWh per person<br>" +
          "%{y:.1f}% low carbon" +
          "<extra></extra>"
      };
    }

    var fit = {
      type: "scatter",
      mode: "lines",
      x: data.fit.x,
      y: data.fit.y,
      line: { color: t.ink, width: 1.5, dash: "dash" },
      hoverinfo: "skip"
    };

    /* Named countries, chosen to show that the low-access end of the axis
       contains every possible mix. */
    var LABEL_SIDE = {
      Ethiopia: ["right", -7, 0], Niger: ["right", -7, 0],
      Bangladesh: ["left", 7, 0], India: ["left", 7, 0],
      Norway: ["right", -7, 0], France: ["left", 7, 0],
      "South Africa": ["left", 7, 0], Nigeria: ["center", 0, 10]
    };
    var annotations = rows.filter(function (d) { return d.label; }).map(function (d) {
      var side = LABEL_SIDE[d.label] || ["center", 0, 10];
      return {
        x: Math.log10(d.demand_pc_kwh), y: d.low_carbon_pct,
        text: d.label, showarrow: false,
        xanchor: side[0], yanchor: side[2] ? "bottom" : "middle",
        xshift: side[1], yshift: side[2],
        font: {
          family: t.mono, size: 10,
          color: d.highlight ? t.amber : t.inkSoft
        }
      };
    });

    /* The slope and r are stated in the figure footer instead of in a box on the
       plot, where the box sat on top of a country label. */

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 52, r: 18, t: 14, b: 44 },
      xaxis: axis(t, {
        type: "log",
        range: [Math.log10(11), Math.log10(78000)],
        tickvals: [20, 50, 100, 300, 1000, 3000, 10000, 30000],
        ticktext: ["20", "50", "100", "300", "1,000", "3,000", "10,000", "30,000"],
        title: { text: "kWh per person, log scale", standoff: 10 }
      }),
      yaxis: axis(t, {
        range: [-4, 104], dtick: 25,
        ticksuffix: "%",
        title: { text: "low-carbon share of electricity", standoff: 10 }
      }),
      annotations: annotations
    });

    return Plotly.newPlot(el,
      [fit, pointTrace(others, t.markMute, 7), pointTrace(nigeria, t.amber, 11)],
      layout, CONFIG);
  }

  /* ---- chapter 3, world fossil: absolute against share ------------------ */

  function ch3Fossil(el, data) {
    var t = tokens();
    var rows = data.rows;
    var years = rows.map(function (d) { return d.year; });

    /* Two stacked panels on one shared year axis, never two y scales on one
       plot. A dual axis lets whoever draws it choose the scales and therefore
       the conclusion, and this chapter is about exactly that kind of framing. */
    var abs = {
      type: "scatter", mode: "lines",
      x: years, y: rows.map(function (d) { return d.fossil_twh; }),
      xaxis: "x", yaxis: "y",
      line: { color: t.teal, width: 2.4 },
      fill: "tozeroy", fillcolor: t.tealWash,
      hovertemplate: "<b>%{x}</b><br>%{y:,.0f} TWh of fossil fuel<extra></extra>"
    };

    var share = {
      type: "scatter", mode: "lines",
      x: years, y: rows.map(function (d) { return d.fossil_share_pct; }),
      xaxis: "x", yaxis: "y2",
      line: { color: t.amber, width: 2.4 },
      hovertemplate: "<b>%{x}</b><br>%{y:.2f}% of all energy<extra></extra>"
    };

    var last = rows[rows.length - 1];
    var layout = Object.assign(baseLayout(t), {
      margin: { l: 62, r: 16, t: 16, b: 36 },
      xaxis: axis(t, { dtick: 10, anchor: "y2", range: [years[0], last.year] }),
      yaxis: axis(t, {
        domain: [0.56, 1], rangemode: "tozero",
        title: { text: "TWh supplied", standoff: 12 },
        tickformat: ",.0f"
      }),
      yaxis2: axis(t, {
        domain: [0, 0.44], range: [80, 100], dtick: 5, ticksuffix: "%",
        title: { text: "share of all energy", standoff: 12 }
      }),
      annotations: [
        {
          xref: "paper", x: 0.012, y: last.fossil_twh, yref: "y",
          xanchor: "left", yanchor: "top",
          text: "<b>Absolute: still climbing</b>", showarrow: false,
          font: { family: t.mono, size: 10, color: t.teal }
        },
        {
          xref: "paper", x: 0.012, yref: "y2", y: 99,
          xanchor: "left", yanchor: "top",
          text: "<b>Share: edging down</b>", showarrow: false,
          font: { family: t.mono, size: 10, color: t.amber }
        }
      ]
    });

    return Plotly.newPlot(el, [abs, share], layout, CONFIG);
  }

  /* ---- chapter 4, production against electricity used ------------------- */

  function ch4Scatter(el, data) {
    var t = tokens();
    var rows = data.rows;
    var th = data.thresholds;

    var xMax = Math.max.apply(null, rows.map(function (d) { return d.ratio; })) * 1.06;
    var yMin = 14, yMax = 46000;

    function group(filterFn, color, size) {
      var r = rows.filter(filterFn);
      return {
        type: "scatter",
        mode: "markers",
        x: r.map(function (d) { return d.ratio; }),
        y: r.map(function (d) { return d.demand_pc_kwh; }),
        text: r.map(function (d) { return d.country; }),
        customdata: r.map(function (d) { return [d.prod_twh, d.total_energy_twh]; }),
        marker: {
          color: color, size: size,
          opacity: color === t.markMute ? 0.8 : 1,
          line: { color: t.surface, width: 1.5 }
        },
        hovertemplate:
          "<b>%{text}</b><br>" +
          "produces %{customdata[0]:,.0f} TWh, uses %{customdata[1]:,.0f} TWh<br>" +
          "that is %{x:.2f} times its own supply<br>" +
          "%{y:,.0f} kWh of electricity per person" +
          "<extra></extra>"
      };
    }

    var outside = group(function (d) { return !d.in_group && !d.highlight; }, t.markMute, 7);
    var inside = group(function (d) { return d.in_group && !d.highlight; }, t.teal, 9);
    var nigeria = group(function (d) { return d.highlight; }, t.amber, 13);

    /* The quadrant is a definition, so draw it as one: a shaded box with its two
       edges marked, rather than leaving the reader to infer where it starts. */
    var shapes = [
      {
        type: "rect", xref: "x", yref: "y",
        x0: th.ratio_min, x1: xMax,
        y0: Math.log10(yMin), y1: Math.log10(th.demand_max),
        fillcolor: t.regionFill, line: { width: 0 }, layer: "below"
      },
      {
        type: "line", xref: "x", yref: "y",
        x0: th.ratio_min, x1: th.ratio_min,
        y0: Math.log10(yMin), y1: Math.log10(yMax),
        line: { color: t.rule, width: 1, dash: "dot" }, layer: "below"
      },
      {
        type: "line", xref: "x", yref: "y",
        x0: 0, x1: xMax,
        y0: Math.log10(th.demand_max), y1: Math.log10(th.demand_max),
        line: { color: t.rule, width: 1, dash: "dot" }, layer: "below"
      }
    ];

    var LABEL_SIDE = {
      Nigeria: ["left", 9, 0],
      Norway: ["right", -9, 0],
      Qatar: ["right", -9, 0],
      Chad: ["right", -9, 0],
      Angola: ["left", 9, 0],
      Indonesia: ["left", 9, 0]
    };

    var annotations = rows.filter(function (d) { return d.label; }).map(function (d) {
      var side = LABEL_SIDE[d.label] || ["left", 9, 0];
      return {
        x: d.ratio, y: Math.log10(d.demand_pc_kwh),
        text: d.label, showarrow: false,
        xanchor: side[0], yanchor: "middle", xshift: side[1],
        font: {
          family: t.mono, size: 10,
          color: d.highlight ? t.amber : (d.in_group ? t.teal : t.inkSoft)
        }
      };
    });

    /* No in-plot label for the shaded region: the legend already names it, and
       the annotation landed on top of one of the points it was describing. */

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 56, r: 20, t: 14, b: 46 },
      xaxis: axis(t, {
        range: [-0.25, xMax],
        dtick: 2,
        title: { text: "fossil fuel produced, as a multiple of own use", standoff: 10 }
      }),
      yaxis: axis(t, {
        type: "log",
        range: [Math.log10(yMin), Math.log10(yMax)],
        tickvals: [20, 100, 500, 2000, 10000, 30000],
        ticktext: ["20", "100", "500", "2,000", "10,000", "30,000"],
        title: { text: "kWh per person, log scale", standoff: 10 }
      }),
      shapes: shapes,
      annotations: annotations
    });

    return Plotly.newPlot(el, [outside, inside, nigeria], layout, CONFIG);
  }

  /* ---- chapter 5, Nigeria's output in total and per person -------------- */

  function ch5Output(el, data) {
    var t = tokens();
    var rows = data.rows;
    var years = rows.map(function (d) { return d.year; });
    var tr = data.trend;

    var total = {
      type: "scatter", mode: "lines",
      x: years, y: rows.map(function (d) { return d.generation_twh; }),
      xaxis: "x", yaxis: "y",
      line: { color: t.teal, width: 2.4 },
      fill: "tozeroy", fillcolor: t.tealWash,
      hovertemplate: "<b>%{x}</b><br>%{y:,.1f} TWh generated in total<extra></extra>"
    };

    var perPerson = {
      type: "scatter", mode: "lines",
      x: years, y: rows.map(function (d) { return d.generation_pc_kwh; }),
      xaxis: "x", yaxis: "y2",
      line: { color: t.amber, width: 2.4 },
      hovertemplate: "<b>%{x}</b><br>%{y:,.1f} kWh per person<extra></extra>"
    };

    /* The fitted trend, drawn so the slope is visible rather than asserted.
       Without it a reader could pick any two years and claim any story. */
    var trend = {
      type: "scatter", mode: "lines",
      x: tr.x, y: tr.y, xaxis: "x", yaxis: "y2",
      line: { color: t.ink, width: 1.2, dash: "dash" },
      hoverinfo: "skip"
    };

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 58, r: 18, t: 16, b: 36 },
      xaxis: axis(t, { dtick: 5, anchor: "y2", range: [years[0], years[years.length - 1]] }),
      yaxis: axis(t, {
        domain: [0.56, 1], rangemode: "tozero",
        title: { text: "TWh generated", standoff: 12 }
      }),
      yaxis2: axis(t, {
        domain: [0, 0.44], range: [0, 210],
        title: { text: "kWh per person", standoff: 12 }
      }),
      annotations: [
        {
          xref: "paper", x: 0.012, yref: "y", y: rows[rows.length - 1].generation_twh,
          xanchor: "left", yanchor: "top",
          text: "<b>Total generated: nearly tripled</b>", showarrow: false,
          font: { family: t.mono, size: 10, color: t.teal }
        },
        {
          xref: "paper", x: 0.012, yref: "y2", y: 200,
          xanchor: "left", yanchor: "top",
          text: "<b>Per person: " + tr.slope_kwh_per_year + " kWh a year since "
            + tr.from + "</b>", showarrow: false,
          font: { family: t.mono, size: 10, color: t.amber }
        }
      ]
    });

    return Plotly.newPlot(el, [total, perPerson, trend], layout, CONFIG);
  }

  /* ---- chapter 5, where the electricity comes from ---------------------- */

  function ch5Mix(el, data) {
    var t = tokens();
    var rows = data.rows;
    var years = rows.map(function (d) { return d.year; });

    /* Teal family plus amber, as agreed. Identity here comes from vertical
       position and the label sitting on the band, not from colour: a four-slot
       categorical palette cannot be built from one hue without some steps
       reading as grey. The table under the chart carries the exact numbers. */
    var SERIES = [
      { key: "gas", label: "Gas", color: t.seq[5] },
      { key: "hydro", label: "Hydro", color: t.seq[2] },
      { key: "solar", label: "Solar", color: t.amber },
      { key: "bioenergy", label: "Bioenergy", color: t.markMute }
    ];

    var traces = SERIES.map(function (sr) {
      return {
        type: "scatter", mode: "lines",
        x: years, y: rows.map(function (d) { return d[sr.key]; }),
        name: sr.label,
        stackgroup: "mix",
        groupnorm: "",
        line: { width: 1, color: t.surface },   /* the 2px surface gap between bands */
        fillcolor: sr.color,
        /* hovermode is "x unified", which prints the year once as the header,
           so the per-band template must not repeat it. */
        hovertemplate: sr.label + ": %{y:.2f}%<extra></extra>"
      };
    });

    var last = rows[rows.length - 1];
    var annotations = [
      /* Labels sit on the bands as chips. A single text colour cannot stay
         legible on both a dark and a light band, and the two bands swap
         lightness between themes. */
      {
        x: 2012, y: 45, xanchor: "center", yanchor: "middle",
        text: "<b>Gas</b>", showarrow: false,
        bgcolor: t.surface, borderpad: 4,
        font: { family: t.mono, size: 12, color: t.ink }
      },
      {
        x: 2012, y: 90, xanchor: "center", yanchor: "middle",
        text: "<b>Hydro</b>", showarrow: false,
        bgcolor: t.surface, borderpad: 4,
        font: { family: t.mono, size: 12, color: t.ink }
      },
      /* Solar and bioenergy are hairlines at this scale, so they are called out
         rather than labelled in place. The near-absence is the point. */
      {
        x: last.year - 0.4, y: 99.6,
        ax: -30, ay: 46,
        xanchor: "right", yanchor: "middle",
        text: "solar, " + last.solar + "%", showarrow: true,
        arrowhead: 0, arrowsize: 1, arrowwidth: 1.2, arrowcolor: t.amber,
        bgcolor: t.surface, borderpad: 3,
        font: { family: t.mono, size: 10, color: t.amber }
      }
    ];

    var layout = Object.assign(baseLayout(t), {
      margin: { l: 48, r: 20, t: 24, b: 36 },
      xaxis: axis(t, { dtick: 5, range: [years[0], last.year] }),
      yaxis: axis(t, {
        range: [0, 100], dtick: 25, ticksuffix: "%",
        title: { text: "share of electricity", standoff: 10 }
      }),
      annotations: annotations,
      hovermode: "x unified"
    });

    return Plotly.newPlot(el, traces, layout, CONFIG);
  }

  /* ---- chapter 5, peer bars and the mix table --------------------------- */

  /* Bars are plain CSS, not Plotly. The partial "geo" build has no bar trace,
     and CSS bars match the figures in the research memo exactly. They are built
     from the same JSON the charts use, so they cannot drift from it. */
  function ch5Peers(el, data) {
    var rows = data.rows;
    var max = Math.max.apply(null, rows.map(function (d) { return d.growth_x; }));

    el.innerHTML = rows.map(function (d) {
      var width = (d.growth_x / max) * 80;   /* 80% leaves room for the value label */
      var cls = "bar-row" + (d.highlight ? " is-hl" : "");
      var fill = "bar-fill" + (d.is_reference ? " is-ghost" : "");
      return '<div class="' + cls + '">'
        + '<span class="bar-name">' + d.country + "</span>"
        + '<span class="bar-track">'
        + '<span class="' + fill + '" style="width:' + width.toFixed(1) + '%"></span>'
        + '<span class="bar-val">' + d.growth_x.toFixed(2) + "x</span>"
        + "</span></div>";
    }).join("");
  }

  function ch5MixTable(el, data) {
    var rows = data.rows;
    var years = [2000, 2010, 2020, rows[rows.length - 1].year];
    var head = "<tr><th>Source</th>"
      + years.map(function (y) { return '<th class="is-num">' + y + "</th>"; }).join("")
      + "</tr>";

    var LABELS = { gas: "Gas", hydro: "Hydro", solar: "Solar", bioenergy: "Bioenergy" };
    var body = data.sources.map(function (key) {
      var cls = key === "solar" ? ' class="is-hl"' : "";
      return "<tr" + cls + "><td>" + LABELS[key] + "</td>"
        + years.map(function (y) {
          var r = rows.filter(function (d) { return d.year === y; })[0];
          return '<td class="is-num">' + r[key].toFixed(2) + "%</td>";
        }).join("") + "</tr>";
    }).join("");

    var totals = "<tr><td>Total</td>"
      + years.map(function (y) {
        var r = rows.filter(function (d) { return d.year === y; })[0];
        return '<td class="is-num">' + r.total_pct.toFixed(2) + "%</td>";
      }).join("") + "</tr>";

    el.innerHTML = '<table><caption>Share of electricity generated, by source. '
      + 'Each figure is rounded to two decimals, so a total can differ from 100 by 0.01.'
      + '</caption>'
      + "<thead>" + head + "</thead><tbody>" + body + totals + "</tbody></table>";
  }

  /* ---- helpers ---------------------------------------------------------- */

  function fmt(n) {
    if (n === null || n === undefined) return "n/a";
    return n.toLocaleString("en-GB", { maximumFractionDigits: n < 10 ? 2 : 0 });
  }

  /* ---- registry and redraw --------------------------------------------- */

  var BUILDERS = {
    ch1Map: ch1Map,
    ch1Growth: ch1Growth,
    ch2Map: ch2Map,
    ch2Income: ch2Income,
    ch3Scatter: ch3Scatter,
    ch3Fossil: ch3Fossil,
    ch4Scatter: ch4Scatter,
    ch5Output: ch5Output,
    ch5Mix: ch5Mix,
    ch5Peers: ch5Peers,
    ch5MixTable: ch5MixTable
  };

  var mounted = [];

  function mount(elId, builderName, dataKey) {
    var el = document.getElementById(elId);
    if (!el) return;
    var data = (window.EJ_DATA || {})[dataKey];
    if (!data) {
      el.innerHTML = '<p class="fig-sub">Chart data missing: ' + dataKey + "</p>";
      return;
    }
    mounted.push({ el: el, builder: builderName, data: data });
    BUILDERS[builderName](el, data);
  }

  function redrawAll() {
    mounted.forEach(function (m) {
      Plotly.purge(m.el);
      BUILDERS[m.builder](m.el, m.data);
    });
  }

  window.EJCharts = { mount: mount, redrawAll: redrawAll, tokens: tokens, fmt: fmt };
})();
