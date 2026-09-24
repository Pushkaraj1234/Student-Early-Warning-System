-- Data integrity (controlled values, cross-institution consistency, deliberate
-- ON DELETE behaviour) and the audit trail.
begin;
select plan(27);

select tests.create_fixture();

-- ------------------------------------------------------- controlled values
select throws_ok(
  format('update public.student_courses set status = %L, grade = %L where id = %L', 'completed', 'A++', tests.uid('sc_s1_a1')),
  '23514', null, 'grades outside the UGC letter scale are rejected');
select throws_ok(
  format('update public.student_courses set marks = 101 where id = %L', tests.uid('sc_s1_a1')),
  '23514', null, 'marks above 100 are rejected');
select throws_ok(
  format('update public.student_courses set grade = %L where id = %L', 'A', tests.uid('sc_s1_a2')),
  '23514', null, 'a grade requires the enrolment to be completed');
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, date '2026-09-22', 1.2, 'high', 'm', 'f', 'd', 'synthetic', %L) $$, tests.uid('student_s1'), tests.uid('model_test')),
  '23514', null, 'risk probability must be within [0, 1]');
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, date '2026-09-22', 0.5, 'critical', 'm', 'f', 'd', 'synthetic', %L) $$, tests.uid('student_s1'), tests.uid('model_test')),
  '23514', null, 'risk level must be one of stable/watch/elevated/high');
select throws_ok(
  $$ insert into public.model_registry (model_name, version, target, dataset_version, feature_version,
                                       data_provenance, training_timestamp)
     values ('bad', 'bad-1', 'academic', 'd', 'f', 'real', now()) $$,
  '23514', null, 'data provenance must be benchmark/synthetic/institutional');
select throws_ok(
  format($$ insert into public.risk_factors (prediction_id, rank, feature, contribution, direction)
            values (%L, 2, 'late_submission_rate', 0.5, 'decreases_risk') $$, tests.uid('pred_s1')),
  '23514', null, 'factor direction must match the sign of its contribution');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, sgpa, cgpa,
            credits_registered, credits_earned, result_status) values (%L, '2025-26', 2, 7, 7, 10, 12, 'pass') $$,
         tests.uid('student_s1')),
  '23514', null, 'credits earned cannot exceed credits registered');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester,
            credits_registered, credits_earned, result_status) values (%L, '2025-26', 2, 20, 20, 'pass') $$,
         tests.uid('student_s1')),
  '23514', null, 'a published pass/fail result requires SGPA and CGPA');
select throws_ok(
  format('update public.profiles set role = %L, institution_id = null where id = %L', 'mentor', tests.uid('user_s4')),
  '23514', null, 'staff profiles must belong to an institution');

-- --------------------------------------------- cross-record consistency
select throws_ok(
  format($$ insert into public.student_courses (institution_id, student_id, course_id, academic_year, semester)
            values (%L, %L, %L, '2026-27', 1) $$, tests.uid('inst_a'), tests.uid('student_s1'), tests.uid('course_b1')),
  '23503', null, 'a student cannot be enrolled in another institution''s course');
select throws_ok(
  format($$ insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date, status)
            values (%L, %L, %L, date '2026-09-05', 'present') $$,
         tests.uid('sc_s1_a1'), tests.uid('student_s1'), tests.uid('course_a2')),
  '23503', null, 'attendance must match an existing enrolment');
select throws_ok(
  format($$ insert into public.assignment_submissions (assignment_id, student_id, status, submitted_at)
            values (%L, %L, 'submitted', now()) $$, tests.uid('asg_a1'), tests.uid('student_s2')),
  '23514', null, 'submissions require enrolment in the assignment''s course');
select throws_ok(
  format($$ insert into public.interventions (student_id, prediction_id, intervention_type, source)
            values (%L, %L, 'mentor_meeting', 'admin') $$, tests.uid('student_s1'), tests.uid('pred_s2')),
  '23514', null, 'an intervention cannot reference another student''s prediction');
select throws_ok(
  format($$ insert into public.mentor_assignments (institution_id, mentor_id, student_id)
            values (%L, %L, %L) $$, tests.uid('inst_a'), tests.uid('user_m1'), tests.uid('student_s1')),
  '23505', null, 'a student has at most one open mentor assignment');

-- ------------------------------------------------------------------- audit
update public.academic_records set sgpa = 8.10 where id = tests.uid('ar_s1');
select is((select changed_columns from public.audit_logs where record_id = tests.uid('ar_s1') and action = 'update'),
          array['sgpa']::text[], 'updates are audited with the changed column names');
update public.academic_records set sgpa = sgpa where id = tests.uid('ar_s2');
select is((select count(*)::int from public.audit_logs where record_id = tests.uid('ar_s2') and action = 'update'),
          0, 'no-op updates are not audited');
select tests.authenticate_as(tests.uid('user_f1'));
update public.attendance_records set status = 'late' where id = tests.uid('att_s1_a1');
select tests.clear_authentication();
select is((select actor_id from public.audit_logs where record_id = tests.uid('att_s1_a1') and action = 'update'),
          tests.uid('user_f1'), 'the audit actor is the authenticated user');
select columns_are('public', 'audit_logs',
  array['id', 'institution_id', 'actor_id', 'action', 'table_name', 'record_id', 'changed_columns', 'created_at'],
  'audit logs store no row contents');

-- -------------------------------------------------------------- updated_at
update public.institutions set updated_at = timestamptz '2000-01-01' where id = tests.uid('inst_a');
select isnt((select updated_at from public.institutions where id = tests.uid('inst_a')), timestamptz '2000-01-01',
            'updated_at is maintained by trigger, not by the client');

-- ------------------------------------------------------ ON DELETE behaviour
select throws_ok(
  format('delete from public.courses where id = %L', tests.uid('course_a2')),
  '23001', null, 'courses with enrolments cannot be deleted (RESTRICT)');
select throws_ok(
  format('delete from public.institutions where id = %L', tests.uid('inst_b')),
  '23001', null, 'institutions with data cannot be deleted (RESTRICT)');
select lives_ok(
  format('delete from public.students where id = %L', tests.uid('student_s2')),
  'service-side erasure of a student succeeds');
select is(
  (select count(*)::int from public.student_courses where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.attendance_records where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.academic_records where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.risk_predictions where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.risk_factors where prediction_id = tests.uid('pred_s2'))
  + (select count(*)::int from public.interventions where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.assignment_submissions where student_id = tests.uid('student_s2'))
  + (select count(*)::int from public.engagement_events where student_id = tests.uid('student_s2')),
  0, 'erasing a student cascades to all of their personal records');
select isnt_empty(format('select 1 from public.courses where id = %L', tests.uid('course_a2')),
                  'reference data survives a student erasure');
select lives_ok(
  format('delete from auth.users where id = %L', tests.uid('user_s1')),
  'deleting an auth user succeeds');
select ok(
  (select user_id is null from public.students where id = tests.uid('student_s1'))
  and not exists (select 1 from public.notifications where recipient_id = tests.uid('user_s1'))
  and not exists (select 1 from public.profiles where id = tests.uid('user_s1')),
  'deleting an account unlinks the student record and removes the profile and notifications');

select * from finish();
rollback;
