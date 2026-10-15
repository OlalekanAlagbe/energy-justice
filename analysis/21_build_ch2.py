"""Chapter 2, "Who is powered": build the chart data.

Claim: the electricity gap between rich and poor countries has not closed in
24 years.

Outputs
  docs/data/ch2_demand_map.json     choropleth of electricity demand per person
  docs/data/ch2_income_groups.json  four income-group lines, 2000 to 2024

Run from the repository root:
  python analysis/21_build_ch2.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data"

MAP_YEAR = 2023      # the broadest year for electricity: 212 countries, against 196 in 2024
LINE_FROM, LINE_TO = 2000, 2024

# Demand per person runs from 0 to over 51,000 kWh, so a linear colour scale
# would put four fifths of the world in one band. These breaks are round numbers
# chosen to spread countries across the ramp. Counts per band are printed below
# and are in the JSON, so the choice can be checked rather than taken on trust.
BREAKS = [0, 100, 500, 1000, 3000, 6000, 12000]
BAND_LABELS = [
    "under 100", "100 to 500", "500 to 1,000", "1,000 to 3,000",
    "3,000 to 6,000", "6,000 to 12,000", "12,000 and over",
]

INCOME_GROUPS = [
    "Low-income countries",
    "Lower-middle-income countries",
    "Upper-middle-income countries",
    "High-income countries",
]

DEMAND = "electricity_demand_per_capita_kwh"
GEN = "electricity_generation_per_capita_kwh"


def band_of(v):
    """Index into BREAKS, 0 based. Right edge open, so 100 falls in band 1."""
    b = 0
    for i, edge in enumerate(BREAKS):
        if v >= edge:
            b = i
    return b


def nn(v, nd=1):
    return None if pd.isna(v) else round(float(v), nd)


def main():
    df = pd.read_csv(RAW)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- the map -------------------------------------------------------------
    c = df[(df.year == MAP_YEAR) & (df.iso_code.notna())].copy()
    have = c[c[DEMAND].notna()].copy()
    have["band"] = have[DEMAND].map(band_of)

    rows = [
        {
            "iso": r.iso_code,
            "country": r.country,
            "demand_pc_kwh": nn(getattr(r, DEMAND)),
            "generation_pc_kwh": nn(getattr(r, GEN)),
            "band": int(r.band),
            "population": int(r.population) if pd.notna(r.population) else None,
        }
        for r in have.sort_values("country").itertuples()
    ]

    d = have[DEMAND]
    nigeria = float(have.loc[have.country == "Nigeria", DEMAND].iloc[0])
    world = float(df[(df.country == "World") & (df.year == MAP_YEAR)][DEMAND].iloc[0])

    band_counts = [int((have.band == i).sum()) for i in range(len(BREAKS))]

    demand_map = {
        "meta": {
            "chart": "Electricity demand per person",
            "chapter": 2,
            "year": MAP_YEAR,
            "built_by": "analysis/21_build_ch2.py",
            "source_file": RAW.name,
            "source_columns": ["iso_code", "country", DEMAND, GEN, "population"],
            "filter": "iso_code present, demand per person reported",
            "n_rows": len(rows),
            "note": (
                "Demand, not generation. Generation alone would call Lesotho the poorest "
                "country on earth, because it generates almost nothing and imports what it "
                "uses. Neither column says how many households are connected."
            ),
        },
        "breaks": BREAKS,
        "band_labels": BAND_LABELS,
        "band_counts": band_counts,
        "rows": rows,
        "summary": {
            "n": len(rows),
            "median_kwh": round(float(d.median()), 1),
            "world_kwh": round(world, 1),
            "nigeria_kwh": round(nigeria, 1),
            "nigeria_percentile": round(float((d < nigeria).mean() * 100), 1),
            "min_country": str(have.loc[d.idxmin(), "country"]),
            "min_kwh": round(float(d.min()), 1),
            "max_country": str(have.loc[d.idxmax(), "country"]),
            "max_kwh": round(float(d.max()), 1),
        },
    }

    (OUT / "ch2_demand_map.json").write_text(json.dumps(demand_map, indent=1), encoding="utf-8")
    print("wrote ch2_demand_map.json ", len(rows), "countries")
    for lab, n in zip(BAND_LABELS, band_counts):
        print(f"   {lab:>18s} kWh  {n:3d} countries")

    # ---- the four income-group lines ----------------------------------------
    g = df[df.country.isin(INCOME_GROUPS) & df.year.between(LINE_FROM, LINE_TO)]
    piv = g.pivot_table(index="year", columns="country", values=GEN)
    piv = piv.dropna()  # only years where all four groups are reported

    series = [
        {
            "group": name,
            "short": name.replace(" countries", "").replace("-income", ""),
            "points": [
                {"year": int(y), "kwh_pc": round(float(piv.loc[y, name]), 1)}
                for y in piv.index
            ],
        }
        for name in INCOME_GROUPS
    ]

    first, last = int(piv.index.min()), int(piv.index.max())
    hi, lo = "High-income countries", "Low-income countries"
    ratio_first = piv.loc[first, hi] / piv.loc[first, lo]
    ratio_last = piv.loc[last, hi] / piv.loc[last, lo]

    income = {
        "meta": {
            "chart": "Electricity generated per person, by income group",
            "chapter": 2,
            "years": [first, last],
            "built_by": "analysis/21_build_ch2.py",
            "source_file": RAW.name,
            "source_columns": ["country", "year", GEN],
            "filter": "only years in which all four income groups are reported",
            "n_rows": len(piv),
            "note": (
                "These are the dataset's own income-group aggregates. Membership is held "
                "fixed: no group's population moves more than 5 per cent year on year "
                "anywhere in the series, so this is not countries being reclassified."
            ),
        },
        "series": series,
        "summary": {
            "first_year": first,
            "last_year": last,
            "ratio_first": round(float(ratio_first), 1),
            "ratio_last": round(float(ratio_last), 1),
            "high_first": round(float(piv.loc[first, hi]), 1),
            "high_last": round(float(piv.loc[last, hi]), 1),
            "low_first": round(float(piv.loc[first, lo]), 1),
            "low_last": round(float(piv.loc[last, lo]), 1),
            "high_gain": round(float(piv.loc[last, hi] - piv.loc[first, hi])),
            "low_gain": round(float(piv.loc[last, lo] - piv.loc[first, lo])),
        },
    }

    (OUT / "ch2_income_groups.json").write_text(json.dumps(income, indent=1), encoding="utf-8")
    s = income["summary"]
    print("wrote ch2_income_groups.json", first, "to", last)
    print(f"   high income {s['high_first']} -> {s['high_last']} kWh  (+{s['high_gain']})")
    print(f"   low income  {s['low_first']} -> {s['low_last']} kWh  (+{s['low_gain']})")
    print(f"   ratio {s['ratio_first']}x -> {s['ratio_last']}x")

    # ---- the population stability check this chapter's note claims -----------
    pop = df[df.country.isin(INCOME_GROUPS)].pivot_table(
        index="year", columns="country", values="population")
    worst = float(pop.pct_change().abs().max().max() * 100)
    print(f"   largest year on year population move in any group: {worst:.2f}%")
    assert worst < 5, "income group membership is not stable, the comparison would be unsound"

    # ---- sanity checks -------------------------------------------------------
    assert len(rows) == 212, len(rows)
    assert sum(band_counts) == len(rows)
    assert s["ratio_first"] == 44.2, s["ratio_first"]
    assert s["ratio_last"] == 43.6, s["ratio_last"]
    assert demand_map["summary"]["min_country"] == "Niue", demand_map["summary"]["min_country"]
    assert demand_map["summary"]["max_country"] == "Iceland"
    print("checks passed")


if __name__ == "__main__":
    main()
