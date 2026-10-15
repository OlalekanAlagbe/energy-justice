"""Chapter 3, "The mix is not the story": build the chart data.

Claim: how clean a country's electricity is tells you nothing about how much of
it people get.

Outputs
  docs/data/ch3_amount_vs_mix.json  the scatter, and the correlation that is a null
  docs/data/ch3_world_fossil.json   world fossil supply, absolute against share
  docs/data/ch3_growth_trap.json    why this site reports absolute change

Run from the repository root:
  python analysis/22_build_ch3.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data"

SCATTER_YEAR = 2023      # the broadest year for electricity
MIN_POP = 1_000_000      # below this, one power station moves a country's whole mix
FOSSIL_FROM, FOSSIL_TO = 1965, 2024
TRAP_FROM, TRAP_TO = 2015, 2024

DEMAND = "electricity_demand_per_capita_kwh"
LOWC = "low_carbon_electricity_share_pct"

# Countries named on the scatter. Picked to show the spread at the low-access end,
# which is the part of the chart that carries the argument: these countries have
# similar amounts of electricity and nothing in common in their mix.
LABELLED = ["Nigeria", "Ethiopia", "Bangladesh", "India", "Norway"]


def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x, y):
    """From ranks, so the project does not need scipy."""
    return float(np.corrcoef(pd.Series(x).rank(), pd.Series(y).rank())[0, 1])


def main():
    df = pd.read_csv(RAW)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- the scatter ---------------------------------------------------------
    c = df[(df.year == SCATTER_YEAR) & (df.iso_code.notna()) & (df.population > MIN_POP)]
    c = c[c[DEMAND].notna() & c[LOWC].notna()].copy()

    x_log = np.log10(c[DEMAND].to_numpy())
    y = c[LOWC].to_numpy()

    r = pearson(x_log, y)
    rho = spearman(c[DEMAND].to_numpy(), y)

    # The flat fit, drawn so the absence of a relationship is visible rather than
    # asserted. Least squares on log10(demand).
    slope, intercept = np.polyfit(x_log, y, 1)
    x_fit = [float(c[DEMAND].min()) * 0.8, float(c[DEMAND].max()) * 1.2]
    y_fit = [float(slope * np.log10(v) + intercept) for v in x_fit]

    rows = [
        {
            "iso": t.iso_code,
            "country": t.country,
            "demand_pc_kwh": round(float(getattr(t, DEMAND)), 1),
            "low_carbon_pct": round(float(getattr(t, LOWC)), 1),
            "population": int(t.population),
            "highlight": t.country == "Nigeria",
            "label": t.country if t.country in LABELLED else None,
        }
        for t in c.sort_values("population", ascending=False).itertuples()
    ]

    scatter = {
        "meta": {
            "chart": "Electricity per person against the low-carbon share of it",
            "chapter": 3,
            "year": SCATTER_YEAR,
            "built_by": "analysis/22_build_ch3.py",
            "source_file": RAW.name,
            "source_columns": ["iso_code", "country", DEMAND, LOWC, "population"],
            "filter": f"iso_code present, population over {MIN_POP:,}, both values reported",
            "n_rows": len(rows),
            "methodology_note": (
                "Low-carbon share here is a share of electricity generated, not of total "
                "energy supply. The two are different denominators and the electricity one "
                "is unaffected by the September 2026 change in how primary energy is measured."
            ),
        },
        "rows": rows,
        "fit": {"x": x_fit, "y": y_fit, "slope_per_decade": round(float(slope), 2)},
        "stats": {
            "n": len(rows),
            "pearson_r_log10": round(r, 4),
            "spearman": round(rho, 3),
            "r_squared": round(r * r, 4),
            "demand_p10": round(float(c[DEMAND].quantile(0.10))),
            "demand_p90": round(float(c[DEMAND].quantile(0.90))),
            "demand_spread": round(float(c[DEMAND].quantile(0.90) / c[DEMAND].quantile(0.10))),
            "low_carbon_p10": round(float(c[LOWC].quantile(0.10)), 1),
            "low_carbon_p90": round(float(c[LOWC].quantile(0.90)), 1),
        },
    }

    (OUT / "ch3_amount_vs_mix.json").write_text(json.dumps(scatter, indent=1), encoding="utf-8")
    st = scatter["stats"]
    print(f"wrote ch3_amount_vs_mix.json  n={st['n']}  r={st['pearson_r_log10']}  "
          f"rho={st['spearman']}  r2={st['r_squared']}")
    print(f"   demand p10-p90 {st['demand_p10']} to {st['demand_p90']} kWh "
          f"({st['demand_spread']}x)")
    print(f"   low-carbon p10-p90 {st['low_carbon_p10']}% to {st['low_carbon_p90']}%")
    print(f"   fitted slope {scatter['fit']['slope_per_decade']} points per 10x more electricity")

    # ---- world fossil, absolute against share --------------------------------
    w = df[df.country == "World"].set_index("year")
    yrs = [y for y in range(FOSSIL_FROM, FOSSIL_TO + 1)
           if pd.notna(w.loc[y, "fossil_fuels_energy_twh"])]
    fossil_rows = [
        {
            "year": int(y),
            "fossil_twh": round(float(w.loc[y, "fossil_fuels_energy_twh"]), 1),
            "fossil_share_pct": round(float(w.loc[y, "fossil_fuels_energy_share_pct"]), 2),
        }
        for y in yrs
    ]

    a, b = fossil_rows[0], fossil_rows[-1]
    i2000 = next(r for r in fossil_rows if r["year"] == 2000)
    # Keep these unrounded until the last step. Rounding each source first and
    # then summing shifts the totals by a terawatt-hour, which is small but is
    # exactly the kind of drift that makes a figure impossible to reproduce.
    added = {}
    for src in ("coal", "gas", "solar", "wind"):
        added[src] = float(w.loc[2024, f"{src}_energy_twh"] - w.loc[2000, f"{src}_energy_twh"])

    fossil = {
        "meta": {
            "chart": "World fossil fuel supply, absolute and as a share",
            "chapter": 3,
            "entity": "World",
            "years": [a["year"], b["year"]],
            "built_by": "analysis/22_build_ch3.py",
            "source_file": RAW.name,
            "source_columns": ["fossil_fuels_energy_twh", "fossil_fuels_energy_share_pct",
                               "coal_energy_twh", "gas_energy_twh",
                               "solar_energy_twh", "wind_energy_twh"],
            "n_rows": len(fossil_rows),
            "methodology_note": (
                "Total energy supply, the method Our World in Data adopted on 10 September "
                "2026. Earlier releases used the substitution method and are not comparable."
            ),
        },
        "rows": fossil_rows,
        "summary": {
            "twh_2000": i2000["fossil_twh"],
            "twh_2024": b["fossil_twh"],
            "abs_change_twh": round(float(w.loc[2024, "fossil_fuels_energy_twh"]
                                          - w.loc[2000, "fossil_fuels_energy_twh"])),
            "pct_change": round(float(w.loc[2024, "fossil_fuels_energy_twh"]
                                      / w.loc[2000, "fossil_fuels_energy_twh"] - 1) * 100, 1),
            "share_2000": i2000["fossil_share_pct"],
            "share_2024": b["fossil_share_pct"],
            "share_change_pp": round(float(w.loc[2024, "fossil_fuels_energy_share_pct"]
                                           - w.loc[2000, "fossil_fuels_energy_share_pct"]), 2),
            "coal_gas_added_twh": round(added["coal"] + added["gas"]),
            "solar_wind_added_twh": round(added["solar"] + added["wind"]),
            "ratio": round((added["coal"] + added["gas"]) / (added["solar"] + added["wind"]), 1),
        },
    }

    (OUT / "ch3_world_fossil.json").write_text(json.dumps(fossil, indent=1), encoding="utf-8")
    sm = fossil["summary"]
    print(f"wrote ch3_world_fossil.json  {sm['twh_2000']} -> {sm['twh_2024']} TWh "
          f"({sm['pct_change']:+}%), share {sm['share_2000']} -> {sm['share_2024']} "
          f"({sm['share_change_pp']:+} pp)")
    print(f"   coal+gas added {sm['coal_gas_added_twh']} TWh, "
          f"solar+wind added {sm['solar_wind_added_twh']} TWh, ratio {sm['ratio']}x")

    # ---- the growth-rate trap ------------------------------------------------
    trap_rows = []
    for name in ("Vietnam", "China"):
        p = df[df.country == name].set_index("year")
        a_, b_ = float(p.loc[TRAP_FROM, "solar_electricity_twh"]), \
            float(p.loc[TRAP_TO, "solar_electricity_twh"])
        trap_rows.append({
            "country": name,
            "twh_from": round(a_, 2),
            "twh_to": round(b_, 2),
            "added_twh": round(b_ - a_, 2),
            "pct_growth": round((b_ / a_ - 1) * 100),
        })

    trap = {
        "meta": {
            "chart": "Why this site reports absolute change, not percentage growth",
            "chapter": 3,
            "from": TRAP_FROM,
            "to": TRAP_TO,
            "built_by": "analysis/22_build_ch3.py",
            "source_file": RAW.name,
            "source_columns": ["solar_electricity_twh"],
            "n_rows": len(trap_rows),
            "note": (
                "Both figures are correct. Vietnam's percentage is larger because its "
                "starting point was 0.01 TWh. Percentage growth from a near-zero base "
                "measures the base, not the achievement."
            ),
        },
        "rows": trap_rows,
    }

    (OUT / "ch3_growth_trap.json").write_text(json.dumps(trap, indent=1), encoding="utf-8")
    for r_ in trap_rows:
        print(f"wrote trap row  {r_['country']:8s} {r_['twh_from']:>7} -> {r_['twh_to']:>7} TWh  "
              f"added {r_['added_twh']:>7}  growth {r_['pct_growth']:,}%")

    # ---- sanity checks -------------------------------------------------------
    assert st["n"] == 158, st["n"]
    assert abs(st["pearson_r_log10"]) < 0.01, "the null result changed, re-read the data"
    assert sm["share_change_pp"] < 0 and sm["abs_change_twh"] > 0, \
        "the chapter's point is that these move in opposite directions"
    assert sm["solar_wind_added_twh"] == 4649, sm["solar_wind_added_twh"]
    assert sm["share_change_pp"] == -2.46, sm["share_change_pp"]
    assert trap_rows[0]["pct_growth"] > trap_rows[1]["pct_growth"]
    assert trap_rows[0]["added_twh"] < trap_rows[1]["added_twh"]
    print("checks passed")


if __name__ == "__main__":
    main()
