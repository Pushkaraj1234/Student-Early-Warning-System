# NSS 75th round (education) — context dataset

Status 2026-09-25. Module: `ml/context/nss75.py`. Tests: `ml/tests/test_nss75_profile.py`.
Latest profile: `ml/reports/nss75-profile-20260924T225037Z/` (aggregate counts only).

## What the dataset is

MoSPI unit-level microdata of the National Sample Survey, 75th round (2017-18), schedule 25.2
"Household Social Consumption: Education" (file prefix `R75252`). Supplied by the owner on 2026-09-25 in five
formats (CSV, JSON, SAS, Stata, SPSS). The files are kept where the owner placed them (`Downloads`); nothing is
copied into the repository.

| Block file | Content | Rows |
|---|---|---:|
| L01 | Blocks 1, 2, 11: sample household identification | 113,757 households |
| L02 | Block 3: household characteristics | 113,757 |
| L03 | Block 3.1: erstwhile members aged 3-35 attending education | 3,606 |
| L04 | Block 4: demographic particulars of household members | 513,366 persons |
| L05 | Block 5: persons aged 3-35 currently attending (basic course) | 152,992 |
| L06 | Block 6: education expenditure of persons attending pre-primary and above | 152,558 |
| L07 | Block 7: persons aged 3-35 currently not attending | 133,464 |
| L08 | Block 8: formal vocational/technical training, ages 12-59 | 6,610 |

This is genuine **Indian** data, but it is a **household survey of the general population**, not records of the
students of a higher-education institution.

## Owner decision (2026-09-25)

Use the survey as **descriptive context only**. It does not train, evaluate or calibrate any SEWS risk model.

Reasons (found by inspecting the files before any training):

1. **Different problem and data.** SEWS predicts a student's future risk from institutional records over time
   (attendance, submissions, grades, LMS activity at a cutoff date). The survey has none of these and no time
   dimension. A model trained on it could not score SEWS students: its features do not exist in the SEWS
   database, and the scoring job refuses any model whose feature version differs.
2. **Protected attributes.** Most of its explanatory variables are religion, social group, gender, disability and
   household consumption. SEWS does not use protected or sensitive variables as predictors.
3. **Built-in leakage.** The profile shows that the 286,456 persons aged 3-35 split exactly into block 5
   (attending, 152,992) and block 7 (not attending, 133,464) with no overlap and nobody missing, and block 6
   (expenditure) exists only for persons in block 5. Whether a person attends is therefore determined by which
   blocks hold their data; a model using those blocks would learn the survey's structure, not risk.
4. **No codebook.** Every value is a code (schedule 25.2 layout) and no codebook or layout document is
   available, so no code can be interpreted.
5. **Terms of use not supplied** with the files.

## What the profile establishes (without decoding anything)

- Every block has unique keys (households: `HHID`; persons: `HHID` + `Per_serialno`, `Person_serialno` in L03).
- Every household in blocks 2-8 exists in block 1, and every person in blocks 5-8 exists in block 4.
- The attending / not-attending partition described above is exact.
- The CSV and Stata deliveries have identical row counts for the seven blocks the Stata archive contains; the
  Stata archive lacks block 3 (L02). The JSON archive contains block 3 twice.
- Heavily missing columns are listed in the report, e.g. `enrolmt_3_35_yrs_status` is empty for 44.2 % of
  persons in block 4 (expected if it applies only to ages 3-35, but that cannot be confirmed without the codebook).

Not checked: the SAS files are XPORT **version 8**, which pandas cannot read; the SPSS files need `pyreadstat`
(not installed); the 1.1 GB JSON was not parsed. None of these is needed because the CSV is complete.

## What is deliberately not produced

- **No weighted estimates.** The files carry `MULT`, `MULT_SubSample` and `MULT_Combined`; which one gives
  combined population estimates is defined in the survey documentation, which is not available.
- **No labelled statistics.** Code frequencies are reported raw (`undecoded_code_counts` in `profile.json`).
- **No identifiers or fine geography** in any output: household ids, person serials, district and lower-level
  geography, dates, staff codes and weights are never listed.

## What would unlock more

| Needed | Enables |
|---|---|
| Schedule 25.2 codebook / data layout (MoSPI) | labelled statistics, e.g. attendance status and main reasons for not attending, by state, sector and level |
| Survey documentation on multipliers | weighted, population-level estimates with correct standard errors (stratified multi-stage design) |
| MoSPI terms of use for this release | confirmation that derived tables may be published in SEWS documentation |

Even with all three, the survey stays context (for example, typical reasons for discontinuing education to inform
support options). It does not replace institutional student data for the SEWS risk model.

## Re-running

```bash
ml/.venv/Scripts/python -m ml.context.nss75 --csv-zip "C:/Users/Asus/Downloads/Data_in_CSV.zip" \
    --stata-zip "C:/Users/Asus/Downloads/Data_in_STATA.zip" --out ml/reports
```
