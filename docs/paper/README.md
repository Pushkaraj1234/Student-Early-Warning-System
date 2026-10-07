# SEWS paper (course week 8)

`sews-ieee.tex` is an IEEE conference paper (IEEEtran class, about 5–6 pages) built from the results of weeks 4–6,
the weekly longitudinal study and the external datasets. Every number in it was checked against the run reports:

| Paper section | Source |
|---|---|
| Pre-registered hypotheses (Table I) | [week06-statistical-analysis.md](../research/week06-statistical-analysis.md), `ml/reports/hypotheses-20261003T095318Z/` |
| Weekly longitudinal study, alerts, uncertainty | [longitudinal-v3.md](../ml/longitudinal-v3.md), `ml/reports/oulad-ts-v3-20261005T192442Z/` |
| Replications (Portugal) | [external-datasets.md](../ml/external-datasets.md), `ml/reports/external-v1-20261007T184644Z/` |
| Related work and references | [week02-literature-review.md](../research/week02-literature-review.md) |

## Compile (Overleaf)

1. Overleaf → New project → Upload project; upload `sews-ieee.tex` and the `figures/` folder (keep the folder name).
2. Compiler: pdfLaTeX. `IEEEtran` is built into Overleaf; no other files are needed.
3. Check the page count against the conference's limit; Fig. `kaplan_meier.png` is included in `figures/` as a spare
   if a second figure fits.

Locally: `pdflatex sews-ieee.tex` twice (needs a TeX distribution with IEEEtran, e.g. TeX Live or MiKTeX).

## Before submission (team)

- [ ] Replace the placeholders: `[Author 1]`, `[Author 2]`, `[Guide]`, `[Department]`, `[College]`, `[City]`,
      `[email]`. Agree the author order with the guide.
- [ ] Check the target venue's template and page limit (this uses the standard IEEE conference format).
- [ ] Verify these method references against the publisher's page (they were not part of the week 2 review):
      `page1954`, `tibshirani1996`, `cho2014`, `hochreiter1997`, `bai2018`, `chawla2002`, `singer1993`,
      `harrell1982`, `gal2016`, `delong1988`, `holm1979`, and the author lists of `realinho2021` and `cortez2008`.
- [ ] `le2026` is a preprint (not peer-reviewed); keep it labelled as such or replace it if a published version
      appears.
- [ ] Decide whether to make the code public. The paper says nothing about availability; if the repository
      becomes public, add a "Code and data availability" sentence (publication is prior art — see week 9).
- [ ] Run the plagiarism check the college requires.
- [ ] Disclose AI assistance as the venue requires (see [week03-ai-use-and-ethics.md](../research/week03-ai-use-and-ethics.md)).

## What the paper does not claim

All results are from UK and Portuguese benchmark data; nothing in it is evidence about Indian students, and no
model reported here is approved for real students.
