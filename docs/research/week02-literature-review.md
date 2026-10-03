# Week 2 — Literature review and research gap

Status 2026-10-03, first version. **Every source below was checked to exist** (title, authors, venue, year and DOI or
URL looked up on the publisher, ACM Digital Library, Semantic Scholar or arXiv). Findings are limited to what could be
confirmed from the abstract or publisher page; anything not confirmed is marked. Two search-engine summaries contained
false details during this review — see [week 3](week03-ai-use-and-ethics.md) §3.

## 1. Search method

| Item | Detail |
|---|---|
| Question | How are students at academic risk identified early, how are such models evaluated, and what limits their fair and trustworthy use? |
| Sources searched | Web search over publisher sites and indexes: ACM Digital Library (LAK, KDD, L@S), Springer (IJAIED, UMUAI, SN Computer Science), Nature (Scientific Data), Journal of Learning Analytics, MDPI, Elsevier, NeurIPS proceedings, arXiv; Indian government sources for context |
| Search terms | early warning / at-risk students / learning analytics; student dropout prediction; OULAD; fairness / algorithmic bias in education; explainable AI in education; data leakage; probability calibration; India higher education dropout |
| Inclusion | Peer-reviewed papers on predicting student success or risk, their evaluation, fairness or explanation; the method papers SEWS relies on; official Indian statistics and law. Preprints included only if directly relevant and marked as such |
| Exclusion | Blog posts, vendor pages, papers whose existence or bibliographic details could not be confirmed |
| Limitation | Not a full PRISMA systematic review: IEEE Xplore and Scopus need an institutional login. The team should repeat the search there and extend it with ResearchRabbit / Connected Papers (course tools) |

## 2. Literature matrix

| # | Reference | Setting / data | Method | Key finding (verified) | Relevance to SEWS | Limitation / gap |
|---|---|---|---|---|---|---|
| 1 | Arnold & Pistilli, 2012 [1] | Purdue University, USA | Course Signals: early alerts shown to students and instructors | Predicts performance from grades, demographics, past academic history and effort measured as LMS interaction; gives real-time feedback to students | Early, two-sided feedback (student + staff) — the model SEWS follows | Single institution; uses demographics as predictors (SEWS excludes protected attributes) |
| 2 | Jayaprakash et al., 2014 [2] | Open Academic Analytics Initiative, Marist College and partner institutions, USA | Open-source early-alert models; portability across institutions; interventions | Reports predictive performance, portability of models across pilot institutions, and intervention results | Portability across institutions = SEWS's cross-group concern (RQ5) | US institutions |
| 3 | Kuzilek, Hlosta & Zdrahal, 2017 [3] | Open University, UK | Data descriptor | OULAD: 22 module presentations, 32,593 students, assessments, demographics and 10,655,280 daily VLE click summaries, CC BY 4.0 | The benchmark SEWS uses for method development | UK distance learning; no attendance data; not Indian |
| 4 | Hlosta, Zdrahal & Zendulka, 2017 [4] | Open University, UK | "Ouroboros": models trained on the current running course instead of legacy data; imbalanced classification | Training on the same running course is a valid alternative to models learned from previous presentations | Shows the cohort-shift problem SEWS measures with out-of-time splits | Same institution |
| 5 | Herodotou et al., 2019 [5] | Open University, UK; 559 teachers, >14,000 students, 15 undergraduate courses | Predictive learning analytics used by teachers | Teachers who made *average* use of the predictions and intervened benefited their students the most | Predictions only help when people act on them → SEWS's human-in-the-loop workflow | Observational; association, not causation |
| 6 | Gardner & Brooks, 2018 [6] | MOOCs (review) | Survey of predictors, outcomes, models and evaluation methods | Categorises MOOC success-prediction work and critically reviews feature engineering and evaluation practice | Evaluation practice (how splits and metrics are chosen) | MOOCs differ from degree programmes |
| 7 | Namoun & Alshanqiti, 2021 [7] | Systematic review of 62 studies | Systematic literature review | Regression and supervised ML dominate; online learning activity, term assessment grades and academic emotions are the most evident predictors | Supports SEWS's feature families (LMS activity, assessments) | — |
| 8 | Glandorf et al., 2024 [8] | Large US university | Dropout prediction at successive points of the degree | AUC improves substantially over time (about 20% higher at the end of year 2 than at enrolment, random forest); important predictors shift from background to college performance | Matches RQ1 (earliness vs accuracy) and SEWS's decision points 30/60/90 | Degree-level dropout, US; yearly rather than within-semester |
| 9 | Le, Abel & Laforge, 2026 [9] (preprint) | LMS interaction logs | LEAP: leakage-excluded early-availability protocol | Ignoring time constraints inflates reported gains, especially from assessment information; performance grows as the observation window grows | Directly supports SEWS's as-of features and leakage guard | Preprint, not peer-reviewed |
| 10 | Kaufman et al., 2012 [10] | General data mining | Formal definition of leakage | Leakage = information about the target that would not legitimately be available; gives a methodology to detect and avoid it | Basis of SEWS's leakage definition | General, not education-specific |
| 11 | Gardner, Brooks & Baker, 2019 [11] | 44 MOOCs, >4 million learners | Slicing analysis; ABROCA (absolute between-ROC area) fairness metric | Models can perform differently across groups (demonstrated by gender); slicing analysis can improve fairness without necessarily losing accuracy | SEWS's subgroup audit ([fairness.md](../ml/fairness.md)) | MOOC data; gender only in the demonstration |
| 12 | Baker & Hawn, 2022 [12] | Review | Review of algorithmic bias in education | Reviews causes of bias and the empirical evidence of how it appears in education | Frames SEWS's fairness obligations | — |
| 13 | Yu, Lee & Kizilcec, 2021 [13] | Large US research university | Dropout models with and without protected attributes | Including protected attributes does not change overall performance and only marginally improves fairness | Supports SEWS excluding protected attributes as inputs while auditing with them | US context |
| 14 | Khosravi et al., 2022 [14] | Conceptual framework | XAI-ED framework for explainable AI in education | Explainability is needed for fairness, accountability, transparency and ethics; proposes six aspects to consider | SEWS's audience-specific explanations (student / mentor / admin) | Framework, not an empirical evaluation |
| 15 | Lundberg & Lee, 2017 [15] | Method | SHAP (Shapley additive explanations) | Unifies several attribution methods with consistency properties | SEWS's per-student factors | Attributions are associations, not causes |
| 16 | Chen & Guestrin, 2016 [16] | Method | XGBoost gradient-boosted trees | Scalable, sparsity-aware tree boosting | One of SEWS's three model families | — |
| 17 | Niculescu-Mizil & Caruana, 2005 [17] | Method | Empirical study of probability calibration | Boosted trees distort probabilities; Platt scaling suits sigmoid-shaped distortion, isotonic regression corrects any monotonic distortion | SEWS calibrates only if an out-of-time check improves Brier and ECE | — |
| 18 | Sihare, 2024 [18] | Higher education (details not verified) | AI/ML for dropout analysis and retention | **Not verified** — abstract not accessible; read before citing any finding | Possible related work on dropout and retention | To be read |
| 19 | Ministry of Education, 2024 [19] | India | AISHE 2021-22 (official statistics) | About 4.33 crore students in higher education; GER 28.4 | Scale of the problem | Statistics, not research on risk |
| 20 | DPDP Act, 2023 [20] | India | Law | A child is a person under 18; processing a child's data needs verifiable parental consent (Section 9) | Why SEWS is limited to adult higher-education students | Rules and dates of application evolve; check the current rules |

Found but not yet read (do not cite until read): *Reliable or Just Accurate? A Cross-Dataset Audit of Early-Warning
Models Under Course-Level Distribution Shift*, Computers (MDPI), 2026, doi:10.3390/computers15090572; *A Machine
Learning Approach to Identify the Students at the Risk of Dropping Out of Secondary Education in India*, Springer
chapter, doi:10.1007/978-981-15-2475-2_51.

## 3. Synthesis by theme

1. **Early-warning systems work only with action.** Course Signals [1], OAAI [2] and the Open University's predictive
   analytics [5] all pair predictions with interventions; [5] shows that how teachers use predictions matters. → SEWS
   sends every suggestion to a mentor and records what was offered, accepted and completed.
2. **Signals and their timing.** LMS activity and assessment results are the most evident predictors [7]; accuracy
   improves as more of the term or degree is observed [8, 9]. → RQ1 and decision points at days 30, 60 and 90.
3. **Evaluation is easy to get wrong.** Leakage [10] and ignoring when information becomes available [9] inflate
   results; models trained on past cohorts can shift [4]. → as-of features, automatic leakage guard, out-of-time
   splits, and cross-module checks.
4. **Probabilities must mean what they say.** Tree ensembles are often poorly calibrated [17]. → calibration decided
   out of time and reported (ECE, Brier).
5. **Fairness and explanation are requirements, not extras** [11–14]. → protected attributes excluded from inputs but
   used for auditing; explanations written for each audience [14, 15].

## 4. Research gaps and how SEWS addresses them

| Gap | Evidence | SEWS response | Research question |
|---|---|---|---|
| G1. Early-warning results are often evaluated without strict time-of-availability rules | [9, 10] | As-of feature builder with a leakage guard; out-of-time splits by cohort/term | RQ1 |
| G2. Calibration under cohort or course shift is rarely reported | [17]; our cross-module check: ECE worsened by up to 0.151 ([results-v2](../ml/results-v2.md)) | Out-of-time calibration decision; ECE and Brier with every result; monitoring in production | RQ1, RQ5 |
| G3. Little reproducible evidence from Indian higher education (attendance rules, CBCS grading, semester structure) | The studies found are mostly UK, US or MOOC [1–8, 11, 13]; Indian-context work [18] not yet assessed | Data model for Indian semesters and CBCS grades; in-app training on an institution's own records | RQ5 |
| G4. Subgroup performance is known to differ, but evidence for Indian social categories was not found | [11, 12, 13] | Subgroup audit framework; benchmark audit done ([fairness.md](../ml/fairness.md)); institutional audit needs approved attributes | RQ4 |
| G5. Predictions are rarely tied to a full, logged human-in-the-loop intervention workflow | [5] shows usage matters; [1, 2] report interventions at institution level | Suggestions hidden until a mentor reviews them; the student accepts or declines; outcomes recorded | RQ6 |
| G6. Explanations rarely tailored to each audience | [14, 15] | Different explanations for students, mentors and admins; stability of top factors measured | RQ3 |

These gaps are stated from the sources reviewed here; a wider search (IEEE Xplore, Scopus) may find work that narrows
them, which the paper must then acknowledge. The research questions are in [research-questions.md](research-questions.md).

## 5. References (IEEE style)

[1] K. E. Arnold and M. D. Pistilli, "Course Signals at Purdue: Using learning analytics to increase student success," in *Proc. 2nd Int. Conf. Learning Analytics and Knowledge (LAK '12)*, 2012, pp. 267–270, doi: 10.1145/2330601.2330666.

[2] S. M. Jayaprakash, E. W. Moody, E. J. M. Lauría, J. R. Regan, and J. D. Baron, "Early alert of academically at-risk students: An open source analytics initiative," *J. Learning Analytics*, vol. 1, no. 1, pp. 6–47, 2014, doi: 10.18608/jla.2014.11.3.

[3] J. Kuzilek, M. Hlosta, and Z. Zdrahal, "Open University Learning Analytics dataset," *Scientific Data*, vol. 4, art. 170171, 2017, doi: 10.1038/sdata.2017.171.

[4] M. Hlosta, Z. Zdrahal, and J. Zendulka, "Ouroboros: Early identification of at-risk students without models based on legacy data," in *Proc. 7th Int. Learning Analytics and Knowledge Conf. (LAK '17)*, 2017, pp. 6–15.

[5] C. Herodotou, M. Hlosta, A. Boroowa, B. Rienties, Z. Zdrahal, and C. Mangafa, "Empowering online teachers through predictive learning analytics," *British J. Educational Technology*, vol. 50, no. 6, pp. 3064–3079, 2019, doi: 10.1111/bjet.12853.

[6] J. Gardner and C. Brooks, "Student success prediction in MOOCs," *User Modeling and User-Adapted Interaction*, vol. 28, pp. 127–203, 2018, doi: 10.1007/s11257-018-9203-z.

[7] A. Namoun and A. Alshanqiti, "Predicting student performance using data mining and learning analytics techniques: A systematic literature review," *Applied Sciences*, vol. 11, no. 1, art. 237, 2021.

[8] D. Glandorf, H. R. Lee, G. A. Orona, M. Pumptow, R. Yu, and C. Fischer, "Temporal and between-group variability in college dropout prediction," in *Proc. 14th Learning Analytics and Knowledge Conf. (LAK '24)*, 2024; arXiv:2401.06498.

[9] N. L. Le, M.-H. Abel, and B. Laforge, "When can we trust early warnings? Leakage-excluded early outcome prediction from LMS interaction logs," arXiv:2605.25794, 2026 (preprint).

[10] S. Kaufman, S. Rosset, C. Perlich, and O. Stitelman, "Leakage in data mining: Formulation, detection, and avoidance," *ACM Trans. Knowledge Discovery from Data*, vol. 6, no. 4, 2012, doi: 10.1145/2382577.2382579.

[11] J. Gardner, C. Brooks, and R. Baker, "Evaluating the fairness of predictive student models through slicing analysis," in *Proc. 9th Int. Conf. Learning Analytics & Knowledge (LAK '19)*, 2019, pp. 225–234, doi: 10.1145/3303772.3303791.

[12] R. S. Baker and A. Hawn, "Algorithmic bias in education," *Int. J. Artificial Intelligence in Education*, vol. 32, no. 4, pp. 1052–1092, 2022, doi: 10.1007/s40593-021-00285-9.

[13] R. Yu, H. Lee, and R. F. Kizilcec, "Should college dropout prediction models include protected attributes?" in *Proc. 8th ACM Conf. Learning @ Scale (L@S '21)*, 2021; arXiv:2103.15237.

[14] H. Khosravi *et al.*, "Explainable artificial intelligence in education," *Computers and Education: Artificial Intelligence*, vol. 3, art. 100074, 2022.

[15] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions," in *Advances in Neural Information Processing Systems 30 (NIPS 2017)*, 2017, pp. 4768–4777.

[16] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proc. 22nd ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining (KDD '16)*, 2016, pp. 785–794, doi: 10.1145/2939672.2939785.

[17] A. Niculescu-Mizil and R. Caruana, "Predicting good probabilities with supervised learning," in *Proc. 22nd Int. Conf. Machine Learning (ICML '05)*, 2005, pp. 625–632, doi: 10.1145/1102351.1102430.

[18] S. R. Sihare, "Student dropout analysis in higher education and retention by artificial intelligence and machine learning," *SN Computer Science*, vol. 5, 2024, doi: 10.1007/s42979-023-02458-w.

[19] Ministry of Education, Government of India, "All India Survey on Higher Education (AISHE) 2021-22," released 25 Jan. 2024. [Online]. Available: https://www.pib.gov.in/PressReleasePage.aspx?PRID=1999713

[20] *The Digital Personal Data Protection Act, 2023* (India), Section 9.
