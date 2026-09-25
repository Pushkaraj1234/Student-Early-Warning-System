# NSS 75th round, schedule 25.2 — code-agnostic profile (2026-09-24T22:50:37+00:00)

> **Descriptive context only. Not used to train or evaluate any SEWS model.** Source: MoSPI unit-level microdata, India, 2017-18. No codebook was available: code values below are **undecoded** and survey weights are **not applied**, so none of these counts is a population estimate.

| Block | Content | Rows | Columns | Duplicate keys |
|---|---|---:|---:|---:|
| L01 | Blocks 1, 2 and 11: identification of sample household | 113757 | 41 | 0 |
| L02 | Block 3: household characteristics | 113757 | 44 | 0 |
| L03 | Block 3.1: erstwhile members aged 3-35 currently attending education | 3606 | 36 | 0 |
| L04 | Block 4: demographic particulars of household members | 513366 | 42 | 0 |
| L05 | Block 5: persons aged 3-35 currently attending (basic course) | 152992 | 58 | 0 |
| L06 | Block 6: expenditure of persons currently attending pre-primary and above | 152558 | 41 | 0 |
| L07 | Block 7: persons aged 3-35 currently not attending | 133464 | 39 | 0 |
| L08 | Block 8: formal vocational/technical training, persons aged 12-59 | 6610 | 33 | 0 |

## Linkage

- Blocks missing from the delivery: none
- households not in L01: {'L02': 0, 'L03': 0, 'L04': 0, 'L05': 0, 'L06': 0, 'L07': 0, 'L08': 0}
- persons not in L04: {'L05': 0, 'L06': 0, 'L07': 0, 'L08': 0}
- block 6 persons not in block 5: 0
- Persons aged 3-35 in block 4: 286456 — attending only (block 5): 152992; not attending only (block 7): 133464; both: 0; neither: 0

## Row counts vs Stata (.dta)

| Block | CSV | Other | Match |
|---|---:|---:|---|
| L01 | 113757 | 113757 | yes |
| L02 | 113757 | None | NO |
| L03 | 3606 | 3606 | yes |
| L04 | 513366 | 513366 | yes |
| L05 | 152992 | 152992 | yes |
| L06 | 152558 | 152558 | yes |
| L07 | 133464 | 133464 | yes |
| L08 | 6610 | 6610 | yes |

## Columns with the most missing values (share of rows)

- L01: Substitution_Code 97.7%, Employee_code2 96.9%, Employee_code 47.9%, Employee_code1 16.2%, Dispatch_date 0.2%
- L02: Location_State_ut 98.9%, Location_district 98.9%, Location_sector 98.9%, Hostel 98.0%, NIC_2008_5d_code 8.7%
- L03: Exp_inccurred_current_acdemic_am 10.5%, Present_resid_district_code 1.8%, Current_enrolmt_basic_course 0.4%, FOD_Sub_Region 0.1%, Present_resid_sector 0.0%
- L04: Disability_type 98.7%, Edu_completed_inYrs 81.5%, enrolmt_3_35_yrs_status 44.2%, Per_12_59yrs_voca_tech_training 24.9%, Completed_class_grade 22.9%
- L05: Disbty_attnd_special_school 96.3%, Tution_fee_waived_amt 95.6%, Pvt_insttn_reason2 90.7%, Nature_institution 86.2%, Reimbursement_agency 84.6%
- L06: Economic_activity_status 98.1%, Source_funding_second_exp 85.9%, Exp_prep_higher_studies_amt 65.8%, Exp_other_course_amt 65.2%, Private_coaching_amt 57.9%
- L07: Exp_preparation_amt 97.8%, Last_attended_12_grade 39.5%, Age_last_enrolld 21.5%, Level_enrolment 20.9%, Course_type 20.9%
- L08: FOD_Sub_Region 0.1%

Raw (undecoded) code frequencies per column are in `profile.json` under `undecoded_code_counts`.
