# Course alignment — research methodology mini-project (10 weeks)

Status 2026-10-03. Maps every week of the course to what the SEWS project (Student Early Warning & Intervention
System) has, where the evidence is, and what is still missing. Updated as each deliverable is finished.

Legend: **done** = exists and is verified · **partial** = exists but not in the form the course asks for ·
**missing** = not started · **yours** = needs a decision, a file or an action only the student/team can provide.

| Week | Course requirement | Status | Evidence in the repository | Still to do |
|---|---|---|---|---|
| 1 | Problem identification: problem statement, objectives, scope, expected outcomes | **done** (2026-10-03) | [week01-problem-statement.md](week01-problem-statement.md); detail in [problem-definition.md](problem-definition.md), [project-scope.md](project-scope.md) | Optional: Google Trends screenshot for the topic (yours) |
| 2 | Literature review, literature matrix, research gaps, research questions | **done** (first version) | [week02-literature-review.md](week02-literature-review.md); [research-questions.md](research-questions.md) | Extend the search in IEEE Xplore / Scopus and add ResearchRabbit or Connected Papers maps (yours, the databases need your institution login) |
| 3 | AI-assisted research, responsible AI, plagiarism, hallucinations, ethics | **done** (first version) | [week03-ai-use-and-ethics.md](week03-ai-use-and-ethics.md); [security-model.md](../security/security-model.md); [fairness.md](../ml/fairness.md) | Turnitin check of the final report (yours) |
| 4 | Hypotheses, experimental design, sampling, data collection | **partial** | Design: out-of-time split, decision points, three model families ([results-v2.md](../ml/results-v2.md)); data: OULAD (public, CC BY 4.0), NSS 75th round, synthetic history | Formal hypotheses H1–H5 written before testing |
| 5 | Data cleaning, missing values, outliers, feature engineering, descriptive statistics, visualisation | **partial** | Feature engineering and leakage guard ([data-contract.md](../ml/data-contract.md)); missing values handled in the pipeline | An exploratory-analysis notebook with descriptive statistics and charts |
| 6 | Correlation, regression, hypothesis testing, performance metrics, validation | **partial** | Metrics, out-of-time validation, bootstrap confidence intervals, calibration, subgroup audit | Significance tests between models (paired bootstrap / DeLong), feature-family ablation (RQ2), correlation analysis |
| 7 | Prototype / proof of concept, version control, reproducibility, documentation | **done** | Mobile app, database, backend jobs, ML pipeline, in-app training; GitHub repository; 130 + 139 + 109 automated tests; 390 database checks | — |
| 8 | Technical writing: abstract, introduction, methodology, results, conclusion; IEEE references | **missing** | Technical docs exist, but no paper | IEEE-format paper (Overleaf template) — needs team names, college, guide (yours) |
| 9 | Patent search, prior-art analysis, technology readiness level, commercialisation | **missing** | — | Prior-art search (Google Patents / WIPO / InPASS), TRL assessment, commercialisation note |
| 10 | Poster, presentation, demo, peer review and viva | **missing** | A working demo exists (app on the emulator) | Poster, slides, demo script, viva questions |

## Order of work from here

1. Week 4 — hypotheses (stated before the tests are run, so they cannot be fitted to the results).
2. Week 5 — exploratory analysis notebook on OULAD (the only real dataset the project may use).
3. Week 6 — statistical tests and the feature-family ablation (answers RQ2).
4. Week 9 — prior-art and TRL (independent of the paper).
5. Week 8 — the paper, using the results of weeks 4–6.
6. Week 10 — poster, slides and viva preparation from the paper.

## What the student/team must provide

- Team member names, roll numbers, college and department, guide's name — for the paper, poster and slides.
- Whether the instructor wants a specific template (IEEE conference paper is assumed; Overleaf).
- Access to IEEE Xplore / Scopus through the college, to extend the literature search.
- Approval before any real student data is used (ethics; DPDP Act 2023).
