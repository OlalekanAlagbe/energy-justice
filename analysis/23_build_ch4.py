"""Chapter 4, "Who is mined": build the chart data.

Claim: a group of thirteen countries, 742 million people between them, produce
far more fossil energy than they use and their people get very little
electricity. This describes those countries. It is not a rule about exporters.

The honest limit is built into the output: across all countries the rank
correlation between the production ratio and electricity per person is 0.15.
Norway produces 7.6 times its own supply and is among the highest-consuming
countries on earth. The pattern is a quadrant, not a law, and the chapter says so.

Outputs
  docs/data/ch4_production_vs_power.json

Run from the repository root:
  python analysis/23_build_ch4.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data"

YEAR = 2024
MIN_POP = 1_000_000
RATIO_MIN = 1.5      # produces at least half as much again as it consumes
DEMAND_MAX = 2000    # kWh per person, below the world average of about 3,800

DEMAND = "electricity_demand_per_capita_kwh"
GEN = "electricity_generation_per_capita_kwh"
PRODUCTION = ["oil_production_twh", "gas_production_twh", "coal_production_twh"]

# Named on the chart. Nigeria is the subject. Norway and Qatar are the
# counter-examples that stop the quadrant being read as a law. The rest are the
# extremes of the group itself.
LABELLED = ["Nigeria", "Norway", "Qatar", "Chad", "Angola", "Indonesia"]


def main():
    df = pd.read_csv(RAW)
    OUT.mkdir(parents=True, exist_ok=True)

    e = df[(df.year == YEAR) & (df.iso_code.notna()) & (df.population > MIN_POP)].copy()
    e["prod_twh"] = e[PRODUCTION].sum(axis=1, min_count=1)
    e = e[e.prod_twh.notna() & e.total_energy_twh.notna() & (e.total_energy_twh > 0)].copy()
    e["ratio"] = e.prod_twh / e.total_energy_twh

    scored = e[e[DEMAND].notna()].copy()
    scored["in_group"] = (scored.ratio > RATIO_MIN) & (scored[DEMAND] < DEMAND_MAX)

    rho = float(np.corrcoef(scored.ratio.rank(), scored[DEMAND].rank())[0, 1])

    # The same filter on generation instead of demand, to show the group is not
    # an artefact of which electricity column was chosen.
    alt = e[e[GEN].notna()]
    alt_group = set(alt.loc[(alt.ratio > RATIO_MIN) & (alt[GEN] < DEMAND_MAX), "country"])
    group = set(scored.loc[scored.in_group, "country"])

    rows = [
        {
            "iso": t.iso_code,
            "country": t.country,
            "prod_twh": round(float(t.prod_twh), 1),
            "total_energy_twh": round(float(t.total_energy_twh), 1),
            "ratio": round(float(t.ratio), 2),
            "demand_pc_kwh": round(float(getattr(t, DEMAND)), 1),
            "population": int(t.population),
            "in_group": bool(t.in_group),
            "highlight": t.country == "Nigeria",
            "label": t.country if t.country in LABELLED else None,
        }
        for t in scored.sort_values("ratio").itertuples()
    ]

    g = scored[scored.in_group]
    group_pop = int(g.population.sum())
    nigeria = scored[scored.country == "Nigeria"].iloc[0]

    payload = {
        "meta": {
            "chart": "Fossil fuel produced against electricity used, per country",
            "chapter": 4,
            "year": YEAR,
            "built_by": "analysis/23_build_ch4.py",
            "source_file": RAW.name,
            "source_columns": PRODUCTION + ["total_energy_twh", DEMAND, "population", "iso_code"],
            "filter": f"iso_code present, population over {MIN_POP:,}, production and "
                      f"total energy supply both reported",
            "n_rows": len(rows),
            "note": (
                "The horizontal axis is production divided by the country's own total energy "
                "supply. It is an accounting residual, not measured trade: the sources warn "
                "that production and consumption figures do not reconcile exactly. Gas that "
                "is flared is excluded from production entirely, which matters for Nigeria."
            ),
        },
        "thresholds": {"ratio_min": RATIO_MIN, "demand_max": DEMAND_MAX},
        "rows": rows,
        "stats": {
            "n": len(rows),
            "spearman_ratio_vs_demand": round(rho, 3),
            "group_n": int(len(g)),
            "group_pop": group_pop,
            "group_pop_millions": round(group_pop / 1e6),
            "nigeria_share_of_group_pct": round(float(nigeria.population) / group_pop * 100, 1),
            "producers_above_threshold": int((scored.ratio > RATIO_MIN).sum()),
            "produce_nothing": int((scored.ratio == 0).sum()),
            "same_group_using_generation": sorted(group) == sorted(alt_group),
            "group_members": sorted(group),
        },
        "nigeria": {
            "prod_twh": round(float(nigeria.prod_twh), 1),
            "total_energy_twh": round(float(nigeria.total_energy_twh), 1),
            "ratio": round(float(nigeria.ratio), 2),
            "demand_pc_kwh": round(float(nigeria[DEMAND]), 1),
            "population": int(nigeria.population),
        },
    }

    (OUT / "ch4_production_vs_power.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")

    st = payload["stats"]
    print(f"wrote ch4_production_vs_power.json  {st['n']} countries")
    print(f"   group: {st['group_n']} countries, {st['group_pop_millions']}m people, "
          f"Nigeria is {st['nigeria_share_of_group_pct']}% of it")
    print(f"   rank correlation across all countries: {st['spearman_ratio_vs_demand']}")
    print(f"   {st['producers_above_threshold']} countries clear the production threshold, "
          f"only {st['group_n']} are also below {DEMAND_MAX} kWh")
    print(f"   {st['produce_nothing']} countries produce no fossil fuel at all")
    print(f"   same group if generation is used instead of demand: "
          f"{st['same_group_using_generation']}")
    print("   members:", ", ".join(st["group_members"]))

    # ---- sanity checks -------------------------------------------------------
    assert st["group_n"] == 13, st["group_n"]
    assert st["group_pop_millions"] == 742, st["group_pop_millions"]
    assert st["same_group_using_generation"], \
        "the group changes with the electricity column, so it is not robust"
    assert abs(st["spearman_ratio_vs_demand"]) < 0.3, \
        "if this ever becomes a strong correlation the chapter's framing must change"
    assert "Norway" not in st["group_members"], "Norway is the counter-example"
    assert "Nigeria" in st["group_members"]
    print("checks passed")


if __name__ == "__main__":
    main()
