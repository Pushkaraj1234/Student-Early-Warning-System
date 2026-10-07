# Week 10 — Poster, presentation, demo, peer review and viva

Status 2026-10-08. Slide deck (16 slides with speaker notes): the "SEWS final presentation" artifact
(private — share it from its Share menu; downloads as PowerPoint or PDF). Placeholders in square brackets —
team names and roll numbers, guide, department, college, date — must be filled in by the team.

## 1. Talk plan (12–15 minutes)

| Min | Slides | Who | Message |
|---|---|---|---|
| 0–2 | Title, problem, objectives | [member 1] | Scale of the problem; six objectives with measurable tests |
| 2–5 | Gap, system, data and ethics, method | [member 2] | Honest method: leakage guard, out-of-time tests, pre-registration |
| 5–9 | Results 1–5 | [member 3] | Earlier = weaker; assignments and backlogs matter; simple models suffice; fairness gaps; alert design |
| 9–12 | Live demo | [member 4] | Student → mentor → administrator workflow |
| 12–15 | IP and TRL, limitations, conclusion | [member 1] | Not patentable; TRL 4; next step is a college pilot |

## 2. Poster (A1 portrait, 594 × 841 mm)

Layout top to bottom; same colours and typefaces as the slides (navy #14213D, off-white #FBFBF8, teal #00696B,
orange #B5502A; Source Serif 4 headings, IBM Plex Sans text). Body text at least 24 pt, readable from 1.5 m.

1. **Header band (navy):** "SEWS — Student Early Warning & Intervention System"; team, guide, department, college.
2. **Problem (left) | Objectives (right):** 4.33 crore students, 45,473 colleges (AISHE 2021-22); one sentence
   research question; O1–O6.
3. **System diagram:** app/website → database with row-level security ← batch jobs ← ML pipeline with approval.
4. **Method strip:** pre-register → as-of features + leakage guard → out-of-time split → bootstrap CIs + Holm →
   fairness and explanations.
5. **Results (centre, largest):** the earliness chart (`ml/reports/oulad-ts-v3-20261005T192442Z/pr_auc_by_week.png`),
   the model table (RF 0.775 · XGBoost 0.769 · LSTM 0.762 · LASSO 0.754 · chance 0.353), the semester result
   (0.56 → 0.80 → 0.84), the fairness table, and the alert finding (85% of passing students crossed a weekly
   threshold at least once).
6. **IP and readiness:** six patents, not patentable under Section 3(k), TRL 4 → pilot.
7. **Footer:** limitations (benchmark data from the UK and Portugal only), 5 key references, QR code to the
   repository or report (only if the team makes it public).

## 3. Demo script (website, testing project, synthetic accounts only)

Before the session: start the website (`docs/architecture/deployment.md`, "Website"), sign in once with each
account, and capture a backup screenshot of every step below in case the network fails. Never use a real
student's account.

1. **Student** (`student.beta@synthetic.example.com`): Home shows the risk level and its main reasons → open the
   explanation → recommended action → submit a check-in.
2. **Mentor** (`mentor.test@synthetic.example.com`): caseload with risk distribution and "Rising risk" → open
   Synthetic Student Beta → trend, factors, previous predictions → approve the suggested intervention → record
   its outcome.
3. **Administrator** (create the account first: `deployment.md`, "Admin account"): model registry with statuses,
   open drift alerts, why benchmark-trained models cannot be approved.
4. **Wide screen:** resize the browser to show the side navigation on desktop and the bottom bar on a phone width.

## 4. Peer-review checklist (use for a rehearsal and for reviewing another team)

- Is the research question stated in one sentence, and answered by the end?
- Are numbers read against a baseline (chance PR-AUC = share at risk)?
- Is every result labelled with its data source (benchmark, synthetic, institutional)?
- Are limitations stated before the examiner has to ask?
- Does the demo show the human decision, not only the prediction?
- Are slides readable from the back row (no text under 24 px, one idea per slide)?
- Does the talk fit in time with two minutes for questions?

## 5. Viva questions and answers

| Question | Answer (with where to find the evidence) |
|---|---|
| What is data leakage and how did you prevent it? | Using information that would not exist yet at prediction time. Features are built "as of" the decision day; a guard rebuilds them from data cut at that day and stops training on any difference (passed at every decision point and at 6 weekly checkpoints). |
| Why PR-AUC and not accuracy? | The outcome is imbalanced; a model can be "accurate" by predicting that nobody is at risk. PR-AUC measures how well at-risk students are ranked and is read against the base rate (0.353 on the test set). |
| Why a time-ordered split? | Cohorts change; a random split mixes future and past students and inflates results. We train on 2013, tune on early 2014 and test once on late 2014. |
| What does "pre-registered" mean here? | The ten hypotheses, tests and decision rules were written in week 4 before any test was run; clarifications were logged before the run. |
| Why did the LSTM not beat XGBoost? | The 37 hand-built time-window features already capture the trajectory; the sequence model learned the same signal (0.762 vs 0.769). We report this negative result. |
| Why not use gender or caste as inputs? | A student's risk must not rise because of who they are. Demographics are used only to audit errors; adding them changed PR-AUC by 0.002 and widened the gender gap. |
| Your model misses more at-risk women. What will you do? | Audit every institutional model before approval; consider per-group thresholds only as an institutional decision (on one model they over-corrected the gap). |
| How is a prediction explained? | SHAP contributions mapped to plain-language factors for students and mentors; counterfactuals show which change (e.g. submitting on time) would lower the estimate — what the model responds to, not causes. |
| Is the probability trustworthy? | Calibration is checked out of time; calibration is applied only if it improves both Brier score and ECE (raw XGBoost ECE 0.050). |
| Does this work for Indian colleges? | Not yet shown (RQ5). All results are UK or Portuguese benchmark data. The next step is retrospective training on one college's anonymised past terms with ethics approval. |
| What about student privacy? | Row-level security in the database, no secret keys in clients, minimum data, consent, DPDP Act 2023 basis required before real data; models trained on benchmark data can never be approved for real students. |
| Could a false alarm harm a student? | Yes — stigma and anxiety. That is why a mentor reviews every suggestion, students see supportive wording, and alert thresholds are set per student over a term rather than every week. |
| What is your contribution if early warning already exists? | A careful, reproducible and audited method inside a working system designed for Indian colleges: leakage guard, pre-registered tests, fairness audits, human approval and per-institution training. |
| Why is it not patentable? | Prior art since 2008 and Section 3(k) of the Patents Act excludes algorithms and business methods without a technical effect (week 9). |
| What is the TRL? | 4 — validated in a lab setting with benchmark and synthetic data; TRL 5 needs real institutional data. |
| What would you do with more time? | The college pilot, the mentor usability survey (SUS), and measuring outcomes of interventions with a designed study. |

## 6. Before the presentation (team checklist)

- [ ] Fill in names, roll numbers, guide, department, college and date on the cover and closing slides.
- [ ] Share the deck from its Share menu with the guide; download PowerPoint and PDF copies.
- [ ] Rehearse twice with a timer; assign speakers.
- [ ] Prepare the demo and backup screenshots.
- [ ] Build the poster from §2 (Canva, PowerPoint or Overleaf) and print at A1.
