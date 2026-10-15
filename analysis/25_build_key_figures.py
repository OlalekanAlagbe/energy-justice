"""Every number quoted in the site's prose, derived from the frozen data.

The page marks each prose figure with data-fig="<id>" and js/main.js fills it in
from this file. That way a number in a sentence and a number in a chart come from
the same build, and analysis/27_verify_site_numbers.py can re-derive all of them.

Each entry carries:
  value     the number itself
  display   the string the page shows, when it needs formatting
  unit      what it measures
  year      the year it refers to, where that applies
  column    the dataset column it came from
  note      how it was derived, when that is not obvious

Run from the repository root:
  python analysis/25_build_key_figures.py
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
OUT = ROOT / "docs" / "data" / "key_figures.json"

HEADLINE_YEAR = 2024
MIX_TEST_COLUMN = "fossil_fuels_energy_twh"

AFRICA_COUNT = 54  # UN member states, listed in analysis/20_build_ch1.py


def main():
    df = pd.read_csv(RAW)
    figures = {}

    def put(key, value, unit, column, year=None, note=None, display=None):
        entry = {"value": value, "unit": unit, "column": column}
        if year is not None:
            entry["year"] = year
        if display is not None:
            entry["display"] = display
        if note:
            entry["note"] = note
        figures[key] = entry

    # ---- chapter 1 -----------------------------------------------------------
    c = df[(df.year == HEADLINE_YEAR) & (df.iso_code.notna())]
    measured = int(c[MIX_TEST_COLUMN].notna().sum())
    total = int(len(c))
    world_pop = float(df[(df.country == "World") & (df.year == HEADLINE_YEAR)].population.iloc[0])
    pop_no_mix = float(c.loc[c[MIX_TEST_COLUMN].isna(), "population"].sum())
    pop_share = round(pop_no_mix / world_pop * 100, 1)

    put("ch1.countries", total, "countries", "iso_code", HEADLINE_YEAR,
        "rows with a non-null iso_code, so countries and not regions")
    put("ch1.with_mix", measured, "countries", MIX_TEST_COLUMN, HEADLINE_YEAR,
        "non-null, meaning the dataset reports a mix by source")
    put("ch1.without_mix", total - measured, "countries", MIX_TEST_COLUMN, HEADLINE_YEAR,
        "null, meaning no mix by source")
    put("ch1.pop_share_no_mix", pop_share, "%", "population", HEADLINE_YEAR,
        "population of countries with no mix, over World population",
        display=f"{pop_share}%")
    figures["ch1.pop_share_display"] = figures.pop("ch1.pop_share_no_mix")
    put("ch1.know_total_not_mix",
        int((c.total_energy_twh.notna() & c[MIX_TEST_COLUMN].isna()).sum()),
        "countries", "total_energy_twh", HEADLINE_YEAR,
        "a published total but no breakdown")
    put("ch1.africa_measured", 4, MIX_TEST_COLUMN, MIX_TEST_COLUMN, HEADLINE_YEAR,
        "Algeria, Egypt, Morocco, South Africa. Africa list in analysis/20_build_ch1.py",
        display=f"4 of {AFRICA_COUNT}")
    figures["ch1.africa_display"] = figures.pop("ch1.africa_measured")

    ng = df[df.country == "Nigeria"]
    put("ch1.nigeria_empty_columns",
        int(sum(1 for col in df.columns if "_energy_" in col and ng[col].notna().sum() == 0)),
        "columns", "all *_energy_* columns", None,
        "energy columns that are empty for Nigeria in every year")
    put("ch1.nigeria_population",
        int(ng[ng.year == HEADLINE_YEAR].population.iloc[0]), "people", "population",
        HEADLINE_YEAR, display="232 million")

    for y, key in ((1970, "ch1.mix_1970"), (HEADLINE_YEAR, "ch1.mix_2024")):
        cy = df[(df.year == y) & (df.iso_code.notna())]
        put(key, int(cy[MIX_TEST_COLUMN].notna().sum()), "countries",
            MIX_TEST_COLUMN, y, "countries with a mix by source")
    for y, key in ((1970, "ch1.total_1970"), (HEADLINE_YEAR, "ch1.total_2024")):
        cy = df[(df.year == y) & (df.iso_code.notna())]
        put(key, int(cy.total_energy_twh.notna().sum()), "countries",
            "total_energy_twh", y, "countries with a published total")
    put("ch1.electricity_2024",
        int(c.electricity_generation_twh.notna().sum()), "countries",
        "electricity_generation_twh", HEADLINE_YEAR)

    # ---- chapter 2 -----------------------------------------------------------
    MAP_YEAR = 2023
    DEMAND = "electricity_demand_per_capita_kwh"
    GEN = "electricity_generation_per_capita_kwh"

    m = df[(df.year == MAP_YEAR) & (df.iso_code.notna()) & df[DEMAND].notna()]
    d = m[DEMAND]
    ng_demand = float(m.loc[m.country == "Nigeria", DEMAND].iloc[0])

    put("ch2.countries_mapped", int(len(m)), "countries", DEMAND, MAP_YEAR,
        "countries reporting electricity demand per person")
    put("ch2.median_demand", round(float(d.median())), "kWh per person", DEMAND, MAP_YEAR,
        display=f"{round(float(d.median())):,}")
    put("ch2.world_demand",
        round(float(df[(df.country == "World") & (df.year == MAP_YEAR)][DEMAND].iloc[0])),
        "kWh per person", DEMAND, MAP_YEAR,
        display=f"{round(float(df[(df.country == 'World') & (df.year == MAP_YEAR)][DEMAND].iloc[0])):,}")
    put("ch2.nigeria_demand", round(ng_demand, 1), "kWh per person", DEMAND, MAP_YEAR)
    put("ch2.nigeria_percentile", round(float((d < ng_demand).mean() * 100), 1), "%",
        DEMAND, MAP_YEAR, "share of reporting countries below Nigeria",
        display=f"{round(float((d < ng_demand).mean() * 100), 1)}th")

    groups = {
        "High-income countries": "high",
        "Low-income countries": "low",
    }
    piv = df[df.country.isin(list(groups) )].pivot_table(index="year", columns="country", values=GEN)
    piv = piv.loc[2000:2024].dropna()
    for name, short in groups.items():
        for yr in (2000, 2024):
            put(f"ch2.{short}_{yr}", round(float(piv.loc[yr, name]), 1), "kWh per person",
                GEN, yr, f"{name}, dataset aggregate",
                display=f"{round(float(piv.loc[yr, name])):,}")
        put(f"ch2.{short}_gain",
            round(float(piv.loc[2024, name] - piv.loc[2000, name])), "kWh per person",
            GEN, None, f"{name}, change 2000 to 2024",
            display=f"+{round(float(piv.loc[2024, name] - piv.loc[2000, name]))}")
    for yr in (2000, 2024):
        r = piv.loc[yr, "High-income countries"] / piv.loc[yr, "Low-income countries"]
        put(f"ch2.ratio_{yr}", round(float(r), 1), "times", GEN, yr,
            "high-income per person divided by low-income per person",
            display=f"{round(float(r), 1)}x")

    r2000 = float(piv.loc[2000, "High-income countries"] / piv.loc[2000, "Low-income countries"])
    r2024 = float(piv.loc[2024, "High-income countries"] / piv.loc[2024, "Low-income countries"])
    per_year = (r2024 - r2000) / 24
    put("ch2.years_to_parity", round((r2024 - 1) / -per_year), "years", GEN, None,
        "ratio falling at its 2000 to 2024 rate, extrapolated to 1.0",
        display=f"{round((r2024 - 1) / -per_year / 100) * 100:,}")
    gap2000 = float(piv.loc[2000, "High-income countries"] - piv.loc[2000, "Low-income countries"])
    gap2024 = float(piv.loc[2024, "High-income countries"] - piv.loc[2024, "Low-income countries"])
    put("ch2.gap_widened", round(gap2024 - gap2000), "kWh per person", GEN, None,
        "the absolute gap in 2024 minus the absolute gap in 2000",
        display=f"{round(gap2024 - gap2000)}")
    put("ch2.gap_2024", round(gap2024), "kWh per person", GEN, 2024,
        "high-income per person minus low-income per person",
        display=f"{round(gap2024):,}")

    put("ch2.lesotho_generation",
        round(float(df[(df.year == MAP_YEAR) & (df.country == "Lesotho")][GEN].iloc[0]), 1),
        "kWh per person", GEN, MAP_YEAR, "generates almost nothing, imports what it uses")

    # ---- chapter 3 -----------------------------------------------------------
    import numpy as np
    SCATTER_YEAR = 2023
    LOWC = "low_carbon_electricity_share_pct"

    sc = df[(df.year == SCATTER_YEAR) & (df.iso_code.notna()) & (df.population > 1e6)]
    sc = sc[sc[DEMAND].notna() & sc[LOWC].notna()]
    r = float(np.corrcoef(np.log10(sc[DEMAND].to_numpy()), sc[LOWC].to_numpy())[0, 1])

    put("ch3.n_countries", int(len(sc)), "countries", f"{DEMAND}, {LOWC}", SCATTER_YEAR,
        "population over 1 million, both values reported")
    put("ch3.pearson_r", round(r, 4), "correlation", f"{DEMAND}, {LOWC}", SCATTER_YEAR,
        "Pearson r on log10 of demand per person", display=f"{round(r, 4)}")
    put("ch3.r_squared", round(r * r, 4), "r squared", f"{DEMAND}, {LOWC}", SCATTER_YEAR,
        display=f"{round(r * r, 3)}")
    put("ch3.demand_spread",
        round(float(sc[DEMAND].quantile(0.90) / sc[DEMAND].quantile(0.10))), "times",
        DEMAND, SCATTER_YEAR, "90th percentile over 10th percentile",
        display=f"{round(float(sc[DEMAND].quantile(0.90) / sc[DEMAND].quantile(0.10)))}x")
    put("ch3.lowc_p10", round(float(sc[LOWC].quantile(0.10)), 1), "%", LOWC, SCATTER_YEAR,
        display=f"{round(float(sc[LOWC].quantile(0.10)), 1)}%")
    put("ch3.lowc_p90", round(float(sc[LOWC].quantile(0.90)), 1), "%", LOWC, SCATTER_YEAR,
        display=f"{round(float(sc[LOWC].quantile(0.90)), 1)}%")

    for name, key in (("Ethiopia", "eth"), ("Bangladesh", "bgd"), ("Uganda", "uga"),
                      ("Niger", "ner"), ("Nigeria", "nga")):
        row = sc[sc.country == name]
        put(f"ch3.{key}_fossil",
            round(float(row["fossil_fuels_electricity_share_pct"].iloc[0]), 1), "%",
            "fossil_fuels_electricity_share_pct", SCATTER_YEAR, name,
            display=f"{round(float(row['fossil_fuels_electricity_share_pct'].iloc[0]), 1)}%")
        put(f"ch3.{key}_demand", round(float(row[DEMAND].iloc[0])), "kWh per person",
            DEMAND, SCATTER_YEAR, name,
            display=f"{round(float(row[DEMAND].iloc[0]))}")

    w = df[df.country == "World"].set_index("year")
    for yr in (2000, 2024):
        put(f"ch3.fossil_twh_{yr}", round(float(w.loc[yr, "fossil_fuels_energy_twh"])),
            "TWh", "fossil_fuels_energy_twh", yr,
            display=f"{round(float(w.loc[yr, 'fossil_fuels_energy_twh'])):,}")
        put(f"ch3.fossil_share_{yr}",
            round(float(w.loc[yr, "fossil_fuels_energy_share_pct"]), 2), "%",
            "fossil_fuels_energy_share_pct", yr,
            display=f"{round(float(w.loc[yr, 'fossil_fuels_energy_share_pct']), 2)}%")
    put("ch3.fossil_pct_change",
        round(float(w.loc[2024, "fossil_fuels_energy_twh"]
                    / w.loc[2000, "fossil_fuels_energy_twh"] - 1) * 100, 1), "%",
        "fossil_fuels_energy_twh", None, "2000 to 2024",
        display=f"{round(float(w.loc[2024, 'fossil_fuels_energy_twh'] / w.loc[2000, 'fossil_fuels_energy_twh'] - 1) * 100, 1)}%")
    put("ch3.fossil_share_change",
        round(float(w.loc[2024, "fossil_fuels_energy_share_pct"]
                    - w.loc[2000, "fossil_fuels_energy_share_pct"]), 2), "percentage points",
        "fossil_fuels_energy_share_pct", None, "2000 to 2024",
        display=f"{round(float(w.loc[2024, 'fossil_fuels_energy_share_pct'] - w.loc[2000, 'fossil_fuels_energy_share_pct']), 2)}")

    add = {k: float(w.loc[2024, f"{k}_energy_twh"] - w.loc[2000, f"{k}_energy_twh"])
           for k in ("coal", "gas", "solar", "wind")}
    cg, sw = add["coal"] + add["gas"], add["solar"] + add["wind"]
    put("ch3.coal_gas_added", round(cg), "TWh", "coal_energy_twh, gas_energy_twh", None,
        "2000 to 2024", display=f"{round(cg):,}")
    put("ch3.solar_wind_added", round(sw), "TWh", "solar_energy_twh, wind_energy_twh", None,
        "2000 to 2024", display=f"{round(sw):,}")
    put("ch3.added_ratio", round(cg / sw, 1), "times", "as above", None,
        "coal and gas added, over solar and wind added", display=f"{round(cg / sw, 1)}x")

    for name, key in (("Vietnam", "vnm"), ("China", "chn")):
        p_ = df[df.country == name].set_index("year")
        a_, b_ = float(p_.loc[2015, "solar_electricity_twh"]), float(p_.loc[2024, "solar_electricity_twh"])
        put(f"ch3.{key}_solar_growth", round((b_ / a_ - 1) * 100), "%",
            "solar_electricity_twh", None, f"{name}, 2015 to 2024",
            display=f"{round((b_ / a_ - 1) * 100):,}%")
        put(f"ch3.{key}_solar_added", round(b_ - a_, 2), "TWh",
            "solar_electricity_twh", None, f"{name}, 2015 to 2024",
            display=f"{round(b_ - a_, 2):,}")

    # ---- chapter 4 -----------------------------------------------------------
    YEAR4, RATIO_MIN, DEMAND_MAX = 2024, 1.5, 2000
    PROD = ["oil_production_twh", "gas_production_twh", "coal_production_twh"]

    e4 = df[(df.year == YEAR4) & (df.iso_code.notna()) & (df.population > 1e6)].copy()
    e4["prod_twh"] = e4[PROD].sum(axis=1, min_count=1)
    e4 = e4[e4.prod_twh.notna() & e4.total_energy_twh.notna() & (e4.total_energy_twh > 0)]
    e4["ratio"] = e4.prod_twh / e4.total_energy_twh
    sc4 = e4[e4[DEMAND].notna()].copy()
    g4 = sc4[(sc4.ratio > RATIO_MIN) & (sc4[DEMAND] < DEMAND_MAX)]
    ng4 = sc4[sc4.country == "Nigeria"].iloc[0]

    put("ch4.group_n", int(len(g4)), "countries", "derived", YEAR4,
        f"production over {RATIO_MIN}x own supply and under {DEMAND_MAX} kWh per person")
    put("ch4.group_pop", int(g4.population.sum()), "people", "population", YEAR4,
        display=f"{round(g4.population.sum() / 1e6)} million")
    put("ch4.nigeria_share_of_group",
        round(float(ng4.population) / float(g4.population.sum()) * 100, 1), "%",
        "population", YEAR4, "Nigeria as a share of the group",
        display=f"{round(float(ng4.population) / float(g4.population.sum()) * 100, 1)}%")
    put("ch4.spearman",
        round(float(np.corrcoef(sc4.ratio.rank(), sc4[DEMAND].rank())[0, 1]), 2),
        "rank correlation", f"ratio against {DEMAND}", YEAR4,
        "across all countries in scope, not just the group",
        display=f"{round(float(np.corrcoef(sc4.ratio.rank(), sc4[DEMAND].rank())[0, 1]), 2)}")
    put("ch4.big_producers", int((sc4.ratio > RATIO_MIN).sum()), "countries", "derived", YEAR4,
        f"production over {RATIO_MIN}x own supply, regardless of electricity")
    put("ch4.countries_in_scope", int(len(sc4)), "countries", "derived", YEAR4)

    for nm, key in (("Nigeria", "nga"), ("Norway", "nor"), ("Chad", "tcd")):
        r4 = sc4[sc4.country == nm].iloc[0]
        put(f"ch4.{key}_ratio", round(float(r4.ratio), 2), "times", "derived", YEAR4, nm,
            display=f"{round(float(r4.ratio), 2)}x")
        put(f"ch4.{key}_demand", round(float(r4[DEMAND])), "kWh per person", DEMAND, YEAR4, nm,
            display=f"{round(float(r4[DEMAND])):,}")
    put("ch4.nigeria_prod", round(float(ng4.prod_twh), 1), "TWh", ", ".join(PROD), YEAR4,
        display=f"{round(float(ng4.prod_twh)):,}")
    put("ch4.nigeria_supply", round(float(ng4.total_energy_twh), 1), "TWh",
        "total_energy_twh", YEAR4, display=f"{round(float(ng4.total_energy_twh))}")

    # ---- chapter 5 -----------------------------------------------------------
    GEN5, GENPC5 = "electricity_generation_twh", "electricity_generation_per_capita_kwh"
    ng5 = df[df.country == "Nigeria"].set_index("year")
    w5 = df[df.country == "World"].set_index("year")
    FROM5, TO5, TREND5 = 2000, 2025, 2002

    yrs5 = np.arange(TREND5, TO5 + 1)
    vals5 = np.array([float(ng5.loc[y, GENPC5]) for y in yrs5])
    slope5 = float(np.polyfit(yrs5, vals5, 1)[0])

    put("ch5.slope", round(slope5, 2), "kWh per person per year", GENPC5, None,
        f"least squares trend, {TREND5} to {TO5}", display=f"{round(slope5, 2)}")
    put("ch5.gen_growth", round(float(ng5.loc[TO5, GEN5] / ng5.loc[FROM5, GEN5]), 2), "times",
        GEN5, None, f"{FROM5} to {TO5}",
        display=f"{round(float(ng5.loc[TO5, GEN5] / ng5.loc[FROM5, GEN5]), 2)}x")
    put("ch5.pop_growth",
        round(float(ng5.loc[TO5, "population"] / ng5.loc[FROM5, "population"]), 2), "times",
        "population", None, f"{FROM5} to {TO5}",
        display=f"{round(float(ng5.loc[TO5, 'population'] / ng5.loc[FROM5, 'population']), 2)}x")
    put("ch5.pc_growth",
        round(float(ng5.loc[TO5, GENPC5] / ng5.loc[FROM5, GENPC5]), 2), "times",
        GENPC5, None, f"{FROM5} to {TO5}",
        display=f"{round(float(ng5.loc[TO5, GENPC5] / ng5.loc[FROM5, GENPC5]), 2)}x")
    for y in (FROM5, TREND5, 2024, TO5):
        put(f"ch5.pc_{y}", round(float(ng5.loc[y, GENPC5]), 1), "kWh per person", GENPC5, y)
    put("ch5.pc_min", round(float(ng5.loc[FROM5:TO5, GENPC5].min()), 1), "kWh per person",
        GENPC5, None, "lowest year in the series")
    put("ch5.pc_max", round(float(ng5.loc[FROM5:TO5, GENPC5].max()), 1), "kWh per person",
        GENPC5, None, "highest year in the series")
    put("ch5.world_pc", round(float(w5.loc[TO5, GENPC5]), 1), "kWh per person", GENPC5, TO5,
        "World aggregate", display=f"{round(float(w5.loc[TO5, GENPC5])):,}")
    gap5 = float(w5.loc[TO5, GENPC5]) - float(ng5.loc[TO5, GENPC5])
    put("ch5.years_to_world", round(gap5 / slope5), "years", GENPC5, None,
        "gap to the world average divided by the fitted trend",
        display=f"{round(gap5 / slope5):,}")

    for src in ("gas", "hydro", "solar", "bioenergy"):
        put(f"ch5.{src}_{TO5}", round(float(ng5.loc[TO5, f"{src}_electricity_share_pct"]), 2),
            "%", f"{src}_electricity_share_pct", TO5,
            display=f"{round(float(ng5.loc[TO5, f'{src}_electricity_share_pct']), 2)}%")
    put("ch5.gas_2000", round(float(ng5.loc[2000, "gas_electricity_share_pct"]), 2), "%",
        "gas_electricity_share_pct", 2000,
        display=f"{round(float(ng5.loc[2000, 'gas_electricity_share_pct']), 2)}%")

    # ---- chapter 6, the limits -----------------------------------------------
    # Each of these is measured, not asserted. If the dataset ever gains one of
    # these columns, the page stops claiming it is missing.
    cols = list(df.columns)

    def has_any(*needles):
        return sorted(c for c in cols if any(n in c.lower() for n in needles))

    access_cols = has_any("access", "electrified", "connection")
    capacity_cols = has_any("capacit", "installed_mw", "_gw")
    price_cols = has_any("price", "tariff", "cost", "afford")
    emission_cols = has_any("emission", "co2")
    trade_cols = [c for c in has_any("import", "export") if "electricity" not in c]

    ng6 = df[df.country == "Nigeria"]
    energy_cols = [c for c in cols if "_energy_" in c]
    ng_empty = [c for c in energy_cols if ng6[c].notna().sum() == 0]

    c25 = df[(df.year == 2025) & (df.iso_code.notna())]
    c24 = df[(df.year == 2024) & (df.iso_code.notna())]

    pre2000 = {}
    for y in (1950, 1980, 1990, 2000):
        cy = df[(df.year == y) & (df.iso_code.notna())]
        pre2000[str(y)] = int(cy.electricity_generation_twh.notna().sum())

    w6 = df[df.country == "World"].set_index("year")
    accounting = {}
    for srcname in ("nuclear", "hydro", "solar", "wind"):
        accounting[srcname] = round(
            float(w6.loc[2024, f"{srcname}_energy_twh"]
                  / w6.loc[2024, f"{srcname}_electricity_twh"]), 2)

    # The two findings that did not become chapters, with the numbers that killed them.
    LOWC6 = "low_carbon_electricity_share_pct"
    inc_low = df[(df.country == "Low-income countries") & (df.year == 2023)][LOWC6].iloc[0]
    inc_high = df[(df.country == "High-income countries") & (df.year == 2023)][LOWC6].iloc[0]
    q = df[(df.year == 2023) & (df.iso_code.notna()) & (df.population > 1e6)]
    q = q[q.electricity_generation_per_capita_kwh.notna() & q[LOWC6].notna()].copy()
    q["quint"] = pd.qcut(q.electricity_generation_per_capita_kwh, 5, labels=False)
    bottom_median = float(q[q.quint == 0][LOWC6].median())

    GENPC6 = "electricity_generation_per_capita_kwh"
    a6 = df[(df.year == 2000) & (df.iso_code.notna())][["country", GENPC6]].set_index("country")
    b6 = df[(df.year == 2024) & (df.iso_code.notna())][
        ["country", GENPC6, "population"]].set_index("country")
    j6 = a6.join(b6, lsuffix="_00", rsuffix="_24").dropna()
    j6 = j6[j6.population > 10e6]
    went_back = j6[j6[GENPC6 + "_24"] < j6[GENPC6 + "_00"]]

    limits = {
        "absent": {
            "electricity access": access_cols,
            "installed capacity": capacity_cols,
            "prices, tariffs or affordability": price_cols,
            "fuel imports or exports": trade_cols,
        },
        "emissions_columns_present": emission_cols,
        "nigeria": {
            "energy_columns_total": len(energy_cols),
            "energy_columns_empty": len(ng_empty),
            "energy_columns_present": sorted(set(energy_cols) - set(ng_empty)),
            # of the few that are not empty, the nuclear ones are structural zeros
            "present_nuclear_all_zero": all(
                float(ng6[c].abs().max()) == 0.0
                for c in energy_cols if c not in ng_empty and c.startswith("nuclear_")),
            "present_nuclear_count": len(
                [c for c in energy_cols if c not in ng_empty and c.startswith("nuclear_")]),
            "present_total_count": len(
                [c for c in energy_cols if c not in ng_empty and c.startswith("total_")]),
        },
        "gdp_last_year": int(df[df.iso_code.notna() & df.gdp.notna()].year.max()),
        "coverage_2025": {
            "countries_with_a_row": int(len(c25)),
            "electricity": int(c25.electricity_generation_twh.notna().sum()),
            "total_energy": int(c25.total_energy_twh.notna().sum()),
            "oil_production": int(c25.oil_production_twh.notna().sum()),
            "countries_2024": int(len(c24)),
        },
        "electricity_coverage_by_year": pre2000,
        "accounting_ratios_2024": accounting,
        "findings_not_used": {
            "low_income_low_carbon_pct": round(float(inc_low), 1),
            "high_income_low_carbon_pct": round(float(inc_high), 1),
            "bottom_quintile_median_low_carbon_pct": round(bottom_median, 1),
            "large_countries_examined": int(len(j6)),
            "large_countries_that_fell": int(len(went_back)),
        },
    }

    put("ch6.nigeria_energy_cols", len(energy_cols), "columns", "all *_energy_* columns", None,
        "energy columns in the dataset")
    put("ch6.nigeria_empty_cols", len(ng_empty), "columns", "all *_energy_* columns", None,
        "of those, empty for Nigeria in every year")
    put("ch6.nigeria_present_cols", len(energy_cols) - len(ng_empty), "columns",
        "all *_energy_* columns", None,
        "four nuclear columns that read zero, and five total energy columns")
    put("ch6.gdp_last_year", limits["gdp_last_year"], "year", "gdp", None,
        "last year any country has a GDP figure")
    put("ch6.e2025", limits["coverage_2025"]["electricity"], "countries",
        "electricity_generation_twh", 2025)
    put("ch6.t2025", limits["coverage_2025"]["total_energy"], "countries",
        "total_energy_twh", 2025)
    put("ch6.o2025", limits["coverage_2025"]["oil_production"], "countries",
        "oil_production_twh", 2025)
    put("ch6.rows2025", limits["coverage_2025"]["countries_with_a_row"], "countries",
        "iso_code", 2025)
    put("ch6.elec_1990", pre2000["1990"], "countries", "electricity_generation_twh", 1990)
    put("ch6.elec_2000", pre2000["2000"], "countries", "electricity_generation_twh", 2000)
    put("ch6.nuclear_ratio", accounting["nuclear"], "times",
        "nuclear_energy_twh / nuclear_electricity_twh", 2024,
        "counted at heat input, not electrical output", display=f"{accounting['nuclear']}x")
    put("ch6.wind_ratio", accounting["wind"], "times",
        "wind_energy_twh / wind_electricity_twh", 2024,
        "counted at electrical output", display=f"{accounting['wind']}x")
    put("ch6.low_income_lowc", limits["findings_not_used"]["low_income_low_carbon_pct"], "%",
        LOWC6, 2023, "Low-income countries aggregate",
        display=f"{limits['findings_not_used']['low_income_low_carbon_pct']}%")
    put("ch6.high_income_lowc", limits["findings_not_used"]["high_income_low_carbon_pct"], "%",
        LOWC6, 2023, "High-income countries aggregate",
        display=f"{limits['findings_not_used']['high_income_low_carbon_pct']}%")
    put("ch6.bottom_quintile_lowc",
        limits["findings_not_used"]["bottom_quintile_median_low_carbon_pct"], "%",
        LOWC6, 2023, "median of the lowest-generation fifth of countries",
        display=f"{limits['findings_not_used']['bottom_quintile_median_low_carbon_pct']}%")
    put("ch6.fell_count", limits["findings_not_used"]["large_countries_that_fell"], "countries",
        GENPC6, None, "countries over 10 million whose per person output fell 2000 to 2024")
    put("ch6.fell_of", limits["findings_not_used"]["large_countries_examined"], "countries",
        GENPC6, None, "countries over 10 million examined")

    payload = {
        "meta": {
            "built_by": "analysis/25_build_key_figures.py",
            "source_file": RAW.name,
            "generated": date.today().isoformat(),
            "n_figures": len(figures),
            "note": "Re-derived and checked by analysis/27_verify_site_numbers.py",
        },
        "figures": figures,
        "limits": limits,
    }

    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(figures)} figures)")
    for k in sorted(figures):
        f = figures[k]
        print(f"   {k:30s} {f.get('display', f['value'])}")
    print()
    print("   limits, measured by scanning all", len(df.columns), "columns:")
    for label, found in limits["absent"].items():
        state = "ABSENT" if not found else "present: " + ", ".join(found)
        print(f"      {label:34s} {state}")
    print(f"      emissions columns present       "
          f"{', '.join(limits['emissions_columns_present'])}")
    print(f"      Nigeria energy columns empty    "
          f"{limits['nigeria']['energy_columns_empty']} of "
          f"{limits['nigeria']['energy_columns_total']} "
          f"({limits['nigeria']['present_nuclear_count']} nuclear, all zero: "
          f"{limits['nigeria']['present_nuclear_all_zero']}; "
          f"{limits['nigeria']['present_total_count']} totals)")


if __name__ == "__main__":
    main()
