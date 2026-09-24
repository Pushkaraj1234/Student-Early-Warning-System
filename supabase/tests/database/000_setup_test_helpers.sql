-- Installs test helpers used by every other test file. Runs first (file order) and
-- COMMITS so later files can use the helpers; 999_teardown drops them again.
-- Every other test file runs inside BEGIN … ROLLBACK, so fixtures never persist.
begin;

create extension if not exists pgtap with schema extensions;

create schema if not exists tests;

-- Deterministic, readable test identifiers: tests.uid('student_s1').
create or replace function tests.uid(p_key text)
returns uuid
language sql
immutable
as $$
  select md5('sews-test:' || p_key)::uuid;
$$;

create or replace function tests.create_user(p_id uuid, p_email text, p_confirmed boolean default true,
                                             p_metadata jsonb default '{}'::jsonb)
returns uuid
language plpgsql
as $$
begin
  insert into auth.users (id, email, email_confirmed_at, raw_user_meta_data, raw_app_meta_data, aud, role)
  values (p_id, p_email, case when p_confirmed then now() end, p_metadata, '{}'::jsonb,
          'authenticated', 'authenticated');
  return p_id;
end;
$$;

-- Switch the current transaction to the `authenticated` API role with a JWT for p_user_id.
create or replace function tests.authenticate_as(p_user_id uuid)
returns void
language plpgsql
as $$
begin
  perform set_config('request.jwt.claims',
                     json_build_object('sub', p_user_id::text, 'role', 'authenticated')::text, true);
  perform set_config('role', 'authenticated', true);
end;
$$;

create or replace function tests.authenticate_as_anon()
returns void
language plpgsql
as $$
begin
  perform set_config('request.jwt.claims', json_build_object('role', 'anon')::text, true);
  perform set_config('role', 'anon', true);
end;
$$;

create or replace function tests.clear_authentication()
returns void
language plpgsql
as $$
begin
  perform set_config('role', session_user::text, true);
  perform set_config('request.jwt.claims', '', true);
end;
$$;

-- Runs a DML statement as the CURRENT role (so RLS applies) and returns the number of
-- rows it affected. RLS silently filters UPDATE/DELETE targets, so "0 rows" is the
-- observable result of a denied UPDATE/DELETE on rows the caller cannot see.
create or replace function tests.affected_rows(p_sql text)
returns integer
language plpgsql
as $$
declare
  v_count integer;
begin
  execute p_sql;
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- Two institutions with one user per role in each, plus records for every table.
--   Institution A: students S1 (claimed), S2 (claimed), S4 (unclaimed, email of the
--                  unconfirmed user_s4); mentor M1 (mentors S1 only); faculty F1
--                  (teaches course A1 only); admin A1.
--   Institution B: student S3; mentor M2 (mentors S3); faculty F2 (course B1); admin A2.
--   Enrolments: S1 → A1, A2;  S2 → A2;  S3 → B1.
create or replace function tests.create_fixture()
returns void
language plpgsql
as $$
declare
  ia uuid := tests.uid('inst_a');
  ib uuid := tests.uid('inst_b');
begin
  insert into public.institutions (id, code, name) values
    (ia, 'TEST_A', 'Test Institution A'),
    (ib, 'TEST_B', 'Test Institution B');

  insert into public.departments (id, institution_id, code, name) values
    (tests.uid('dept_a'), ia, 'TDA', 'Test Department A'),
    (tests.uid('dept_b'), ib, 'TDB', 'Test Department B');

  insert into public.programmes (id, institution_id, department_id, code, name, degree_level, duration_semesters) values
    (tests.uid('prog_a'), ia, tests.uid('dept_a'), 'TPA', 'Test Programme A', 'undergraduate', 8),
    (tests.uid('prog_b'), ib, tests.uid('dept_b'), 'TPB', 'Test Programme B', 'undergraduate', 8);

  insert into public.courses (id, institution_id, department_id, programme_id, code, title, credits, semester_number) values
    (tests.uid('course_a1'), ia, tests.uid('dept_a'), tests.uid('prog_a'), 'TA101', 'Test Course A1', 4, 1),
    (tests.uid('course_a2'), ia, tests.uid('dept_a'), tests.uid('prog_a'), 'TA102', 'Test Course A2', 3, 1),
    (tests.uid('course_b1'), ib, tests.uid('dept_b'), tests.uid('prog_b'), 'TB101', 'Test Course B1', 4, 1);

  perform tests.create_user(tests.uid('user_s1'), 's1@test-a.example.com');
  perform tests.create_user(tests.uid('user_s2'), 's2@test-a.example.com');
  perform tests.create_user(tests.uid('user_s3'), 's3@test-b.example.com');
  perform tests.create_user(tests.uid('user_s4'), 's4@test-a.example.com', false);
  perform tests.create_user(tests.uid('user_m1'), 'm1@test-a.example.com');
  perform tests.create_user(tests.uid('user_m2'), 'm2@test-b.example.com');
  perform tests.create_user(tests.uid('user_f1'), 'f1@test-a.example.com');
  perform tests.create_user(tests.uid('user_f2'), 'f2@test-b.example.com');
  perform tests.create_user(tests.uid('user_a1'), 'a1@test-a.example.com');
  perform tests.create_user(tests.uid('user_a2'), 'a2@test-b.example.com');

  update public.profiles set role = 'mentor', institution_id = ia where id = tests.uid('user_m1');
  update public.profiles set role = 'mentor', institution_id = ib where id = tests.uid('user_m2');
  update public.profiles set role = 'faculty', institution_id = ia where id = tests.uid('user_f1');
  update public.profiles set role = 'faculty', institution_id = ib where id = tests.uid('user_f2');
  update public.profiles set role = 'admin', institution_id = ia where id = tests.uid('user_a1');
  update public.profiles set role = 'admin', institution_id = ib where id = tests.uid('user_a2');
  update public.profiles set institution_id = ia where id in (tests.uid('user_s1'), tests.uid('user_s2'));
  update public.profiles set institution_id = ib where id = tests.uid('user_s3');

  insert into public.students (id, institution_id, programme_id, user_id, roll_number, full_name,
                               institutional_email, admission_year, current_semester) values
    (tests.uid('student_s1'), ia, tests.uid('prog_a'), tests.uid('user_s1'), 'TA001', 'Test Student One', 's1@test-a.example.com', 2026, 1),
    (tests.uid('student_s2'), ia, tests.uid('prog_a'), tests.uid('user_s2'), 'TA002', 'Test Student Two', 's2@test-a.example.com', 2026, 1),
    (tests.uid('student_s3'), ib, tests.uid('prog_b'), tests.uid('user_s3'), 'TB001', 'Test Student Three', 's3@test-b.example.com', 2026, 1),
    (tests.uid('student_s4'), ia, tests.uid('prog_a'), null, 'TA004', 'Test Student Four', 's4@test-a.example.com', 2026, 1);

  insert into public.mentor_assignments (id, institution_id, mentor_id, student_id) values
    (tests.uid('ma_m1_s1'), ia, tests.uid('user_m1'), tests.uid('student_s1')),
    (tests.uid('ma_m2_s3'), ib, tests.uid('user_m2'), tests.uid('student_s3'));

  insert into public.course_faculty (institution_id, course_id, faculty_id) values
    (ia, tests.uid('course_a1'), tests.uid('user_f1')),
    (ib, tests.uid('course_b1'), tests.uid('user_f2'));

  insert into public.student_courses (id, institution_id, student_id, course_id, academic_year, semester) values
    (tests.uid('sc_s1_a1'), ia, tests.uid('student_s1'), tests.uid('course_a1'), '2026-27', 1),
    (tests.uid('sc_s1_a2'), ia, tests.uid('student_s1'), tests.uid('course_a2'), '2026-27', 1),
    (tests.uid('sc_s2_a2'), ia, tests.uid('student_s2'), tests.uid('course_a2'), '2026-27', 1),
    (tests.uid('sc_s3_b1'), ib, tests.uid('student_s3'), tests.uid('course_b1'), '2026-27', 1);

  insert into public.attendance_records (id, student_course_id, student_id, course_id, attendance_date, status) values
    (tests.uid('att_s1_a1'), tests.uid('sc_s1_a1'), tests.uid('student_s1'), tests.uid('course_a1'), date '2026-09-01', 'present'),
    (tests.uid('att_s1_a2'), tests.uid('sc_s1_a2'), tests.uid('student_s1'), tests.uid('course_a2'), date '2026-09-01', 'absent'),
    (tests.uid('att_s2_a2'), tests.uid('sc_s2_a2'), tests.uid('student_s2'), tests.uid('course_a2'), date '2026-09-01', 'present'),
    (tests.uid('att_s3_b1'), tests.uid('sc_s3_b1'), tests.uid('student_s3'), tests.uid('course_b1'), date '2026-09-01', 'present');

  insert into public.academic_records (id, student_id, academic_year, semester, sgpa, cgpa,
                                       credits_registered, credits_earned, result_status) values
    (tests.uid('ar_s1'), tests.uid('student_s1'), '2025-26', 1, 8.00, 8.00, 20, 20, 'pass'),
    (tests.uid('ar_s2'), tests.uid('student_s2'), '2025-26', 1, 7.00, 7.00, 20, 20, 'pass'),
    (tests.uid('ar_s3'), tests.uid('student_s3'), '2025-26', 1, 6.00, 6.00, 20, 20, 'pass');

  insert into public.assignments (id, institution_id, course_id, academic_year, title, max_score, due_at) values
    (tests.uid('asg_a1'), ia, tests.uid('course_a1'), '2026-27', 'Test Assignment A1', 20, timestamptz '2026-09-10 18:00+00'),
    (tests.uid('asg_a2'), ia, tests.uid('course_a2'), '2026-27', 'Test Assignment A2', 20, timestamptz '2026-09-10 18:00+00'),
    (tests.uid('asg_b1'), ib, tests.uid('course_b1'), '2026-27', 'Test Assignment B1', 20, timestamptz '2026-09-10 18:00+00');

  insert into public.assignment_submissions (id, assignment_id, student_id, status, submitted_at, score, graded_at) values
    (tests.uid('sub_s1_a1'), tests.uid('asg_a1'), tests.uid('student_s1'), 'submitted',
     timestamptz '2026-09-09 10:00+00', 15, timestamptz '2026-09-12 10:00+00'),
    (tests.uid('sub_s2_a2'), tests.uid('asg_a2'), tests.uid('student_s2'), 'submitted',
     timestamptz '2026-09-09 10:00+00', null, null),
    (tests.uid('sub_s3_b1'), tests.uid('asg_b1'), tests.uid('student_s3'), 'late',
     timestamptz '2026-09-11 10:00+00', null, null);

  insert into public.engagement_events (student_id, event_type, event_count, source, occurred_at) values
    (tests.uid('student_s1'), 'lms_login', 1, 'lms', timestamptz '2026-09-01 10:00+00'),
    (tests.uid('student_s2'), 'lms_login', 2, 'lms', timestamptz '2026-09-01 10:00+00'),
    (tests.uid('student_s3'), 'lms_login', 3, 'lms', timestamptz '2026-09-01 10:00+00');

  -- Test database = development environment: the synthetic test model may create predictions.
  perform set_config('sews.environment', 'development', true);
  insert into public.model_registry (id, model_name, version, target, dataset_version, feature_version,
                                     data_provenance, training_timestamp)
  values (tests.uid('model_test'), 'test-model', 'test-model-1', 'academic', 'ds-test-1', 'fs-test-1',
          'synthetic', timestamptz '2026-09-01 00:00+00');

  insert into public.risk_predictions (id, student_id, prediction_date, risk_probability, risk_level,
                                       model_version, feature_version, dataset_version, data_provenance,
                                       model_registry_id) values
    (tests.uid('pred_s1'), tests.uid('student_s1'), date '2026-09-20', 0.10, 'stable', 'test-model-1', 'fs-test-1', 'ds-test-1', 'synthetic', tests.uid('model_test')),
    (tests.uid('pred_s2'), tests.uid('student_s2'), date '2026-09-20', 0.60, 'elevated', 'test-model-1', 'fs-test-1', 'ds-test-1', 'synthetic', tests.uid('model_test')),
    (tests.uid('pred_s3'), tests.uid('student_s3'), date '2026-09-20', 0.80, 'high', 'test-model-1', 'fs-test-1', 'ds-test-1', 'synthetic', tests.uid('model_test'));

  insert into public.risk_factors (prediction_id, rank, feature, feature_value, contribution, direction) values
    (tests.uid('pred_s1'), 1, 'attendance_rate_last_14d', 0.95, -0.30, 'decreases_risk'),
    (tests.uid('pred_s2'), 1, 'missed_submission_rate', 0.50, 0.40, 'increases_risk'),
    (tests.uid('pred_s3'), 1, 'attendance_rate_last_14d', 0.40, 0.70, 'increases_risk');

  -- iv_s1: offered by the mentor (visible to the student); iv_s2/iv_s3: unreviewed rule recommendations.
  insert into public.interventions (id, student_id, prediction_id, intervention_type, status, source, notes, reason, priority) values
    (tests.uid('iv_s1'), tests.uid('student_s1'), tests.uid('pred_s1'), 'mentor_meeting', 'pending', 'mentor', 'Staff-only note S1', 'Check-in after recent absences', 'medium'),
    (tests.uid('iv_s2'), tests.uid('student_s2'), tests.uid('pred_s2'), 'assignment_support', 'recommended', 'model_rule', 'Staff-only note S2', 'Rule: missed submissions increased', 'medium'),
    (tests.uid('iv_s3'), tests.uid('student_s3'), tests.uid('pred_s3'), 'attendance_follow_up', 'recommended', 'model_rule', 'Staff-only note S3', 'Rule: attendance fell', 'high');

  insert into public.notifications (id, recipient_id, notification_type, title, body) values
    (tests.uid('notif_s1'), tests.uid('user_s1'), 'risk_update', 'Test title S1', 'Test body S1'),
    (tests.uid('notif_s2'), tests.uid('user_s2'), 'risk_update', 'Test title S2', 'Test body S2');
end;
$$;

grant usage on schema tests to anon, authenticated, service_role;
grant execute on all functions in schema tests to anon, authenticated, service_role;

select plan(1);
select has_function('tests', 'create_fixture', 'test helpers are installed');
select * from finish();

commit;
