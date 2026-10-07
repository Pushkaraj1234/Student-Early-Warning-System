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
| 4 | Hypotheses, experimental design, sampling, data collection | **done** (2026-10-03) | [week04-research-design.md](week04-research-design.md): 10 hypotheses with tests and Holm correction fixed before testing, design, sampling, data sources, planned mentor questionnaire | Run the mentor questionnaire after a pilot (needs ethics approval) |
| 5 | Data cleaning, missing values, outliers, feature engineering, descriptive statistics, visualisation | **done** (2026-10-03) | [week05-eda.md](week05-eda.md); generated report with 9 tables and 5 charts (`ml/reports/eda-oulad-20261003T093048Z/`), code `ml/analysis/eda.py` | — |
| 6 | Correlation, regression, hypothesis testing, performance metrics, validation | **done** (2026-10-03) | [week06-statistical-analysis.md](week06-statistical-analysis.md): 10 pre-registered tests, Holm-corrected, all supported; report `ml/reports/hypotheses-20261003T095318Z/`; code `ml/analysis/hypotheses.py` | — |
| 7 | Prototype / proof of concept, version control, reproducibility, documentation | **done** | Mobile app and website, database, backend jobs, ML pipeline, in-app training; weekly longitudinal model ([longitudinal-v3.md](../ml/longitudinal-v3.md)) and two external benchmark datasets ([external-datasets.md](../ml/external-datasets.md)); GitHub repository; 130 + 181 + 115 automated tests; 390 database checks | — |
| 8 | Technical writing: abstract, introduction, methodology, results, conclusion; IEEE references | **missing** | Technical docs exist, but no paper | IEEE-format paper (Overleaf template) — needs team names, college, guide (yours) |
| 9 | Patent search, prior-art analysis, technology readiness level, commercialisation | **missing** | — | Prior-art search (Google Patents / WIPO / InPASS), TRL assessment, commercialisation note |
| 10 | Poster, presentation, demo, peer review and viva | **missing** | A working demo exists (app on the emulator) | Poster, slides, demo script, viva questions |

## Order of work from here

1. ~~Week 4 — hypotheses~~ done 2026-10-03.
2. ~~Week 5 — exploratory analysis~~ done 2026-10-03.
3. ~~Week 6 — statistical tests~~ done 2026-10-03.
4. Week 9 — prior-art and TRL (independent of the paper).
5. Week 8 — the paper, using the results of weeks 4–6.
6. Week 10 — poster, slides and viva preparation from the paper.

## What the student/team must provide

- Team member names, roll numbers, college and department, guide's name — for the paper, poster and slides.
- Whether the instructor wants a specific template (IEEE conference paper is assumed; Overleaf).
- Access to IEEE Xplore / Scopus through the college, to extend the literature search.
- Approval before any real student data is used (ethics; DPDP Act 2023).
