-- ============================================================================
-- SEWS development seed — 100% SYNTHETIC DATA.
-- No real person, institution or student record is represented here. Names are
-- labelled "Synthetic", emails use the reserved example.com domain, and every
-- risk prediction is tagged data_provenance = 'synthetic' with a 'seed-demo'
-- model version: they are demo fixtures, NOT model output.
--
-- Local development only (applied by `supabase db reset` and scripts/db/test-local.sh).
-- Never load into a production project.
--
-- To try the student app locally: sign up with one of the student emails below
-- (e.g. student.beta@synthetic.example.com), confirm the email, and complete
-- onboarding — the account is then linked to that synthetic record.
--
-- Dates are relative to the day the seed runs so the demo always looks current.
-- Idempotent: fixed/derived UUIDs + ON CONFLICT DO NOTHING.
-- ============================================================================

-- Development database only: allows the synthetic demo model (status 'development') to create
-- predictions. Production databases never set this (docs/architecture/environments.md).
set sews.environment = 'development';

-- ------------------------------------------------------------ reference data
insert into public.institutions (id, code, name) values
  ('a0000000-0000-4000-8000-000000000001', 'SYNTH', 'SEWS Synthetic Institute (demo data)')
on conflict do nothing;

insert into public.departments (id, institution_id, code, name) values
  ('a0000000-0000-4000-8000-000000000011', 'a0000000-0000-4000-8000-000000000001', 'CSE', 'Synthetic Department of Computing'),
  ('a0000000-0000-4000-8000-000000000012', 'a0000000-0000-4000-8000-000000000001', 'MATH', 'Synthetic Department of Mathematics')
on conflict do nothing;

insert into public.programmes (id, institution_id, department_id, code, name, degree_level, duration_semesters) values
  ('a0000000-0000-4000-8000-000000000021', 'a0000000-0000-4000-8000-000000000001',
   'a0000000-0000-4000-8000-000000000011', 'BTECH-CS', 'B.Tech Computing (synthetic)', 'undergraduate', 8)
on conflict do nothing;

insert into public.courses (id, institution_id, department_id, programme_id, code, title, credits, semester_number) values
  ('a0000000-0000-4000-8000-000000000031', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000011',
   'a0000000-0000-4000-8000-000000000021', 'SYN-CS201', 'Data Structures (synthetic)', 4, 3),
  ('a0000000-0000-4000-8000-000000000032', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000011',
   'a0000000-0000-4000-8000-000000000021', 'SYN-CS202', 'Digital Logic (synthetic)', 3, 3),
  ('a0000000-0000-4000-8000-000000000033', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000012',
   'a0000000-0000-4000-8000-000000000021', 'SYN-MA201', 'Discrete Mathematics (synthetic)', 4, 3),
  ('a0000000-0000-4000-8000-000000000034', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000011',
   'a0000000-0000-4000-8000-000000000021', 'SYN-CS102', 'Programming Fundamentals (synthetic)', 4, 2),
  ('a0000000-0000-4000-8000-000000000035', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000012',
   'a0000000-0000-4000-8000-000000000021', 'SYN-MA102', 'Calculus (synthetic)', 4, 2)
on conflict do nothing;

-- ------------------------------------------------------------------ students
insert into public.students (id, institution_id, programme_id, roll_number, full_name,
                             institutional_email, admission_year, current_semester, status) values
  ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000021',
   'SYN2025001', 'Synthetic Student Alpha', 'student.alpha@synthetic.example.com', 2025, 3, 'active'),
  ('a0000000-0000-4000-8000-000000000042', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000021',
   'SYN2025002', 'Synthetic Student Beta', 'student.beta@synthetic.example.com', 2025, 3, 'active'),
  ('a0000000-0000-4000-8000-000000000043', 'a0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000021',
   'SYN2025003', 'Synthetic Student Gamma', 'student.gamma@synthetic.example.com', 2025, 3, 'active')
on conflict do nothing;

-- ---------------------------------------------------- past semester results
insert into public.student_courses (id, institution_id, student_id, course_id, academic_year, semester,
                                    status, marks, grade, result_published_at)
select md5('seed-sc-' || v.student_id || v.course_id)::uuid,
       'a0000000-0000-4000-8000-000000000001', v.student_id::uuid, v.course_id::uuid,
       '2025-26', 2, 'completed', v.marks, v.grade, now() - interval '100 days'
from (values
  ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000034', 91.00, 'O'),
  ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000035', 84.00, 'A+'),
  ('a0000000-0000-4000-8000-000000000042', 'a0000000-0000-4000-8000-000000000034', 58.00, 'B'),
  ('a0000000-0000-4000-8000-000000000042', 'a0000000-0000-4000-8000-000000000035', 35.00, 'F'),
  ('a0000000-0000-4000-8000-000000000043', 'a0000000-0000-4000-8000-000000000034', 72.00, 'A'),
  ('a0000000-0000-4000-8000-000000000043', 'a0000000-0000-4000-8000-000000000035', 66.00, 'B+')
) as v (student_id, course_id, marks, grade)
on conflict do nothing;

insert into public.academic_records (id, student_id, academic_year, semester, sgpa, cgpa,
                                     credits_registered, credits_earned, result_status, published_at)
select md5('seed-ar-' || v.student_id || v.semester)::uuid, v.student_id::uuid, '2025-26', v.semester,
       v.sgpa, v.cgpa, 20, v.earned, v.result_status, now() - interval '100 days' * (3 - v.semester)
from (values
  ('a0000000-0000-4000-8000-000000000041', 1, 8.40, 8.40, 20.0, 'pass'),
  ('a0000000-0000-4000-8000-000000000041', 2, 8.70, 8.55, 20.0, 'pass'),
  ('a0000000-0000-4000-8000-000000000042', 1, 6.20, 6.20, 20.0, 'pass'),
  ('a0000000-0000-4000-8000-000000000042', 2, 5.40, 5.80, 16.0, 'fail'),
  ('a0000000-0000-4000-8000-000000000043', 1, 7.10, 7.10, 20.0, 'pass'),
  ('a0000000-0000-4000-8000-000000000043', 2, 6.90, 7.00, 20.0, 'pass')
) as v (student_id, semester, sgpa, cgpa, earned, result_status)
on conflict do nothing;

-- -------------------------------------------------- current semester enrolment
insert into public.student_courses (id, institution_id, student_id, course_id, academic_year, semester, status)
select md5('seed-sc-' || s.id || c.id)::uuid, s.institution_id, s.id, c.id, '2026-27', 3, 'enrolled'
from public.students s
cross join public.courses c
where s.id in ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000042',
               'a0000000-0000-4000-8000-000000000043')
  and c.id in ('a0000000-0000-4000-8000-000000000031', 'a0000000-0000-4000-8000-000000000032',
               'a0000000-0000-4000-8000-000000000033')
on conflict do nothing;

-- ---------------------------------------------------------------- attendance
-- Weekdays over the last six weeks. Alpha attends ~93%, Gamma ~82%, Beta declines
-- from ~85% to ~50% (a deliberately visible synthetic trend).
insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date, session_number, status)
select sc.id, sc.student_id, sc.course_id, d.day, 1,
       case
         when h.pct >= 97 then 'excused'
         when h.pct < (case sc.student_id
                         when 'a0000000-0000-4000-8000-000000000041' then 93
                         when 'a0000000-0000-4000-8000-000000000043' then 82
                         else 85 - (d.day - (current_date - 42)) * 0.8
                       end) then 'present'
         else 'absent'
       end
from public.student_courses sc
cross join lateral (
  select g::date as day
  from generate_series(current_date - 42, current_date - 1, interval '1 day') as g
  where extract(isodow from g) < 6
) as d
cross join lateral (select abs(hashtext(sc.id::text || d.day::text)) % 100 as pct) as h
where sc.academic_year = '2026-27'
  and sc.student_id in ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000042',
                        'a0000000-0000-4000-8000-000000000043')
on conflict do nothing;

-- ---------------------------------------------------------------- assignments
insert into public.assignments (id, institution_id, course_id, academic_year, title, max_score, due_at)
select md5('seed-as-' || c.id || o.n)::uuid, c.institution_id, c.id, '2026-27',
       'Synthetic assignment ' || o.n, 20, (current_date + o.offset_days)::timestamptz + interval '18 hours'
from public.courses c
cross join (values (1, -21), (2, -7), (3, 7)) as o (n, offset_days)
where c.id in ('a0000000-0000-4000-8000-000000000031', 'a0000000-0000-4000-8000-000000000032',
               'a0000000-0000-4000-8000-000000000033')
on conflict do nothing;

-- Past-due assignments only. Alpha: on time, high scores. Gamma: on time, one late.
-- Beta: first late with a low score, second missing.
insert into public.assignment_submissions (assignment_id, student_id, status, submitted_at, score, graded_at)
select a.id, s.id, v.status,
       case when v.status in ('submitted', 'late') then a.due_at + v.submit_offset end,
       v.score,
       case when v.score is not null then a.due_at + interval '3 days' end
from public.assignments a
join public.students s on s.id in ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000042',
                                   'a0000000-0000-4000-8000-000000000043')
cross join lateral (
  select case
           when s.id = 'a0000000-0000-4000-8000-000000000041' then 'submitted'
           when s.id = 'a0000000-0000-4000-8000-000000000043' and a.title like '% 2' then 'late'
           when s.id = 'a0000000-0000-4000-8000-000000000043' then 'submitted'
           when a.title like '% 1' then 'late'
           else 'missing'
         end as status,
         case
           when s.id = 'a0000000-0000-4000-8000-000000000041' then 18.0
           when s.id = 'a0000000-0000-4000-8000-000000000043' then 14.5
           when a.title like '% 1' then 9.0
         end as score,
         case
           when s.id = 'a0000000-0000-4000-8000-000000000041' then interval '-1 day'
           when s.id = 'a0000000-0000-4000-8000-000000000043' and a.title like '% 2' then interval '2 days'
           when s.id = 'a0000000-0000-4000-8000-000000000043' then interval '-2 hours'
           else interval '3 days'
         end as submit_offset
) as v
where a.academic_year = '2026-27' and a.due_at < now()
on conflict do nothing;

-- ---------------------------------------------------------- engagement events
insert into public.engagement_events (id, student_id, course_id, event_type, event_count, source, occurred_at)
select md5('seed-ee-' || s.id || d.day)::uuid, s.id, null,
       (array['lms_login', 'resource_view', 'quiz_attempt', 'forum_activity'])[1 + abs(hashtext('type' || s.id::text || d.day::text)) % 4],
       1 + abs(hashtext(s.id::text || d.day::text)) % 4,
       'lms', d.day::timestamptz + interval '10 hours'
from public.students s
cross join lateral (
  select g::date as day from generate_series(current_date - 30, current_date - 1, interval '1 day') as g
) as d
where s.id in ('a0000000-0000-4000-8000-000000000041', 'a0000000-0000-4000-8000-000000000042',
               'a0000000-0000-4000-8000-000000000043')
  and abs(hashtext('active' || s.id::text || d.day::text)) % 100 <
      case s.id
        when 'a0000000-0000-4000-8000-000000000041' then 85
        when 'a0000000-0000-4000-8000-000000000043' then 60
        else 70 - (d.day - (current_date - 30)) * 1.8
      end
on conflict do nothing;

-- --------------------------------------------- demo risk predictions (SYNTHETIC)
insert into public.model_registry (id, model_name, version, target, dataset_version, feature_version,
                                   data_provenance, training_timestamp)
values ('a0000000-0000-4000-8000-000000000061', 'seed-demo', 'seed-demo-0', 'academic', 'seed-synthetic-0',
        'seed-demo-0', 'synthetic', timestamptz '2026-09-01 00:00+00')
on conflict do nothing;

-- Listed oldest first: the trajectory trigger compares each prediction with the previous one.
insert into public.risk_predictions (id, student_id, prediction_date, risk_probability, risk_level,
                                     model_version, feature_version, dataset_version, data_provenance,
                                     model_registry_id)
select md5('seed-rp-' || v.student_id || v.days_ago)::uuid, v.student_id::uuid, current_date - v.days_ago,
       v.probability, v.risk_level, 'seed-demo-0', 'seed-demo-0', 'seed-synthetic-0', 'synthetic',
       'a0000000-0000-4000-8000-000000000061'
from (values
  ('a0000000-0000-4000-8000-000000000041', 28, 0.08, 'stable'),
  ('a0000000-0000-4000-8000-000000000041', 14, 0.07, 'stable'),
  ('a0000000-0000-4000-8000-000000000041', 0, 0.06, 'stable'),
  ('a0000000-0000-4000-8000-000000000042', 28, 0.35, 'watch'),
  ('a0000000-0000-4000-8000-000000000042', 14, 0.55, 'elevated'),
  ('a0000000-0000-4000-8000-000000000042', 0, 0.74, 'high'),
  ('a0000000-0000-4000-8000-000000000043', 28, 0.30, 'watch'),
  ('a0000000-0000-4000-8000-000000000043', 14, 0.28, 'watch'),
  ('a0000000-0000-4000-8000-000000000043', 0, 0.32, 'watch')
) as v (student_id, days_ago, probability, risk_level)
on conflict do nothing;

insert into public.risk_factors (prediction_id, rank, feature, feature_value, contribution, direction)
select md5('seed-rp-' || v.student_id || 0)::uuid, v.rank, v.feature, v.feature_value, v.contribution, v.direction
from (values
  ('a0000000-0000-4000-8000-000000000041', 1, 'attendance_rate_last_14d', 0.93, -0.42, 'decreases_risk'),
  ('a0000000-0000-4000-8000-000000000041', 2, 'mean_released_score_pct', 90.0, -0.35, 'decreases_risk'),
  ('a0000000-0000-4000-8000-000000000041', 3, 'missed_submission_rate', 0.0, -0.12, 'decreases_risk'),
  ('a0000000-0000-4000-8000-000000000042', 1, 'attendance_rate_last_14d', 0.52, 0.61, 'increases_risk'),
  ('a0000000-0000-4000-8000-000000000042', 2, 'missed_submission_rate', 0.50, 0.44, 'increases_risk'),
  ('a0000000-0000-4000-8000-000000000042', 3, 'engagement_active_days_14d', 3, 0.21, 'increases_risk'),
  ('a0000000-0000-4000-8000-000000000043', 1, 'late_submission_rate', 0.33, 0.18, 'increases_risk'),
  ('a0000000-0000-4000-8000-000000000043', 2, 'attendance_rate_last_14d', 0.82, -0.09, 'decreases_risk'),
  ('a0000000-0000-4000-8000-000000000043', 3, 'mean_released_score_pct', 72.5, -0.05, 'decreases_risk')
) as v (student_id, rank, feature, feature_value, contribution, direction)
on conflict do nothing;

-- ----------------------------------------------------------- interventions
-- Unreviewed rule-engine recommendations (status 'recommended'): students see them only after
-- a mentor approves them. Rule ids, reasons and priorities are what rules-1.0.0
-- (services/sews_services/recommendations/engine.py) produces for Beta's seeded data: 14-day
-- attendance 52% (< 60%: high) and a high academic estimate. Only the risk rule links a prediction.
insert into public.interventions (id, student_id, prediction_id, intervention_type, status, source, due_on, reason,
                                  priority, rule_id, rule_version)
select md5('seed-iv-' || v.student_id || v.intervention_type)::uuid, v.student_id::uuid,
       case when v.links_prediction then md5('seed-rp-' || v.student_id || 0)::uuid end,
       v.intervention_type, 'recommended', 'model_rule', current_date + v.due_in_days, v.reason, v.priority,
       v.rule_id, 'rules-1.0.0'
from (values
  ('a0000000-0000-4000-8000-000000000042', 'attendance_follow_up', 7,
   'Attendance in the last 14 days was 52%, below the 75% requirement.', 'high', 'attendance.below_requirement', false),
  ('a0000000-0000-4000-8000-000000000042', 'mentor_meeting', 10,
   'The academic early-warning estimate is high.', 'high', 'risk.high_or_rising', true)
) as v (student_id, intervention_type, due_in_days, reason, priority, rule_id, links_prediction)
on conflict do nothing;

-- Academic terms (odd/even semesters) and a synthetic LMS integration.
insert into public.academic_terms (institution_id, academic_year, term, starts_on, ends_on) values
  ('a0000000-0000-4000-8000-000000000001', '2025-26', 'odd', date '2025-07-21', date '2025-12-05'),
  ('a0000000-0000-4000-8000-000000000001', '2025-26', 'even', date '2026-01-05', date '2026-05-15'),
  ('a0000000-0000-4000-8000-000000000001', '2026-27', 'odd', date '2026-07-20', date '2026-12-04')
on conflict do nothing;

insert into public.lms_integrations (id, institution_id, provider, display_name) values
  ('a0000000-0000-4000-8000-000000000051', 'a0000000-0000-4000-8000-000000000001', 'csv_import', 'Synthetic LMS export')
on conflict do nothing;
