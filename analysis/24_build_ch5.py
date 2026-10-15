"""Chapter 5, Nigeria: build the chart data.

Claim: Nigeria's electricity generation has grown nearly three times since 2000.
Its population grew nearly twice. What is left over for each person is about one
extra kilowatt-hour a year.

A note on how this chapter is framed. The research memo led with the fact that
Nigeria generated 161.5 kWh per person in 2002 and 161.4 kWh in 2024. That is
true and it is a bad headline, because 2024 is a dip year and the series runs to
2025. Measured properly, from 2002 to 2025, the trend is +1.21 kWh per person per
year. The chapter reports the trend and shows the fitted line, so the reader can
see the slope rather than take two endpoints on trust.

Outputs
  docs/data/ch5_nigeria_output.json  total generation and per person, two panels
  docs/data/ch5_nigeria_mix.json     electricity by source, stacked
  docs/data/ch5_peer_growth.json     growth per person against peers

Run from the repository root:
  python analysis/24_build_ch5.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data"

FROM, TO = 2000, 2025      # Nigeria's electricity series is complete across this span
TREND_FROM = 2002          # the first year after the step up from the 2000-2001 level
PEER_FROM, PEER_TO = 2000, 2024   # 2024, because 2025 electricity covers only 90 countries

GEN = "electricity_generation_twh"
GEN_PC = "electricity_generation_per_capita_kwh"

PEERS = ["Vietnam", "Ethiopia", "Bangladesh", "India", "Ghana",
         "World", "Nigeria", "South Africa"]

# Nigeria's electricity comes from four sources. Oil, coal and wind are 0.00% in
# every year of the series and are left out rather than drawn as empty bands.
# Bioenergy is tiny, between 0.03% and 0.16%, but it is not zero, and a stacked
# share chart whose bands do not total 100 is misreporting the mix. So it stays.
SOURCES = ["gas", "hydro", "solar", "bioenergy"]
ALL_SOURCES = ["gas", "hydro", "solar", "oil", "coal", "wind", "bioenergy",
               "other_renewables_excluding_bioenergy"]


def main():
    df = pd.read_csv(RAW)
    OUT.mkdir(parents=True, exist_ok=True)
    ng = df[df.country == "Nigeria"].set_index("year")

    # ---- output, two panels --------------------------------------------------
    rows = [
        {
            "year": int(y),
            "generation_twh": round(float(ng.loc[y, GEN]), 2),
            "generation_pc_kwh": round(float(ng.loc[y, GEN_PC]), 1),
            "population": int(ng.loc[y, "population"]),
        }
        for y in range(FROM, TO + 1)
    ]

    # Regress on the raw column, not on the rounded values written into rows.
    # Rounding first shifts the slope in the sixth decimal, which is invisible in
    # the slope itself but moves the derived "years to reach the world average"
    # by a whole year, and made this script disagree with 25_build_key_figures.py.
    yrs = np.arange(TREND_FROM, TO + 1)
    vals = np.array([float(ng.loc[y, GEN_PC]) for y in yrs])
    slope, intercept = np.polyfit(yrs, vals, 1)

    w = df[df.country == "World"].set_index("year")
    world_pc = float(w.loc[TO, GEN_PC])
    gap = world_pc - float(ng.loc[TO, GEN_PC])
    years_to_close = gap / slope

    output = {
        "meta": {
            "chart": "Nigeria's electricity, in total and per person",
            "chapter": 5,
            "years": [FROM, TO],
            "built_by": "analysis/24_build_ch5.py",
            "source_file": RAW.name,
            "source_columns": [GEN, GEN_PC, "population"],
            "n_rows": len(rows),
            "note": (
                "Two panels on one shared year axis, never two y scales on one plot. "
                "A dual axis would let the scales be chosen, and therefore the conclusion."
            ),
        },
        "rows": rows,
        "trend": {
            "from": int(TREND_FROM), "to": int(TO),
            "slope_kwh_per_year": round(float(slope), 2),
            "x": [int(TREND_FROM), int(TO)],
            "y": [round(float(slope * TREND_FROM + intercept), 1),
                  round(float(slope * TO + intercept), 1)],
        },
        "summary": {
            "gen_first": rows[0]["generation_twh"],
            "gen_last": rows[-1]["generation_twh"],
            "gen_growth_x": round(rows[-1]["generation_twh"] / rows[0]["generation_twh"], 2),
            "pop_growth_x": round(rows[-1]["population"] / rows[0]["population"], 2),
            "pc_first": rows[0]["generation_pc_kwh"],
            "pc_last": rows[-1]["generation_pc_kwh"],
            "pc_growth_x": round(rows[-1]["generation_pc_kwh"] / rows[0]["generation_pc_kwh"], 2),
            "pc_min": min(r["generation_pc_kwh"] for r in rows),
            "pc_max": max(r["generation_pc_kwh"] for r in rows),
            "pc_change_since_trend_start":
                round(rows[-1]["generation_pc_kwh"]
                      - next(r["generation_pc_kwh"] for r in rows if r["year"] == TREND_FROM), 1),
            "world_pc_last": round(world_pc, 1),
            "gap_to_world_kwh": round(gap, 1),
            "years_to_reach_world_at_this_rate": round(years_to_close),
            # stated so the memo's endpoint coincidence is on the record, not hidden
            "pc_2002": round(float(ng.loc[2002, GEN_PC]), 1),
            "pc_2024": round(float(ng.loc[2024, GEN_PC]), 1),
        },
    }

    (OUT / "ch5_nigeria_output.json").write_text(json.dumps(output, indent=1), encoding="utf-8")
    s = output["summary"]
    print("wrote ch5_nigeria_output.json")
    print(f"   generation {s['gen_first']} -> {s['gen_last']} TWh ({s['gen_growth_x']}x), "
          f"population {s['pop_growth_x']}x")
    print(f"   per person {s['pc_first']} -> {s['pc_last']} kWh ({s['pc_growth_x']}x), "
          f"band {s['pc_min']} to {s['pc_max']}")
    print(f"   trend {TREND_FROM}-{TO}: {output['trend']['slope_kwh_per_year']:+} kWh per year")
    print(f"   world is {s['world_pc_last']} kWh, gap {s['gap_to_world_kwh']}, "
          f"{s['years_to_reach_world_at_this_rate']} years at this rate")

    # ---- the mix -------------------------------------------------------------
    zero = [c for c in ALL_SOURCES
            if float(ng.loc[FROM:TO, f"{c}_electricity_share_pct"].abs().max()) == 0.0]
    mix_rows = []
    for y in range(FROM, TO + 1):
        row = {"year": int(y)}
        for src in SOURCES:
            row[src] = round(float(ng.loc[y, f"{src}_electricity_share_pct"]), 2)
            row[src + "_twh"] = round(float(ng.loc[y, f"{src}_electricity_twh"]), 2)
        row["total_pct"] = round(sum(row[s_] for s_ in SOURCES), 2)
        mix_rows.append(row)

    mix = {
        "meta": {
            "chart": "Where Nigeria's electricity comes from",
            "chapter": 5,
            "years": [FROM, TO],
            "built_by": "analysis/24_build_ch5.py",
            "source_file": RAW.name,
            "source_columns": [f"{s_}_electricity_share_pct" for s_ in SOURCES],
            "n_rows": len(mix_rows),
            "methodology_note": (
                "Shares of electricity generated, not of total energy supply, so the "
                "10 September 2026 change in how primary energy is measured does not apply."
            ),
            "omitted_sources": zero,
            "omitted_reason": "0.00% of Nigeria's electricity in every year of the series",
        },
        "sources": SOURCES,
        "rows": mix_rows,
        "summary": {
            "gas_last": mix_rows[-1]["gas"],
            "hydro_last": mix_rows[-1]["hydro"],
            "solar_last": mix_rows[-1]["solar"],
            "bioenergy_last": mix_rows[-1]["bioenergy"],
            "gas_first": mix_rows[0]["gas"],
            "hydro_first": mix_rows[0]["hydro"],
            "solar_first": mix_rows[0]["solar"],
            "solar_peak": max(r["solar"] for r in mix_rows),
            "fossil_last": mix_rows[-1]["gas"],
        },
    }

    (OUT / "ch5_nigeria_mix.json").write_text(json.dumps(mix, indent=1), encoding="utf-8")
    print("wrote ch5_nigeria_mix.json  omitted as always zero:", ", ".join(zero))
    print(f"   {TO}: gas {mix_rows[-1]['gas']}%, hydro {mix_rows[-1]['hydro']}%, "
          f"solar {mix_rows[-1]['solar']}%, bioenergy {mix_rows[-1]['bioenergy']}%")
    print(f"   bands total {mix_rows[-1]['total_pct']}% in {TO}")

    # ---- peers ---------------------------------------------------------------
    peer_rows = []
    for name in PEERS:
        p = df[df.country == name].set_index("year")
        a, b = float(p.loc[PEER_FROM, GEN_PC]), float(p.loc[PEER_TO, GEN_PC])
        peer_rows.append({
            "country": name,
            "kwh_first": round(a, 1),
            "kwh_last": round(b, 1),
            "growth_x": round(b / a, 2),
            "highlight": name == "Nigeria",
            "is_reference": name == "World",
        })
    peer_rows.sort(key=lambda r: r["growth_x"], reverse=True)

    peers = {
        "meta": {
            "chart": "Growth in electricity generated per person",
            "chapter": 5,
            "from": PEER_FROM, "to": PEER_TO,
            "built_by": "analysis/24_build_ch5.py",
            "source_file": RAW.name,
            "source_columns": [GEN_PC],
            "n_rows": len(peer_rows),
            "note": (
                f"{PEER_TO} and not 2025, because 2025 electricity is reported for only "
                "90 of 220 countries and a peer comparison needs every country present."
            ),
        },
        "rows": peer_rows,
    }

    (OUT / "ch5_peer_growth.json").write_text(json.dumps(peers, indent=1), encoding="utf-8")
    print(f"wrote ch5_peer_growth.json  {PEER_FROM} to {PEER_TO}")
    for r in peer_rows:
        print(f"   {r['country']:14s} {r['kwh_first']:>8} -> {r['kwh_last']:>8} kWh  "
              f"{r['growth_x']}x")

    # ---- sanity checks -------------------------------------------------------
    assert all(abs(r["total_pct"] - 100.0) < 0.05 for r in mix_rows), \
        "the three sources must account for all of Nigeria's electricity"
    assert set(zero) >= {"oil", "coal", "wind"}, zero
    assert output["trend"]["slope_kwh_per_year"] > 0, \
        "the trend is slightly positive and the chapter must not call it flat"
    assert s["gen_growth_x"] > s["pop_growth_x"], \
        "generation did outgrow population, which is the point of the two panels"
    assert next(r for r in peer_rows if r["country"] == "Nigeria")["growth_x"] < \
        next(r for r in peer_rows if r["country"] == "World")["growth_x"]
    print("checks passed")


if __name__ == "__main__":
    main()
