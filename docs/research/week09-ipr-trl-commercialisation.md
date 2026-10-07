# Week 9 — Patent search, prior art, technology readiness and commercialisation

Status 2026-10-08. Search done on 2026-10-08 with Google Patents and web search; every patent listed in §2 was
opened on Google Patents and its title, owner, dates and status read from that page. **This is a student
research exercise, not legal advice.** A patent attorney/agent must do the formal search and opinion before any
filing or commercial launch.

## 1. Which kinds of IP apply to SEWS (India)

| Type | Law | Fits SEWS? | Note |
|---|---|---|---|
| Patent | Patents Act, 1970 | **Doubtful** (§3) | Section 3(k) excludes "a mathematical or business method or a computer programme *per se* or algorithms". The revised *Guidelines for Examination of Computer Related Inventions* (CGPDTM, final 2025; draft 25 March 2025) allow AI/ML inventions only when they show a **technical effect** (e.g. faster processing, better device control); business/administrative methods remain excluded [CRI-2025] |
| Copyright | Copyright Act, 1957 | **Yes** | Source code and documentation are literary works; protection is automatic. Registration with the Copyright Office is optional but gives evidence of authorship |
| Trademark | Trade Marks Act, 1999 | Possible | For the product name, after a clearance search (software/SaaS classes 9 and 42) on the IP India public search — **not done yet (team)** |
| Trade secret / confidentiality | Contract law | Yes | Trained institutional models and data stay inside each institution anyway (in-app training) |
| Licence | — | **Missing** | The repository has no LICENSE file: by default all rights are reserved. Decide proprietary vs open source (§6) |

The GitHub repository is **private** (checked 2026-10-08), so the code itself has not been published. The team's
paper, poster and viva will be public disclosures; India has no general grace period for an applicant's own
publication, so **if a patent is ever wanted, file before publishing**.

## 2. Prior-art search

**Method.** Databases: Google Patents (US, EP, WO, IN), web search for Indian published applications; WIPO
PATENTSCOPE and the Indian InPASS database should be searched by the team (they need interactive use).
Keywords: *student retention, at-risk student, early alert, dropout prediction, persistence model, learning
analytics, intervention*. Relevant classes: CPC **G06Q 50/20** (education services), **G09B** (educational
appliances), **G06N 20/00** (machine learning), **G06Q 10/04** (forecasting).

**Patents found and verified** (status as shown on Google Patents, 2026-10-08):

| Document | Owner | Priority | Status | What it claims | Overlap with SEWS | Difference |
|---|---|---|---|---|---|---|
| US 8,472,862 B2 "Method for improving student retention rates" | Starfish Retention Solutions → **EAB Global** | 2008-07-08 | **Active**, to 2032-04-07 | Networked suite that automatically raises flags for at-risk students from academic systems, plus manual flags and scheduling/tracking between students and providers | Alerts, mentor workflow, intervention tracking | SEWS uses calibrated ML risk estimates with explanations, fairness audits, consent and per-institution training; no appointment scheduling |
| US 10,460,245 B2 "Flexible, personalized student success modeling…" | **Civitas Learning** | 2015-09-04 | **Active**, to 2037-09-19 | Converts units of academic progress into Markov-model states and builds persistence models for complex term structures | Persistence (dropout) prediction | SEWS does not use Markov state models over progress units; it uses as-of features at decision points/weeks |
| US 9,779,084 B2 "Online classroom analytics system and methods" | Mattersight | 2013-10-04 | **Active**, to 2033-10-04 | Linguistic analysis of student communications to score metrics and predict academic outcomes | Outcome prediction | SEWS analyses no text or speech |
| US 2017/0256172 A1 "Student data-to-insight-to-action-to-learning analytics system" | Civitas Learning | 2016-03-04 | Abandoned | Action knowledge base, success predictions, rule-triggered interventions, multi-level impact analysis | Interventions and measuring their outcomes | Abandoned: now free prior art |
| US 2015/0193699 A1 "Data-adaptive insight and action platform for higher education" | Civitas Learning | 2014-01-08 | Abandoned | Segments students by data availability, builds predictive models from SIS/LMS data for interventions | Predictive models from student systems | Abandoned: free prior art |
| US 2014/0205990 A1 "Machine learning for student engagement" | PurePredictive (orig. Cloudvu) | 2013-01-24 | Abandoned | Learning-pattern archetypes from interaction behaviour (mouse movement, time on page) to measure engagement | Engagement from platform logs | Abandoned: free prior art |

Indian application found but **not verified** by us: 202441050998, "Machine learning approaches for automating
student performance predictions for enhancing university education system", published 12 July 2024 (journal
28/2024) according to the institution hosting a copy. Confirm on InPASS before citing.

**Non-patent prior art** (already in the [week 2 review](week02-literature-review.md)): Purdue Course Signals
(Arnold & Pistilli 2012), OU Analyse at the Open University (Kuzilek 2017; Hlosta 2017), and the **Moodle LMS
built-in model "Students at risk of dropping out"** (GPL open source, Community-of-Inquiry engagement indicators)
— early warning from learning-platform data is long established and freely available.

## 3. Patentability of SEWS (our assessment)

| Requirement | Assessment |
|---|---|
| Novelty | The core idea — predict at-risk students from academic and engagement data, alert a mentor, track interventions — is anticipated by §2 (some of it since 2008). |
| Inventive step | Our specific techniques (as-of feature reconstruction with a leakage guard, event-time replay of history, per-institution training with an approval gate, alert smoothing) are careful engineering of known methods; a skilled person would likely find them obvious. |
| Section 3(k) | A risk-prediction method for an educational/administrative purpose is likely to be treated as an algorithm or business method without the technical effect the 2025 guidelines require. |

**Conclusion: a patent is not recommended.** Protect SEWS through copyright (automatic; optionally registered),
a clear licence, a trademark for the name after a clearance search, and publication of the method (the paper),
which also acts as a defensive publication against others patenting the same ideas.

**Freedom to operate.** The active patents above are US patents and are enforceable only in the US. We found no
Indian counterpart in this search (not exhaustive). Before selling in the US, a professional freedom-to-operate
opinion is needed — especially against US 8,472,862 (automated at-risk flags and student–provider tracking).

## 4. Technology readiness level (TRL)

Definitions follow the standard nine-level TRL scale (as used by NASA, the EU Horizon programme and Indian funding
agencies).

| TRL | Meaning | SEWS evidence | Status |
|---|---|---|---|
| 1 | Basic principles observed | Literature review, problem definition (weeks 1–2) | done |
| 2 | Technology concept formulated | Architecture, data contract, research questions | done |
| 3 | Experimental proof of concept | Models on OULAD; 10 pre-registered tests supported (week 6) | done |
| 4 | Validated in a lab environment | Integrated system on a hosted **testing** project with synthetic users: app/website, database with row-level security, batch jobs, in-app training; models validated out of time on OULAD and on two external datasets; 426 automated tests and 390 database checks | **current level** |
| 5 | Validated in a relevant environment | Retrospective validation on one Indian institution's real, anonymised past terms (in-app training, approval workflow) | next — needs ethics approval and a data-sharing agreement |
| 6 | Demonstrated in a relevant environment | One-semester shadow pilot: predictions produced weekly, mentors review them, outcomes compared | planned |
| 7 | Prototype demonstrated in an operational environment | Live pilot across departments with mentors acting on alerts; mentor questionnaire (week 4) | planned |
| 8 | System complete and qualified | Production project, security audit, DPDP Act compliance review, SMTP, backups, monitoring | planned |
| 9 | Proven in operation | Several institutions using it over multiple terms | — |

**SEWS is at TRL 4.** It cannot claim TRL 5 until it has run on real institutional data.

## 5. Commercialisation

**Market (India).** AISHE 2021-22 registered **1,168 universities, 45,473 colleges and 12,002 standalone
institutions**, with about **4.33 crore students** [MoE-AISHE]. NAAC accreditation assesses student support and
progression (Criterion V), which gives institutions a reason to track and support students systematically.

**Who pays and how** (options, not decided):

| Model | How | Fits |
|---|---|---|
| SaaS subscription | Per enrolled student per year, hosted | Private colleges and universities |
| Institutional licence + support | One-time or annual fee, institution's own cloud | Universities with IT teams and strict data-residency rules |
| Open core | Free core (open source), paid hosting, training, support | Government colleges; faster adoption |
| Grants / incubation | Pilot funding through the college's incubator | Reaching TRL 5–7 |

**Competition.** EAB Navigate (includes Starfish) and Civitas Learning (US vendors with patents above); learning
platforms with built-in models (Moodle's free "Students at risk of dropping out"); student-information/ERP systems
with dashboards. **SEWS's differences:** India-specific signals (attendance, internal assessments, backlogs),
mentor workflow with consent and intervention outcomes, explanations for students and mentors, fairness audits,
per-institution training with an approval gate, privacy by design for the DPDP Act, and a low-cost stack that runs
as an app and a website.

**SWOT**

| Strengths | Weaknesses |
|---|---|
| Working end-to-end system; evidence-based evaluation; fairness and privacy built in; low running cost | No real Indian data yet (TRL 4); benchmark results only; small team |
| **Opportunities** | **Threats** |
| Large market; NEP 2020 / NAAC focus on student outcomes; colleges' existing attendance and marks data | Data-protection obligations (DPDP Act 2023, consent, children's data under section 9); harm from false alarms or bias; incumbents and free LMS tools; mentor workload |

**Route to market.** Pilot at the team's own college (TRL 5–6) → case study and the paper → incubator support →
2–3 paying pilot institutions (TRL 7) → production hardening (TRL 8).

## 6. Actions

| Action | Who |
|---|---|
| Decide the licence (proprietary vs open source) and add a LICENSE file | team + guide |
| Trademark clearance search for the product name (classes 9, 42) on IP India public search | team |
| Search InPASS and WIPO PATENTSCOPE with the keywords and classes in §2; confirm 202441050998 | team |
| Do not file a patent; if the guide disagrees, consult a patent agent **before** the paper is published | guide |
| Plan the TRL 5 pilot: ethics approval, data-sharing agreement, DPDP Act basis | team + college |

## 7. References

- [CRI-2025] Office of the CGPDTM, *Guidelines for Examination of Computer Related Inventions (CRIs) 2025*
  (draft 25 March 2025; final 2025). Summaries: EU IP Helpdesk, 5 Aug 2025; Bar & Bench, "Revised CRI Guidelines
  2025". Read the official text on ipindia.gov.in before citing details.
- Patents Act, 1970, section 3(k); Copyright Act, 1957; Trade Marks Act, 1999 (Government of India).
- US 8,472,862 B2; US 10,460,245 B2; US 9,779,084 B2; US 2017/0256172 A1; US 2015/0193699 A1;
  US 2014/0205990 A1 — Google Patents, accessed 2026-10-08.
- [MoE-AISHE] Ministry of Education, *All India Survey on Higher Education 2021-22* (released 25 January 2024).
- Moodle documentation, "Analytics" (built-in model "Students at risk of dropping out"), accessed 2026-10-08.
