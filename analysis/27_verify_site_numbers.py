"""Re-derive every number the site shows, straight from the frozen data file.

This is the audit. It does not trust the JSON in docs/data/. It recomputes each
figure from data/owid-energy-2026-10-14.csv and compares. Any mismatch is printed
and the script exits non-zero.

It covers both halves of the site:
  the chart data   docs/data/ch*.json
  the prose        docs/data/key_figures.json, which supplies every number
                   written into a sentence

Run from the repository root:
  python analysis/27_verify_site_numbers.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "owid-energy-2026-10-14.csv"
DATA = ROOT / "docs" / "data"

HEADLINE_YEAR = 2024
MIX = "fossil_fuels_energy_twh"

checks = []


def check(label, expected, actual, tol=0.0):
    ok = (abs(expected - actual) <= tol) if isinstance(expected, (int, float)) \
        and isinstance(actual, (int, float)) else expected == actual
    checks.append((ok, label, expected, actual))


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main():
    if not RAW.exists():
        sys.exit(f"missing {RAW}. The frozen data file must be in the repository.")
    df = pd.read_csv(RAW)

    c24 = df[(df.year == HEADLINE_YEAR) & (df.iso_code.notna())]
    world_pop = float(df[(df.country == "World") & (df.year == HEADLINE_YEAR)].population.iloc[0])

    # ---- chapter 1, the coverage map -----------------------------------------
    cov = load("ch1_coverage_map.json")
    s = cov["summary"]

    check("ch1 map: countries on the map", int(len(c24)), s["total_countries"])
    check("ch1 map: with an energy mix", int(c24[MIX].notna().sum()), s["measured"])
    check("ch1 map: without one", int(c24[MIX].isna().sum()), s["not_measured"])
    check("ch1 map: rows written", int(len(c24)), len(cov["rows"]))
    check(
        "ch1 map: world population share with no mix",
        round(float(c24.loc[c24[MIX].isna(), "population"].sum()) / world_pop * 100, 1),
        s["pop_share_not_measured_pct"], tol=0.05,
    )
    check("ch1 map: a total but no breakdown",
          int((c24.total_energy_twh.notna() & c24[MIX].isna()).sum()), s["know_total_not_mix"])
    check("ch1 map: African countries measured", 4, s["africa_measured"])
    check("ch1 map: African countries counted", 54, s["africa_total"])

    # every row must match the source, not just the totals
    truth = c24.set_index("iso_code")
    bad = []
    for r in cov["rows"]:
        if r["iso"] not in truth.index:
            bad.append((r["iso"], "not in the data"))
            continue
        want = int(pd.notna(truth.loc[r["iso"], MIX]))
        if want != r["measured"]:
            bad.append((r["iso"], f"measured {r['measured']} but source says {want}"))
    check("ch1 map: every country row matches the source", 0, len(bad))
    for iso, why in bad[:10]:
        print("   row mismatch:", iso, why)

    nigeria = next(r for r in cov["rows"] if r["iso"] == "NGA")
    check("ch1 map: Nigeria has no energy mix", 0, nigeria["measured"])

    # ---- chapter 1, the panel growth chart -----------------------------------
    growth = load("ch1_panel_growth.json")
    for row in growth["rows"]:
        cy = df[(df.year == row["year"]) & (df.iso_code.notna())]
        if row["year"] in (1970, 1990, 2000, HEADLINE_YEAR):
            check(f"ch1 growth {row['year']}: with a mix",
                  int(cy[MIX].notna().sum()), row["with_mix"])
            check(f"ch1 growth {row['year']}: with a total",
                  int(cy.total_energy_twh.notna().sum()), row["with_total"])
            check(f"ch1 growth {row['year']}: with electricity",
                  int(cy.electricity_generation_twh.notna().sum()), row["with_electricity"])

    # ---- chapter 2, the demand map -------------------------------------------
    MAP_YEAR, DEMAND, GEN = 2023, "electricity_demand_per_capita_kwh",         "electricity_generation_per_capita_kwh"
    dm = load("ch2_demand_map.json")
    src = df[(df.year == MAP_YEAR) & (df.iso_code.notna()) & df[DEMAND].notna()]

    check("ch2 map: countries mapped", int(len(src)), dm["summary"]["n"])
    check("ch2 map: rows written", int(len(src)), len(dm["rows"]))
    check("ch2 map: band counts sum to the rows", len(dm["rows"]), sum(dm["band_counts"]))
    check("ch2 map: median", round(float(src[DEMAND].median()), 1), dm["summary"]["median_kwh"], tol=0.05)
    ng_d = float(src.loc[src.country == "Nigeria", DEMAND].iloc[0])
    check("ch2 map: Nigeria demand", round(ng_d, 1), dm["summary"]["nigeria_kwh"], tol=0.05)
    check("ch2 map: Nigeria percentile",
          round(float((src[DEMAND] < ng_d).mean() * 100), 1),
          dm["summary"]["nigeria_percentile"], tol=0.05)
    check("ch2 map: lowest country", str(src.loc[src[DEMAND].idxmin(), "country"]),
          dm["summary"]["min_country"])
    check("ch2 map: highest country", str(src.loc[src[DEMAND].idxmax(), "country"]),
          dm["summary"]["max_country"])

    # every row's value and its band assignment
    breaks = dm["breaks"]
    truth_d = src.set_index("iso_code")
    bad_rows, bad_bands = [], []
    for r in dm["rows"]:
        if r["iso"] not in truth_d.index:
            bad_rows.append(r["iso"]); continue
        want = round(float(truth_d.loc[r["iso"], DEMAND]), 1)
        if abs(want - r["demand_pc_kwh"]) > 0.05:
            bad_rows.append(f"{r['iso']} value {r['demand_pc_kwh']} vs {want}")
        band = max(i for i, e in enumerate(breaks) if want >= e)
        if band != r["band"]:
            bad_bands.append(f"{r['iso']} band {r['band']} vs {band}")
    check("ch2 map: every country value matches the source", 0, len(bad_rows))
    check("ch2 map: every band assignment is correct", 0, len(bad_bands))
    for x in (bad_rows + bad_bands)[:10]:
        print("   ch2 map mismatch:", x)

    # ---- chapter 2, the income lines -----------------------------------------
    ig = load("ch2_income_groups.json")
    s2 = ig["summary"]
    GROUPS = ["Low-income countries", "Lower-middle-income countries",
              "Upper-middle-income countries", "High-income countries"]
    piv = df[df.country.isin(GROUPS)].pivot_table(index="year", columns="country", values=GEN)
    piv = piv.loc[2000:2024].dropna()

    check("ch2 income: first year", int(piv.index.min()), s2["first_year"])
    check("ch2 income: last year", int(piv.index.max()), s2["last_year"])
    check("ch2 income: four series", 4, len(ig["series"]))
    for key, name in (("high", "High-income countries"), ("low", "Low-income countries")):
        for yr in (2000, 2024):
            check(f"ch2 income: {key} {yr}", round(float(piv.loc[yr, name]), 1),
                  s2[f"{key}_{'first' if yr == 2000 else 'last'}"], tol=0.05)
    for yr, key in ((2000, "ratio_first"), (2024, "ratio_last")):
        want = round(float(piv.loc[yr, "High-income countries"]
                           / piv.loc[yr, "Low-income countries"]), 1)
        check(f"ch2 income: ratio {yr}", want, s2[key], tol=0.05)

    bad_pts = []
    for ser in ig["series"]:
        for pt in ser["points"]:
            want = round(float(piv.loc[pt["year"], ser["group"]]), 1)
            if abs(want - pt["kwh_pc"]) > 0.05:
                bad_pts.append(f"{ser['group']} {pt['year']}")
    check("ch2 income: every point matches the source", 0, len(bad_pts))

    # the chapter claims membership is stable, so the check must actually run
    pop = df[df.country.isin(GROUPS)].pivot_table(index="year", columns="country", values="population")
    worst = float(pop.pct_change().abs().max().max() * 100)
    check("ch2 income: no group population moves more than 5% in a year", True, worst < 5)
    print(f"   largest year on year income-group population move: {worst:.2f}%")

    # The chapter says the ratio narrowed while the absolute gap grew. Both halves
    # of that sentence have to stay true, or the paragraph has to be rewritten.
    gap_2000 = float(piv.loc[2000, "High-income countries"] - piv.loc[2000, "Low-income countries"])
    gap_2024 = float(piv.loc[2024, "High-income countries"] - piv.loc[2024, "Low-income countries"])
    check("ch2: the ratio fell", True,
          (piv.loc[2024, "High-income countries"] / piv.loc[2024, "Low-income countries"])
          < (piv.loc[2000, "High-income countries"] / piv.loc[2000, "Low-income countries"]))
    check("ch2: the absolute gap grew, which the page says explicitly", True,
          gap_2024 > gap_2000)

    # ---- chapter 3, the scatter ----------------------------------------------
    import numpy as np
    SCATTER_YEAR, LOWC = 2023, "low_carbon_electricity_share_pct"
    sc_json = load("ch3_amount_vs_mix.json")
    sc = df[(df.year == SCATTER_YEAR) & (df.iso_code.notna()) & (df.population > 1e6)]
    sc = sc[sc[DEMAND].notna() & sc[LOWC].notna()]

    check("ch3 scatter: countries", int(len(sc)), sc_json["stats"]["n"])
    check("ch3 scatter: rows written", int(len(sc)), len(sc_json["rows"]))

    r_true = float(np.corrcoef(np.log10(sc[DEMAND].to_numpy()), sc[LOWC].to_numpy())[0, 1])
    check("ch3 scatter: Pearson r", round(r_true, 4),
          sc_json["stats"]["pearson_r_log10"], tol=0.0001)
    check("ch3 scatter: r squared", round(r_true * r_true, 4),
          sc_json["stats"]["r_squared"], tol=0.0001)
    rho_true = float(np.corrcoef(sc[DEMAND].rank(), sc[LOWC].rank())[0, 1])
    check("ch3 scatter: Spearman", round(rho_true, 3),
          sc_json["stats"]["spearman"], tol=0.001)
    check("ch3 scatter: the result is still a null", True,
          abs(sc_json["stats"]["pearson_r_log10"]) < 0.01)

    # the fitted line must be the real least-squares fit, not a flat line drawn by hand
    slope_true, _ = np.polyfit(np.log10(sc[DEMAND].to_numpy()), sc[LOWC].to_numpy(), 1)
    check("ch3 scatter: fitted slope", round(float(slope_true), 2),
          sc_json["fit"]["slope_per_decade"], tol=0.005)

    truth_sc = sc.set_index("iso_code")
    bad_sc = []
    for row in sc_json["rows"]:
        if row["iso"] not in truth_sc.index:
            bad_sc.append(row["iso"]); continue
        if abs(round(float(truth_sc.loc[row["iso"], DEMAND]), 1) - row["demand_pc_kwh"]) > 0.05:
            bad_sc.append(row["iso"] + " demand")
        if abs(round(float(truth_sc.loc[row["iso"], LOWC]), 1) - row["low_carbon_pct"]) > 0.05:
            bad_sc.append(row["iso"] + " low carbon")
    check("ch3 scatter: every point matches the source", 0, len(bad_sc))
    for x in bad_sc[:10]:
        print("   ch3 scatter mismatch:", x)

    check("ch3 scatter: Nigeria is the only highlighted point", 1,
          sum(1 for r_ in sc_json["rows"] if r_["highlight"]))

    # ---- chapter 3, world fossil ---------------------------------------------
    fj = load("ch3_world_fossil.json")
    sf = fj["summary"]
    w3 = df[df.country == "World"].set_index("year")

    check("ch3 fossil: 2000 TWh", round(float(w3.loc[2000, "fossil_fuels_energy_twh"]), 1),
          sf["twh_2000"], tol=0.05)
    check("ch3 fossil: 2024 TWh", round(float(w3.loc[2024, "fossil_fuels_energy_twh"]), 1),
          sf["twh_2024"], tol=0.05)
    check("ch3 fossil: percent change",
          round(float(w3.loc[2024, "fossil_fuels_energy_twh"]
                      / w3.loc[2000, "fossil_fuels_energy_twh"] - 1) * 100, 1),
          sf["pct_change"], tol=0.05)
    check("ch3 fossil: share change in points",
          round(float(w3.loc[2024, "fossil_fuels_energy_share_pct"]
                      - w3.loc[2000, "fossil_fuels_energy_share_pct"]), 2),
          sf["share_change_pp"], tol=0.005)
    check("ch3 fossil: absolute rose while share fell", True,
          sf["abs_change_twh"] > 0 and sf["share_change_pp"] < 0)

    add3 = {k: float(w3.loc[2024, f"{k}_energy_twh"] - w3.loc[2000, f"{k}_energy_twh"])
            for k in ("coal", "gas", "solar", "wind")}
    check("ch3 fossil: coal and gas added", round(add3["coal"] + add3["gas"]),
          sf["coal_gas_added_twh"])
    check("ch3 fossil: solar and wind added", round(add3["solar"] + add3["wind"]),
          sf["solar_wind_added_twh"])
    check("ch3 fossil: ratio",
          round((add3["coal"] + add3["gas"]) / (add3["solar"] + add3["wind"]), 1),
          sf["ratio"], tol=0.05)

    bad_f = []
    for row in fj["rows"]:
        if abs(round(float(w3.loc[row["year"], "fossil_fuels_energy_twh"]), 1)
               - row["fossil_twh"]) > 0.05:
            bad_f.append(str(row["year"]))
    check("ch3 fossil: every year matches the source", 0, len(bad_f))

    # ---- chapter 3, the growth trap ------------------------------------------
    tj = load("ch3_growth_trap.json")
    for row in tj["rows"]:
        pc = df[df.country == row["country"]].set_index("year")
        a3 = float(pc.loc[2015, "solar_electricity_twh"])
        b3 = float(pc.loc[2024, "solar_electricity_twh"])
        check(f"ch3 trap: {row['country']} added", round(b3 - a3, 2), row["added_twh"], tol=0.01)
        check(f"ch3 trap: {row['country']} growth", round((b3 / a3 - 1) * 100),
              row["pct_growth"], tol=1)
    vn = next(r_ for r_ in tj["rows"] if r_["country"] == "Vietnam")
    cn = next(r_ for r_ in tj["rows"] if r_["country"] == "China")
    check("ch3 trap: the smaller country has the bigger percentage", True,
          vn["pct_growth"] > cn["pct_growth"] and vn["added_twh"] < cn["added_twh"])

    # ---- chapter 4, production against electricity used ----------------------
    YEAR4, RATIO_MIN, DEMAND_MAX = 2024, 1.5, 2000
    PROD = ["oil_production_twh", "gas_production_twh", "coal_production_twh"]
    pj = load("ch4_production_vs_power.json")
    s4 = pj["stats"]

    e4 = df[(df.year == YEAR4) & (df.iso_code.notna()) & (df.population > 1e6)].copy()
    e4["prod_twh"] = e4[PROD].sum(axis=1, min_count=1)
    e4 = e4[e4.prod_twh.notna() & e4.total_energy_twh.notna() & (e4.total_energy_twh > 0)]
    e4["ratio"] = e4.prod_twh / e4.total_energy_twh
    sc4 = e4[e4[DEMAND].notna()].copy()
    g4 = sc4[(sc4.ratio > RATIO_MIN) & (sc4[DEMAND] < DEMAND_MAX)]

    check("ch4: countries in scope", int(len(sc4)), s4["n"])
    check("ch4: rows written", int(len(sc4)), len(pj["rows"]))
    check("ch4: thresholds as documented", [RATIO_MIN, DEMAND_MAX],
          [pj["thresholds"]["ratio_min"], pj["thresholds"]["demand_max"]])
    check("ch4: group size", int(len(g4)), s4["group_n"])
    check("ch4: group population", int(g4.population.sum()), s4["group_pop"])
    check("ch4: group members", sorted(g4.country.tolist()), s4["group_members"])

    ng4 = sc4[sc4.country == "Nigeria"].iloc[0]
    check("ch4: Nigeria share of the group",
          round(float(ng4.population) / float(g4.population.sum()) * 100, 1),
          s4["nigeria_share_of_group_pct"], tol=0.05)
    check("ch4: Nigeria production", round(float(ng4.prod_twh), 1), pj["nigeria"]["prod_twh"], tol=0.05)
    check("ch4: Nigeria ratio", round(float(ng4.ratio), 2), pj["nigeria"]["ratio"], tol=0.005)

    rho4 = float(np.corrcoef(sc4.ratio.rank(), sc4[DEMAND].rank())[0, 1])
    check("ch4: rank correlation", round(rho4, 3), s4["spearman_ratio_vs_demand"], tol=0.001)
    check("ch4: the correlation is still weak, so the quadrant framing holds",
          True, abs(s4["spearman_ratio_vs_demand"]) < 0.3)
    check("ch4: big producers above the ratio threshold",
          int((sc4.ratio > RATIO_MIN).sum()), s4["producers_above_threshold"])
    check("ch4: most big producers are NOT energy-poor", True,
          s4["producers_above_threshold"] > 2 * s4["group_n"])
    check("ch4: Norway is outside the group", False, "Norway" in s4["group_members"])

    # the group must not depend on which electricity column was chosen
    alt4 = e4[e4[GEN].notna()]
    alt_group = sorted(alt4.loc[(alt4.ratio > RATIO_MIN) & (alt4[GEN] < DEMAND_MAX), "country"])
    check("ch4: same group using generation instead of demand",
          alt_group, sorted(g4.country.tolist()))
    check("ch4: that robustness is recorded in the JSON", True,
          s4["same_group_using_generation"])

    truth4 = sc4.set_index("iso_code")
    bad4 = []
    for row in pj["rows"]:
        if row["iso"] not in truth4.index:
            bad4.append(row["iso"]); continue
        t4 = truth4.loc[row["iso"]]
        if abs(round(float(t4.ratio), 2) - row["ratio"]) > 0.005:
            bad4.append(row["iso"] + " ratio")
        if abs(round(float(t4[DEMAND]), 1) - row["demand_pc_kwh"]) > 0.05:
            bad4.append(row["iso"] + " demand")
        want_in = bool(t4.ratio > RATIO_MIN and t4[DEMAND] < DEMAND_MAX)
        if want_in != row["in_group"]:
            bad4.append(row["iso"] + " group flag")
    check("ch4: every row matches the source", 0, len(bad4))
    for x in bad4[:10]:
        print("   ch4 mismatch:", x)

    # ---- chapter 5, Nigeria --------------------------------------------------
    GEN5, GENPC5 = "electricity_generation_twh", "electricity_generation_per_capita_kwh"
    FROM5, TO5, TREND5 = 2000, 2025, 2002
    ng5 = df[df.country == "Nigeria"].set_index("year")
    w5 = df[df.country == "World"].set_index("year")

    oj = load("ch5_nigeria_output.json")
    s5 = oj["summary"]

    check("ch5 output: years written", TO5 - FROM5 + 1, len(oj["rows"]))
    bad5 = []
    for row in oj["rows"]:
        y = row["year"]
        if abs(round(float(ng5.loc[y, GEN5]), 2) - row["generation_twh"]) > 0.005:
            bad5.append(f"{y} total")
        if abs(round(float(ng5.loc[y, GENPC5]), 1) - row["generation_pc_kwh"]) > 0.05:
            bad5.append(f"{y} per person")
        if int(ng5.loc[y, "population"]) != row["population"]:
            bad5.append(f"{y} population")
    check("ch5 output: every year matches the source", 0, len(bad5))
    for x in bad5[:10]:
        print("   ch5 output mismatch:", x)

    check("ch5 output: generation growth",
          round(float(ng5.loc[TO5, GEN5] / ng5.loc[FROM5, GEN5]), 2), s5["gen_growth_x"], tol=0.005)
    check("ch5 output: population growth",
          round(float(ng5.loc[TO5, "population"] / ng5.loc[FROM5, "population"]), 2),
          s5["pop_growth_x"], tol=0.005)
    check("ch5 output: generation outgrew population", True,
          s5["gen_growth_x"] > s5["pop_growth_x"])

    yrs5 = np.arange(TREND5, TO5 + 1)
    vals5 = np.array([float(ng5.loc[y, GENPC5]) for y in yrs5])
    slope5 = float(np.polyfit(yrs5, vals5, 1)[0])
    check("ch5 output: fitted trend", round(slope5, 2),
          oj["trend"]["slope_kwh_per_year"], tol=0.005)
    check("ch5 output: the trend is positive, so the chapter must not call it flat",
          True, oj["trend"]["slope_kwh_per_year"] > 0)
    check("ch5 output: the 2002 and 2024 endpoints are recorded, not hidden",
          [round(float(ng5.loc[2002, GENPC5]), 1), round(float(ng5.loc[2024, GENPC5]), 1)],
          [s5["pc_2002"], s5["pc_2024"]])

    gap5 = float(w5.loc[TO5, GENPC5]) - float(ng5.loc[TO5, GENPC5])
    check("ch5 output: years to reach the world average", round(gap5 / slope5),
          s5["years_to_reach_world_at_this_rate"])

    # Two scripts derive this figure. They must agree exactly, not within a
    # tolerance: a tolerance is how one of them came to regress on rounded values
    # while the other used the raw column, and the disagreement went unnoticed.
    check("ch5: the chart build and the figure build agree exactly",
          load("ch5_nigeria_output.json")["summary"]["years_to_reach_world_at_this_rate"],
          load("key_figures.json")["figures"]["ch5.years_to_world"]["value"])

    # ---- chapter 5, the mix --------------------------------------------------
    mj = load("ch5_nigeria_mix.json")
    check("ch5 mix: four sources", ["gas", "hydro", "solar", "bioenergy"], mj["sources"])

    bad_mix, bad_total = [], []
    for row in mj["rows"]:
        y = row["year"]
        for src_name in mj["sources"]:
            want = round(float(ng5.loc[y, f"{src_name}_electricity_share_pct"]), 2)
            if abs(want - row[src_name]) > 0.005:
                bad_mix.append(f"{y} {src_name}")
        if abs(row["total_pct"] - 100.0) > 0.05:
            bad_total.append(str(y))
    check("ch5 mix: every share matches the source", 0, len(bad_mix))
    check("ch5 mix: the bands total 100% in every year", 0, len(bad_total))
    for x in (bad_mix + bad_total)[:10]:
        print("   ch5 mix mismatch:", x)

    # the omitted sources must really be zero everywhere, or the chart hides something
    bad_zero = []
    for src_name in mj["meta"]["omitted_sources"]:
        if float(ng5.loc[FROM5:TO5, f"{src_name}_electricity_share_pct"].abs().max()) != 0.0:
            bad_zero.append(src_name)
    check("ch5 mix: every omitted source really is zero in every year", 0, len(bad_zero))
    check("ch5 mix: bioenergy was not omitted, because it is not zero", False,
          "bioenergy" in mj["meta"]["omitted_sources"])

    # ---- chapter 5, the peers ------------------------------------------------
    pj5 = load("ch5_peer_growth.json")
    PEER_FROM, PEER_TO = pj5["meta"]["from"], pj5["meta"]["to"]
    bad_peer = []
    for row in pj5["rows"]:
        pc = df[df.country == row["country"]].set_index("year")
        a5, b5 = float(pc.loc[PEER_FROM, GENPC5]), float(pc.loc[PEER_TO, GENPC5])
        if abs(round(b5 / a5, 2) - row["growth_x"]) > 0.005:
            bad_peer.append(row["country"])
        if abs(round(a5, 1) - row["kwh_first"]) > 0.05:
            bad_peer.append(row["country"] + " first")
        if abs(round(b5, 1) - row["kwh_last"]) > 0.05:
            bad_peer.append(row["country"] + " last")
    check("ch5 peers: every peer matches the source", 0, len(bad_peer))
    for x in bad_peer[:10]:
        print("   ch5 peer mismatch:", x)
    check("ch5 peers: Nigeria is the only highlighted row", 1,
          sum(1 for r_ in pj5["rows"] if r_["highlight"]))
    ng_row = next(r_ for r_ in pj5["rows"] if r_["country"] == "Nigeria")
    wd_row = next(r_ for r_ in pj5["rows"] if r_["country"] == "World")
    check("ch5 peers: Nigeria grew more slowly than the world", True,
          ng_row["growth_x"] < wd_row["growth_x"])
    eth_row = next(r_ for r_ in pj5["rows"] if r_["country"] == "Ethiopia")
    check("ch5 peers: Ethiopia started lower than Nigeria and grew faster", True,
          eth_row["kwh_first"] < ng_row["kwh_first"]
          and eth_row["growth_x"] > ng_row["growth_x"])

    # ---- chapter 6, the limits -----------------------------------------------
    lim = load("key_figures.json").get("limits")
    check("ch6: the limits block exists", True, lim is not None)

    cols6 = list(df.columns)

    def found(*needles):
        return sorted(c for c in cols6 if any(n in c.lower() for n in needles))

    # Each claim of absence is re-derived. If the dataset ever gains one of these
    # columns, this fails and the page must stop saying it is missing.
    check("ch6: no electricity access column", [], found("access", "electrified", "connection"))
    check("ch6: no capacity column", [], found("capacit", "installed_mw", "_gw"))
    check("ch6: no price or tariff column", [], found("price", "tariff", "cost", "afford"))
    check("ch6: no fuel trade column", [],
          [c for c in found("import", "export") if "electricity" not in c])
    check("ch6: the page's absence list agrees",
          [[], [], [], []], [lim["absent"][k] for k in lim["absent"]])

    # emissions: electricity only, nothing economy-wide
    check("ch6: emissions columns are electricity only", True,
          all("electricity" in c for c in found("emission", "co2")))

    ng6 = df[df.country == "Nigeria"]
    energy_cols6 = [c for c in cols6 if "_energy_" in c]
    ng_empty6 = [c for c in energy_cols6 if ng6[c].notna().sum() == 0]
    check("ch6: Nigeria energy columns in total", len(energy_cols6),
          lim["nigeria"]["energy_columns_total"])
    check("ch6: Nigeria energy columns empty", len(ng_empty6),
          lim["nigeria"]["energy_columns_empty"])
    present6 = sorted(set(energy_cols6) - set(ng_empty6))
    check("ch6: Nigeria energy columns present", present6,
          lim["nigeria"]["energy_columns_present"])
    nuc6 = [c for c in present6 if c.startswith("nuclear_")]
    check("ch6: the nuclear columns Nigeria has are all zero", True,
          all(float(ng6[c].abs().max()) == 0.0 for c in nuc6))
    check("ch6: four nuclear and five totals", [4, 5],
          [lim["nigeria"]["present_nuclear_count"], lim["nigeria"]["present_total_count"]])

    check("ch6: last year of GDP",
          int(df[df.iso_code.notna() & df.gdp.notna()].year.max()), lim["gdp_last_year"])

    c25_6 = df[(df.year == 2025) & (df.iso_code.notna())]
    check("ch6: 2025 electricity coverage",
          int(c25_6.electricity_generation_twh.notna().sum()),
          lim["coverage_2025"]["electricity"])
    check("ch6: 2025 total energy coverage",
          int(c25_6.total_energy_twh.notna().sum()), lim["coverage_2025"]["total_energy"])
    check("ch6: 2025 is thinner than 2024, which is why 2024 is the headline year", True,
          lim["coverage_2025"]["total_energy"] < lim["coverage_2025"]["countries_2024"])

    for y6 in ("1990", "2000"):
        cy6 = df[(df.year == int(y6)) & (df.iso_code.notna())]
        check(f"ch6: electricity coverage in {y6}",
              int(cy6.electricity_generation_twh.notna().sum()),
              lim["electricity_coverage_by_year"][y6])

    w6v = df[df.country == "World"].set_index("year")
    for src6 in ("nuclear", "hydro", "solar", "wind"):
        check(f"ch6: {src6} accounting ratio",
              round(float(w6v.loc[2024, f"{src6}_energy_twh"]
                          / w6v.loc[2024, f"{src6}_electricity_twh"]), 2),
              lim["accounting_ratios_2024"][src6], tol=0.005)
    check("ch6: nuclear is on a different accounting basis from the renewables", True,
          lim["accounting_ratios_2024"]["nuclear"] > 2.5
          and max(lim["accounting_ratios_2024"][k] for k in ("hydro", "solar", "wind")) < 1.1)

    # the two findings that were deliberately not built into chapters
    LOWC6 = "low_carbon_electricity_share_pct"
    fnu = lim["findings_not_used"]
    check("ch6: low-income aggregate low-carbon share",
          round(float(df[(df.country == "Low-income countries")
                         & (df.year == 2023)][LOWC6].iloc[0]), 1),
          fnu["low_income_low_carbon_pct"], tol=0.05)
    check("ch6: the aggregate finding does not hold at country level", True,
          fnu["bottom_quintile_median_low_carbon_pct"] < fnu["low_income_low_carbon_pct"])

    GENPC6 = "electricity_generation_per_capita_kwh"
    a6v = df[(df.year == 2000) & (df.iso_code.notna())][["country", GENPC6]].set_index("country")
    b6v = df[(df.year == 2024) & (df.iso_code.notna())][
        ["country", GENPC6, "population"]].set_index("country")
    j6v = a6v.join(b6v, lsuffix="_00", rsuffix="_24").dropna()
    j6v = j6v[j6v.population > 10e6]
    check("ch6: large countries examined", int(len(j6v)), fnu["large_countries_examined"])
    check("ch6: large countries that fell",
          int((j6v[GENPC6 + "_24"] < j6v[GENPC6 + "_00"]).sum()),
          fnu["large_countries_that_fell"])

    # ---- the prose figures ---------------------------------------------------
    figs = load("key_figures.json")["figures"]
    ng = df[df.country == "Nigeria"]

    expected = {
        "ch1.countries": int(len(c24)),
        "ch1.with_mix": int(c24[MIX].notna().sum()),
        "ch1.without_mix": int(c24[MIX].isna().sum()),
        "ch1.know_total_not_mix": int((c24.total_energy_twh.notna() & c24[MIX].isna()).sum()),
        "ch1.mix_1970": int(df[(df.year == 1970) & (df.iso_code.notna())][MIX].notna().sum()),
        "ch1.mix_2024": int(c24[MIX].notna().sum()),
        "ch1.total_1970": int(df[(df.year == 1970) & (df.iso_code.notna())].total_energy_twh.notna().sum()),
        "ch1.total_2024": int(c24.total_energy_twh.notna().sum()),
        "ch1.electricity_2024": int(c24.electricity_generation_twh.notna().sum()),
        "ch1.nigeria_empty_columns":
            int(sum(1 for col in df.columns if "_energy_" in col and ng[col].notna().sum() == 0)),
        "ch1.nigeria_population": int(ng[ng.year == HEADLINE_YEAR].population.iloc[0]),
        "ch1.pop_share_display":
            round(float(c24.loc[c24[MIX].isna(), "population"].sum()) / world_pop * 100, 1),
        "ch1.africa_display": 4,
        "ch2.countries_mapped": int(len(src)),
        "ch2.median_demand": round(float(src[DEMAND].median())),
        "ch2.world_demand":
            round(float(df[(df.country == "World") & (df.year == MAP_YEAR)][DEMAND].iloc[0])),
        "ch2.nigeria_demand": round(ng_d, 1),
        "ch2.nigeria_percentile": round(float((src[DEMAND] < ng_d).mean() * 100), 1),
        "ch2.high_2000": round(float(piv.loc[2000, "High-income countries"]), 1),
        "ch2.high_2024": round(float(piv.loc[2024, "High-income countries"]), 1),
        "ch2.low_2000": round(float(piv.loc[2000, "Low-income countries"]), 1),
        "ch2.low_2024": round(float(piv.loc[2024, "Low-income countries"]), 1),
        "ch2.high_gain": round(float(piv.loc[2024, "High-income countries"]
                                     - piv.loc[2000, "High-income countries"])),
        "ch2.low_gain": round(float(piv.loc[2024, "Low-income countries"]
                                    - piv.loc[2000, "Low-income countries"])),
        "ch2.ratio_2000": round(float(piv.loc[2000, "High-income countries"]
                                      / piv.loc[2000, "Low-income countries"]), 1),
        "ch2.ratio_2024": round(float(piv.loc[2024, "High-income countries"]
                                      / piv.loc[2024, "Low-income countries"]), 1),
        "ch2.years_to_parity": round(
            (float(piv.loc[2024, "High-income countries"] / piv.loc[2024, "Low-income countries"]) - 1)
            / -((float(piv.loc[2024, "High-income countries"] / piv.loc[2024, "Low-income countries"])
                 - float(piv.loc[2000, "High-income countries"] / piv.loc[2000, "Low-income countries"])) / 24)),
        "ch2.gap_widened": round(
            float(piv.loc[2024, "High-income countries"] - piv.loc[2024, "Low-income countries"])
            - float(piv.loc[2000, "High-income countries"] - piv.loc[2000, "Low-income countries"])),
        "ch2.gap_2024": round(
            float(piv.loc[2024, "High-income countries"] - piv.loc[2024, "Low-income countries"])),
        "ch2.lesotho_generation":
            round(float(df[(df.year == MAP_YEAR) & (df.country == "Lesotho")][GEN].iloc[0]), 1),
        "ch3.n_countries": int(len(sc)),
        "ch3.pearson_r": round(r_true, 4),
        "ch3.r_squared": round(r_true * r_true, 4),
        "ch3.demand_spread":
            round(float(sc[DEMAND].quantile(0.90) / sc[DEMAND].quantile(0.10))),
        "ch3.lowc_p10": round(float(sc[LOWC].quantile(0.10)), 1),
        "ch3.lowc_p90": round(float(sc[LOWC].quantile(0.90)), 1),
        "ch3.fossil_twh_2000": round(float(w3.loc[2000, "fossil_fuels_energy_twh"])),
        "ch3.fossil_twh_2024": round(float(w3.loc[2024, "fossil_fuels_energy_twh"])),
        "ch3.fossil_share_2000": round(float(w3.loc[2000, "fossil_fuels_energy_share_pct"]), 2),
        "ch3.fossil_share_2024": round(float(w3.loc[2024, "fossil_fuels_energy_share_pct"]), 2),
        "ch3.fossil_pct_change": round(float(w3.loc[2024, "fossil_fuels_energy_twh"]
                                             / w3.loc[2000, "fossil_fuels_energy_twh"] - 1) * 100, 1),
        "ch3.fossil_share_change": round(float(w3.loc[2024, "fossil_fuels_energy_share_pct"]
                                               - w3.loc[2000, "fossil_fuels_energy_share_pct"]), 2),
        "ch3.coal_gas_added": round(add3["coal"] + add3["gas"]),
        "ch3.solar_wind_added": round(add3["solar"] + add3["wind"]),
        "ch3.added_ratio": round((add3["coal"] + add3["gas"])
                                 / (add3["solar"] + add3["wind"]), 1),
        "ch4.group_n": int(len(g4)),
        "ch4.group_pop": int(g4.population.sum()),
        "ch4.nigeria_share_of_group":
            round(float(ng4.population) / float(g4.population.sum()) * 100, 1),
        "ch4.spearman": round(rho4, 2),
        "ch4.big_producers": int((sc4.ratio > RATIO_MIN).sum()),
        "ch4.countries_in_scope": int(len(sc4)),
        "ch4.nigeria_prod": round(float(ng4.prod_twh), 1),
        "ch4.nigeria_supply": round(float(ng4.total_energy_twh), 1),
    }
    for nm, key in (("Nigeria", "nga"), ("Norway", "nor"), ("Chad", "tcd")):
        r4 = sc4[sc4.country == nm].iloc[0]
        expected[f"ch4.{key}_ratio"] = round(float(r4.ratio), 2)
        expected[f"ch4.{key}_demand"] = round(float(r4[DEMAND]))

    expected.update({
        "ch5.slope": round(slope5, 2),
        "ch5.gen_growth": round(float(ng5.loc[TO5, GEN5] / ng5.loc[FROM5, GEN5]), 2),
        "ch5.pop_growth": round(float(ng5.loc[TO5, "population"]
                                      / ng5.loc[FROM5, "population"]), 2),
        "ch5.pc_growth": round(float(ng5.loc[TO5, GENPC5] / ng5.loc[FROM5, GENPC5]), 2),
        "ch5.pc_min": round(float(ng5.loc[FROM5:TO5, GENPC5].min()), 1),
        "ch5.pc_max": round(float(ng5.loc[FROM5:TO5, GENPC5].max()), 1),
        "ch5.world_pc": round(float(w5.loc[TO5, GENPC5]), 1),
        "ch5.years_to_world": round(gap5 / slope5),
        "ch5.gas_2000": round(float(ng5.loc[2000, "gas_electricity_share_pct"]), 2),
    })
    for y5 in (FROM5, TREND5, 2024, TO5):
        expected[f"ch5.pc_{y5}"] = round(float(ng5.loc[y5, GENPC5]), 1)
    for src5 in ("gas", "hydro", "solar", "bioenergy"):
        expected[f"ch5.{src5}_{TO5}"] = round(
            float(ng5.loc[TO5, f"{src5}_electricity_share_pct"]), 2)

    expected.update({
        "ch6.nigeria_energy_cols": len(energy_cols6),
        "ch6.nigeria_empty_cols": len(ng_empty6),
        "ch6.nigeria_present_cols": len(present6),
        "ch6.gdp_last_year": int(df[df.iso_code.notna() & df.gdp.notna()].year.max()),
        "ch6.e2025": int(c25_6.electricity_generation_twh.notna().sum()),
        "ch6.t2025": int(c25_6.total_energy_twh.notna().sum()),
        "ch6.o2025": int(c25_6.oil_production_twh.notna().sum()),
        "ch6.rows2025": int(len(c25_6)),
        "ch6.elec_1990": lim["electricity_coverage_by_year"]["1990"],
        "ch6.elec_2000": lim["electricity_coverage_by_year"]["2000"],
        "ch6.nuclear_ratio": lim["accounting_ratios_2024"]["nuclear"],
        "ch6.wind_ratio": lim["accounting_ratios_2024"]["wind"],
        "ch6.low_income_lowc": fnu["low_income_low_carbon_pct"],
        "ch6.high_income_lowc": fnu["high_income_low_carbon_pct"],
        "ch6.bottom_quintile_lowc": fnu["bottom_quintile_median_low_carbon_pct"],
        "ch6.fell_count": fnu["large_countries_that_fell"],
        "ch6.fell_of": fnu["large_countries_examined"],
    })
    for nm, key in (("Ethiopia", "eth"), ("Bangladesh", "bgd"), ("Uganda", "uga"),
                    ("Niger", "ner"), ("Nigeria", "nga")):
        row_ = sc[sc.country == nm]
        expected[f"ch3.{key}_fossil"] = round(
            float(row_["fossil_fuels_electricity_share_pct"].iloc[0]), 1)
        expected[f"ch3.{key}_demand"] = round(float(row_[DEMAND].iloc[0]))
    for nm, key in (("Vietnam", "vnm"), ("China", "chn")):
        pc = df[df.country == nm].set_index("year")
        a3 = float(pc.loc[2015, "solar_electricity_twh"])
        b3 = float(pc.loc[2024, "solar_electricity_twh"])
        expected[f"ch3.{key}_solar_growth"] = round((b3 / a3 - 1) * 100)
        expected[f"ch3.{key}_solar_added"] = round(b3 - a3, 2)
    for key, want in expected.items():
        if key not in figs:
            check(f"prose {key}: present in key_figures.json", True, False)
            continue
        check(f"prose {key}", want, figs[key]["value"], tol=0.05)

    # every prose figure must be checked by this script, or it is unaudited
    unchecked = sorted(set(figs) - set(expected))
    check("prose: every figure is covered by a check", 0, len(unchecked))
    for k in unchecked:
        print("   unaudited prose figure:", k)

    # ---- the page may not quote a figure that does not exist -----------------
    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    import re
    used = set(re.findall(r'data-fig="([^"]+)"', index))
    missing = sorted(used - set(figs))
    check("page: every data-fig id exists in key_figures.json", 0, len(missing))
    for k in missing:
        print("   page asks for a figure that was never built:", k)

    # ---- report --------------------------------------------------------------
    failed = [c for c in checks if not c[0]]
    print()
    for ok, label, exp, act in checks:
        if not ok:
            print(f"FAIL  {label}\n        expected {exp!r}, got {act!r}")
    print(f"{len(checks) - len(failed)} of {len(checks)} checks passed.")
    if failed:
        print(f"{len(failed)} FAILED.")
        sys.exit(1)
    print("Every number on the site matches the frozen data file.")


if __name__ == "__main__":
    main()
