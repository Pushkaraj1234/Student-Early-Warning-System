# Database Design (implemented)

> Status: **IMPLEMENTED v1 (2026-09-24)** in `supabase/migrations/` and verified by 242 pgTAP assertions
> (`supabase/tests/database/`) on a local PostgreSQL 18 cluster that emulates Supabase's auth roles
> (`scripts/db/test-local.sh`). **Not yet applied to the hosted project** `rzekfmfuskknadrchkhg`;
> its existing schema has still not been inspected (see "Before applying to the hosted project").

## 1. Principles (unchanged)

Minimum data · RLS on every exposed table · deny by default · institution isolation ·
temporal correctness (`recorded_at` for as-of features) · immutable, versioned predictions ·
schema changes only through idempotent migrations.

## 2. Migrations

| File | Purpose |
|---|---|
| `20260924000100_foundation_private_schema.sql` | `private` schema (not exposed by the Data API), `set_updated_at` trigger |
| `20260924000200_institutions_and_profiles.sql` | institutions, departments, programmes, profiles; sign-up trigger (always creates a `student` profile — client-sent roles are ignored) |
| `20260924000300_students_courses_academics.sql` | students, courses, mentor_assignments, course_faculty, student_courses, academic_records, attendance_records, assignments, assignment_submissions, engagement_events |
| `20260924000400_risk_interventions_notifications_audit.sql` | risk_predictions, risk_factors, interventions, notifications, audit_logs |
| `20260924000500_authorization_helpers_and_integrity.sql` | SECURITY DEFINER scope helpers; stamping and validation triggers |
| `20260924000600_rls_policies_and_grants.sql` | column-level grants + one explicit policy per permitted operation |
| `20260924000700_audit_triggers.sql` | audit trail on sensitive tables (who / what / which columns — no row contents) |
| `20260924000800_rpc_functions.sql` | `claim_student_record`, `complete_onboarding`, `get_my_recommended_actions`, `admin_set_user_role` |

Every migration is applied **twice** by the test script to prove idempotency. Every table gets RLS
enabled and API privileges revoked in the same migration that creates it.

## 3. Tables (19)

The 17 required entities plus two **scope tables** that authorization needs:
`mentor_assignments` (mentor scope) and `course_faculty` (faculty scope).

| Area | Tables |
|---|---|
| Tenancy & identity | institutions, departments, programmes, profiles (`id` = `auth.users.id`) |
| Academic | students, courses, student_courses, academic_records, attendance_records, assignments, assignment_submissions, engagement_events |
| Scope | mentor_assignments, course_faculty |
| ML outputs | risk_predictions, risk_factors |
| Support | interventions, notifications |
| Governance | audit_logs |

All primary keys are UUIDs; all timestamps are `timestamptz`; controlled values use named CHECK
constraints (roles, statuses, risk levels, UGC grades `O, A+, A, B+, B, C, P, F, Ab`, provenance,
intervention types, …). `student_courses.grade_points` is generated from the grade. The exact column
list is exported to `supabase/types/schema_contract.json`.

## 4. Relationships and ON DELETE behaviour

| Relationship | ON DELETE | Why |
|---|---|---|
| departments/programmes/courses/students → institutions | RESTRICT | An accidental delete must not cascade through an institution |
| programmes → departments, students → programmes, courses → departments/programmes | RESTRICT (composite FK with `institution_id`) | Reference data; composite keys make cross-institution rows impossible |
| student_courses, academic_records, attendance_records, assignment_submissions, engagement_events, risk_predictions, interventions, mentor_assignments → students | CASCADE | An erasure request (service role only) removes all of a student's personal data |
| attendance_records → student_courses (`student_course_id, student_id, course_id`) | CASCADE | Attendance can exist only for a real enrolment |
| student_courses → courses, assignments → courses | RESTRICT | Courses with enrolments or assignments cannot vanish |
| risk_factors → risk_predictions | CASCADE | Factors belong to their prediction |
| interventions.prediction_id → risk_predictions | SET NULL | Keep the intervention history |
| profiles → auth.users | CASCADE | Account deletion |
| students.user_id, recorded_by, created_by, assigned_to → profiles | SET NULL | Records survive staff/account deletion |
| notifications → profiles | CASCADE | Personal to the recipient |
| audit_logs.actor_id / record_id | no FK (deliberate) | The audit trail must survive deletion of the actor or record |

## 5. Authorization model

- **Identity** comes only from `auth.uid()` (verified JWT). **Role and institution** come only from
  `public.profiles`. Clients cannot write `role`, `institution_id`, `user_id`, `recorded_by`,
  `created_by` or any scope column (column-level grants).
- New accounts are always `student`. A student account is linked to its institutional record only by
  `claim_student_record()`, which requires a **confirmed** email equal to `students.institutional_email`.
- Staff roles are set by the service role or by an institution admin via `admin_set_user_role()`
  (same institution only; not their own role; a linked student account cannot become staff).

### RLS summary (✓ = permitted; everything else is denied by default)

| Table | Student | Mentor (active assignment) | Faculty (courses taught) | Admin (own institution) | Service role |
|---|---|---|---|---|---|
| institutions | read own | read own | read own | read, rename | all |
| departments / programmes / courses | read (own inst.) | read | read | read, insert, update, delete | all |
| profiles | read, edit own name | own | own | read (inst.) | all |
| students | own row | mentees | students in their courses | read, insert, update | all (incl. delete/erasure) |
| mentor_assignments | own | own | — | all | all |
| course_faculty | — | — | own | read, insert, delete | all |
| student_courses | own | mentees | their courses: read, update marks/grade | all | all |
| academic_records (SGPA/CGPA) | own | mentees | — | all | all |
| attendance_records | own | mentees | their courses: read, insert, update | all | all |
| assignments | enrolled courses | mentees' courses | their courses: all | all | all |
| assignment_submissions | own | mentees | their courses: read, insert, update | all | all |
| engagement_events | own | mentees | — | read | write |
| risk_predictions / risk_factors | own (read) | mentees (read) | — | read | **write (only)** |
| interventions | via `get_my_recommended_actions()` only (no staff notes) | mentees: read, create (`source='mentor'`), update | — | all | all |
| notifications | own: read, mark read | own | own | own | write |
| audit_logs | — | — | — | read (inst.) | written by trigger |

`anon` has no privileges on any table or RPC.

## 6. Indexes

Required indexes (student_id, institution_id, programme_id, course_id, prediction_date, created_at,
attendance_date, assignment due dates, intervention status) exist — many as the leading column of a
unique constraint — and are asserted in `010_schema_and_privileges.sql`. FK indexes on rarely deleted
"who recorded this" columns were intentionally omitted.

## 7. Seed data

`supabase/seed.sql` — 100% synthetic ("SEWS Synthetic Institute (demo data)", students named
"Synthetic Student Alpha/Beta/Gamma", `@synthetic.example.com` emails). Demo risk predictions are
tagged `data_provenance='synthetic'` and model version `seed-demo-0`; they are fixtures, not model
output. Seed applies twice with identical row counts.

## 8. Testing workflow

```bash
bash scripts/db/test-local.sh              # fresh DB, migrations x2, seed, 10 pgTAP files
bash scripts/db/export-schema-contract.sh  # refresh supabase/types/schema_contract.json
```
The same pgTAP files run unchanged with `npx supabase test db` once Docker (or a linked project) is
available. A mutation check confirmed the suite fails when a policy is weakened.

## 9. Before applying to the hosted project

1. `npx supabase login` and `npx supabase link --project-ref rzekfmfuskknadrchkhg`.
2. `npx supabase migration list` and `npx supabase db pull` — **inspect the existing schema** and resolve
   any conflict (these migrations use `IF NOT EXISTS`, so a pre-existing table with a different shape
   would be silently kept — review first).
3. `npx supabase db push`, then run the pgTAP suite against the linked database.
4. Dashboard settings that migrations cannot set: enable email confirmation, password policy
   (8+ chars, upper/lower/digit), add `io.sews.app://login-callback` to redirect URLs.
5. Never load `seed.sql` into a project holding real data.

## 10. Known limitations

- Faculty scope is per course, not per course *term*: a faculty member assigned to a course sees all
  years of that course.
- Overlapping mentor assignments with end dates are not prevented (only one open-ended assignment per
  student is enforced).
- `recorded_at` is updated on every correction, so a corrected record is treated as "learned" at the
  correction time for as-of features (conservative for leakage).
- The local test harness emulates Supabase roles on PostgreSQL 18; hosted Supabase (PostgreSQL 15/17,
  non-superuser `postgres`) must still be verified with `supabase test db`.
