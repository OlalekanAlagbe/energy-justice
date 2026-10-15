"""Chapter 1, "Who is counted": build the chart data.

Claim: this dataset describes the rich world's energy in detail and most of the
world's hardly at all, and that gap has not closed in 54 years.

Outputs
  docs/data/ch1_coverage_map.json    two-state choropleth, 2024
  docs/data/ch1_panel_growth.json    size of the measured panel by year

Run from the repository root:
  python analysis/20_build_ch1.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data"

HEADLINE_YEAR = 2024

# The dataset has no region column, so Africa has to be named explicitly to count
# how many African countries are measured. This is the 54 UN member states of
# Africa, using the dataset's own spelling of each country name. Kept here rather
# than in a separate file so the count is auditable beside the number it produces.
AFRICA = [
    "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cameroon",
    "Cape Verde", "Central African Republic", "Chad", "Comoros", "Congo",
    "Cote d'Ivoire", "Democratic Republic of Congo", "Djibouti", "Egypt",
    "Equatorial Guinea", "Eritrea", "Eswatini", "Ethiopia", "Gabon", "Gambia",
    "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Lesotho", "Liberia", "Libya",
    "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Morocco",
    "Mozambique", "Namibia", "Niger", "Nigeria", "Rwanda", "Sao Tome and Principe",
    "Senegal", "Seychelles", "Sierra Leone", "Somalia", "South Africa",
    "South Sudan", "Sudan", "Tanzania", "Togo", "Tunisia", "Uganda", "Zambia",
    "Zimbabwe",
]

# A country is "measured" if the dataset gives it an energy mix, not just a total.
# fossil_fuels_energy_twh is the test: it is the aggregate every mix breakdown
# needs, so if it is missing the mix is missing.
MIX_TEST_COLUMN = "fossil_fuels_energy_twh"


def nn(v):
    """None for pandas NA, so the JSON has null rather than NaN, which is invalid JSON."""
    return None if pd.isna(v) else v


def main():
    df = pd.read_csv(RAW)
    OUT.mkdir(parents=True, exist_ok=True)

    # Countries only. iso_code is empty for every region and aggregate, which is
    # the clean separator. Kosovo has no ISO code and so is excluded here; it is
    # one country and does not move any figure in this chapter.
    c = df[(df.year == HEADLINE_YEAR) & (df.iso_code.notna())].copy()
    c["measured"] = c[MIX_TEST_COLUMN].notna().astype(int)

    world_pop = float(df[(df.country == "World") & (df.year == HEADLINE_YEAR)].population.iloc[0])
    not_measured_pop = float(c.loc[c.measured == 0, "population"].sum())

    af = c[c.country.isin(AFRICA)]
    missing_from_data = sorted(set(AFRICA) - set(c.country))
    if missing_from_data:
        print("NOTE: African countries with no", HEADLINE_YEAR, "row:", missing_from_data)

    rows = [
        {
            "iso": r.iso_code,
            "country": r.country,
            "measured": int(r.measured),
            "total_energy_twh": nn(round(r.total_energy_twh, 2) if pd.notna(r.total_energy_twh) else None),
            "electricity_twh": nn(round(r.electricity_generation_twh, 2) if pd.notna(r.electricity_generation_twh) else None),
            "population": nn(int(r.population) if pd.notna(r.population) else None),
        }
        for r in c.sort_values("country").itertuples()
    ]

    coverage = {
        "meta": {
            "chart": "Does this country have an energy mix breakdown",
            "chapter": 1,
            "year": HEADLINE_YEAR,
            "built_by": "analysis/20_build_ch1.py",
            "source_file": RAW.name,
            "source_columns": [
                "iso_code", "country", MIX_TEST_COLUMN, "total_energy_twh",
                "electricity_generation_twh", "population",
            ],
            "filter": "iso_code present, so countries only and no regions or aggregates",
            "n_rows": len(rows),
        },
        "rows": rows,
        "summary": {
            "measured": int(c.measured.sum()),
            "not_measured": int((c.measured == 0).sum()),
            "total_countries": len(c),
            "pop_share_not_measured_pct": round(not_measured_pop / world_pop * 100, 1),
            "with_total_energy": int(c.total_energy_twh.notna().sum()),
            "with_electricity": int(c.electricity_generation_twh.notna().sum()),
            "know_total_not_mix": int((c.total_energy_twh.notna() & (c.measured == 0)).sum()),
            "africa_measured": int(af.measured.sum()),
            "africa_total": len(af),
            "africa_measured_names": sorted(af.loc[af.measured == 1, "country"].tolist()),
        },
    }

    (OUT / "ch1_coverage_map.json").write_text(
        json.dumps(coverage, indent=1), encoding="utf-8")
    print("wrote ch1_coverage_map.json  ",
          coverage["summary"]["measured"], "measured /",
          coverage["summary"]["not_measured"], "not measured")

    # ---- panel growth over time -------------------------------------------------
    # One row per year: how many countries the dataset can describe, three ways.
    years = range(1965, HEADLINE_YEAR + 1)
    growth_rows = []
    for y in years:
        cy = df[(df.year == y) & (df.iso_code.notna())]
        growth_rows.append({
            "year": int(y),
            "with_mix": int(cy[MIX_TEST_COLUMN].notna().sum()),
            "with_total": int(cy.total_energy_twh.notna().sum()),
            "with_electricity": int(cy.electricity_generation_twh.notna().sum()),
            "rows_total": int(len(cy)),
        })

    growth = {
        "meta": {
            "chart": "How many countries the dataset can describe, by year",
            "chapter": 1,
            "years": [int(min(years)), int(max(years))],
            "built_by": "analysis/20_build_ch1.py",
            "source_file": RAW.name,
            "source_columns": [
                "iso_code", MIX_TEST_COLUMN, "total_energy_twh", "electricity_generation_twh",
            ],
            "n_rows": len(growth_rows),
            "note": (
                "Electricity before 1985 is close to zero here because only the United "
                "Kingdom and the world aggregate have country-level electricity that far "
                "back. That is a fact about the data, not about electricity."
            ),
        },
        "rows": growth_rows,
        "summary": {
            "mix_1970": next(r["with_mix"] for r in growth_rows if r["year"] == 1970),
            "mix_2024": next(r["with_mix"] for r in growth_rows if r["year"] == HEADLINE_YEAR),
            "span_years": HEADLINE_YEAR - 1970,
        },
    }

    (OUT / "ch1_panel_growth.json").write_text(
        json.dumps(growth, indent=1), encoding="utf-8")
    print("wrote ch1_panel_growth.json  mix panel",
          growth["summary"]["mix_1970"], "in 1970 ->",
          growth["summary"]["mix_2024"], "in", HEADLINE_YEAR)

    # ---- sanity checks, loud failure beats a quiet wrong number -----------------
    s = coverage["summary"]
    assert s["measured"] + s["not_measured"] == s["total_countries"]
    assert s["measured"] == 74, s["measured"]
    assert s["not_measured"] == 146, s["not_measured"]
    assert s["africa_measured"] == 4, s["africa_measured"]
    assert s["africa_total"] == 54, s["africa_total"]
    assert s["know_total_not_mix"] == 144, s["know_total_not_mix"]
    nigeria = next(r for r in rows if r["iso"] == "NGA")
    assert nigeria["measured"] == 0, "Nigeria should have no energy mix"
    print("checks passed")


if __name__ == "__main__":
    main()
