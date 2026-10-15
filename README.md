# Energy Justice: who is counted, who is powered, who is mined

A data essay built from the Our World in Data energy dataset. Six chapters, each one claim
the data supports, with the evidence and the column names behind it.

By Olalekan Joshua Alagbe. Nigeria appears as a recurring case throughout.

## What it says

The project started from a different idea. I expected to find three kinds of country moving at
different speeds through one energy transition. The data did not support that, so I changed
the story.

What the data does show is that energy inequality is about quantity, not cleanliness. How
clean a country's electricity is tells you almost nothing about how much of it people get.
Across 158 countries the correlation between the two is r = 0.0002. What separates countries
is the amount, and for the poorest countries the amount has barely moved in a quarter century.

The dataset is also unequal in itself. It describes the energy mix of 74 countries in detail
and reports only a total for the other 146. Nigeria is in the second group.

## The data

Our World in Data, complete energy dataset, release 2026-09-10. 19,494 rows, 130 columns,
covering 1700 to 2025.

Compiled by Our World in Data from the Energy Institute Statistical Review of World Energy
(2026), Ember Yearly Electricity Data (2026), the US Energy Information Administration, the
Maddison Project Database 2023, and several historical reconstructions. Full source list and
licensing at https://ourworldindata.org/energy.

The file in `data/owid-energy-2026-10-14.csv` is frozen. It is the copy every number comes
from and it is not edited after the date in its name.

**One thing to know about the numbers.** Energy here is measured as total energy supply. Our
World in Data changed to this on 10 September 2026, replacing the substitution method used in
earlier releases. The two are not directly comparable, and renewable shares in this release
are lower than figures you may have seen in older charts or in news coverage. Every page that
shows a fossil, renewable or low-carbon share says so in a footnote. The limits chapter states
it in full.

## Method

Data is pre-computed in Python. Nothing is loaded or calculated in the browser.

Each chapter has one build script that reads the frozen CSV and writes only the JSON its own
charts need, into `docs/data/`. A separate script collects every number that appears in a
written sentence, so prose figures come from the same build as the charts rather than being
typed by hand. The bundler then concatenates the JSON into one script the page can read, which
is what lets the site work when opened straight from the folder, without a server.

Charts are Plotly, using the partial `geo` build so the page pulls 1.2 MB instead of 4.8 MB.
Bar charts are plain CSS, since the partial build has no bar trace and CSS bars match the rest
of the page better anyway. Colours and typefaces are read out of the stylesheet at runtime, so
the charts and the page cannot drift apart, and both themes come from the same tokens.

## How to view it

The site is static and needs no server.

```
# open it directly
docs/index.html
```

Or serve it locally if you prefer:

```
python -m http.server --directory docs 8000
# then open http://localhost:8000
```

Deployed with GitHub Pages from the `docs/` folder on `main`.

## How to verify it

Every number on the site can be traced back to the frozen CSV and the code that produced it.

```
python -m venv .venv
.venv/Scripts/activate        # on Windows
# source .venv/bin/activate   # on macOS or Linux
pip install -r analysis/requirements.txt

# rebuild every chart and prose figure from the frozen data
python analysis/20_build_ch1.py
python analysis/21_build_ch2.py
python analysis/22_build_ch3.py
python analysis/23_build_ch4.py
python analysis/24_build_ch5.py
python analysis/25_build_key_figures.py
python analysis/26_bundle.py

# re-derive every number the site shows and compare
python analysis/27_verify_site_numbers.py
```

`27_verify_site_numbers.py` does not trust the generated JSON. It recomputes each figure from
`data/owid-energy-2026-10-14.csv`, compares, prints any mismatch and exits non-zero. It checks
every chart row, every prose figure, and the statistics behind the claims: it re-runs the
regressions, re-derives the correlations, and re-scans the column names behind every claim on
the limits page that something is missing. It fails if the page quotes a figure that was never
built, or if a built figure is not covered by a check.

## Repository

```
data/           the frozen CSV, named with the date it was taken
analysis/       the build scripts, the figure collector, the bundler, the verifier
docs/           the site. HTML, CSS, JS, the vendored Plotly build, and the chart JSON
```

In `analysis/`:

| Script | What it does |
|---|---|
| `20_build_ch1.py` | Chapter 1, what the dataset can and cannot describe |
| `21_build_ch2.py` | Chapter 2, electricity per person and the income groups |
| `22_build_ch3.py` | Chapter 3, the scatter, world fossil supply, the growth trap |
| `23_build_ch4.py` | Chapter 4, production against electricity used |
| `24_build_ch5.py` | Chapter 5, Nigeria |
| `25_build_key_figures.py` | every number quoted in prose, and Chapter 6's limits |
| `26_bundle.py` | JSON into one script the page can read from `file://` |
| `27_verify_site_numbers.py` | re-derives everything and fails on a mismatch |

Each build script reads only the frozen CSV and writes only its own chapter's JSON. None of
them import from any other.

## Limitations

The full version is Chapter 6 on the site. The short version:

- **There is no electricity access column.** Per person generation and demand are different
  measures. A country can look adequate on average and still leave most households unserved.
- **The energy mix is missing for 146 of 220 countries**, including Nigeria. Of the 66 columns
  describing energy supply, 57 are empty for Nigeria in every year. Four of the nine that
  remain are nuclear and read zero; the other five are the total and figures derived from it.
- **Traditional biomass is not counted.** The sources cover commercially traded fuels, so
  firewood and charcoal are outside them. For Nigeria that is most household cooking energy.
- **Off-grid and self-generation are invisible.** Private generators do not appear.
- **Flared gas is excluded** from gas production.
- **Every figure is a national average.** There is no data inside countries, and national
  averages are where energy injustice hides.
- **No prices, no reliability.** Nothing on affordability, tariffs or outage hours.
- **Electricity emissions only**, from 2000. No economy-wide emissions.
- **Production minus supply is an accounting residual**, not a measurement of exports. The
  sources warn the two sides do not reconcile exactly.
- **Country-level electricity before 2000 is thin.** The codebook says 1900, but before 1985
  only the United Kingdom and the world aggregate have it.
- **GDP ends in 2022**, three years before the energy data.
- **2025 is incomplete.** 90 of 220 countries have electricity and 79 have total energy, so
  2024 is the headline year and 2023 is used wherever many countries are ranked or mapped.

## Licence

Code in this repository is MIT. The data is republished by Our World in Data under the terms
of its original producers. Check those terms before reusing it:
https://ourworldindata.org/energy
