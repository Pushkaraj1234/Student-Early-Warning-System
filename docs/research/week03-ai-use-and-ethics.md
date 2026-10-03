# Week 3 — AI-assisted research, responsible AI and research ethics

Status 2026-10-03, first version. The team should complete §1 with every AI tool it used itself.

## 1. AI tools used in this project (disclosure)

| Tool | Used for | How the output was checked |
|---|---|---|
| Claude (Anthropic), as a coding and writing assistant (Claude Code) | Writing and reviewing code, tests and database migrations; drafting documentation; running the data analysis; searching for and checking literature | Automated tests (database 390 checks, ML 139, services 130, mobile 109), static analysis, the leakage guard, numbers copied from result files by scripts, every citation looked up (week 2) |
| Google Colab (team's own notebook) | Team's early XGBoost / LSTM experiments on an enrolment dataset | Re-run and audited — see §3, example 5 |
| *To be completed by the team* (e.g. ChatGPT, Gemini, Perplexity) | | |

Rule followed throughout: **AI output is a draft until it is verified against a primary source, a test, or the data.**
AI tools are not authors and are not cited as sources; the sources they point to are read and cited instead.

## 2. Prompting practices used

- Ask for **specific, checkable** output (a DOI, a table copied from a metrics file) rather than general summaries.
- Ask the tool to **separate what it verified from what it assumes**, and to say "not verified" instead of guessing.
- Give the tool the data or document and ask it to work from that, not from memory.
- Ask for **failure cases** (what would make this result wrong?) as well as the result.
- Never paste personal data of real people into an AI tool.

## 3. Hallucinations and errors caught in this project

Concrete examples, kept as evidence that verification is necessary:

1. **Invented finding attached to a real paper.** A search-engine summary of Hlosta et al. (2017) claimed the work cut
   drop-out "from 37% to 19%" at a Czech university. The paper's abstract says nothing of the kind; the claim was
   discarded.
2. **Wrong name.** A summary called the Open University's tool "Online University Analytics". Not used.
3. **Wrong count from memory.** The ML results write-up first said V2 added 13 features; the metrics file shows 16
   (21 → 37). Corrected before publishing.
4. **Unverified assumption.** A draft described a cited paper as having an Indian author; this could not be confirmed
   and was removed. The paper is listed as "not verified — read before citing".
5. **Misleading result in an experiment (team notebook).** The Colab notebook predicted an institution's *Grand
   Total* enrolment from columns that add up to it; a linear model scores R² = 1.000 because the target is a sum of
   the inputs. Once the leaking columns are removed, no feature is left. High R² was a property of the data, not
   evidence of a good model.
6. **Tool errors in code.** An automatic lint fix silently deleted an import that a later change still needed, and a
   variable name hid a function of the same name; both were caught by the type checker before anything ran.

## 4. Plagiarism and academic integrity

- All prose in the project documents is written for this project; quotations, if any, are marked and cited.
- Ideas and methods taken from papers are cited (IEEE style, week 2); datasets are cited with their licences.
- The final report and paper are checked with **Turnitin** (or the college's tool) before submission, and the
  similarity report is kept.
- AI-use disclosure for the paper (adapt to the venue's policy):

  > *The authors used Claude (Anthropic) to assist with software development, documentation drafts and checking
  > references. All AI-assisted output was reviewed, tested and verified against primary sources by the authors,
  > who take full responsibility for the content.*

## 5. Research ethics

| Topic | What the project does |
|---|---|
| Data provenance | Every number is labelled **benchmark** (OULAD, UK, CC BY 4.0 — attribution required), **synthetic** (generated; proves software only) or **institutional** (none yet). Synthetic results are never presented as model performance |
| Real student data | None used. Using it needs the institution's approval, an ethics review, a data-sharing agreement and a lawful basis under the DPDP Act 2023; children's data is out of scope (Section 9) |
| Third-party data | NSS 75th round: used only for descriptive context because no codebook or terms of use were supplied. The team's enrolment file: source and year not stated, so it is not used in SEWS |
| Privacy by design | Row-level security on every table; students see only their own data; models and reports contain no student identifiers (tested) |
| Fairness | Protected attributes are never model inputs; subgroup errors are audited and reported ([fairness.md](../ml/fairness.md)) |
| Human oversight | Every suggestion is reviewed by a mentor; the student can decline; models need a person's approval before use |
| Honest claims | No causal claims about interventions; benchmark results are not presented as evidence about Indian students |

## 6. Responsible AI in the product (summary)

Explanations are shown with every risk signal, written differently for students, mentors and administrators;
students see a risk level and its reasons, never a raw probability; models are versioned, monitored for drift and can
only reach production with institutional data, calibration evidence and a recorded approval
([institutional-training.md](../ml/institutional-training.md)).
