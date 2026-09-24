-- Mentor scope: only students with an active mentor assignment, never another
-- institution; interventions for mentees only; no academic/predictive writes.
begin;
select plan(33);

select tests.create_fixture();
select tests.authenticate_as(tests.uid('user_m1'));

-- -------------------------------------------------------- reads: mentees only
select set_eq($$ select id from public.students $$, array[tests.uid('student_s1')],
              'mentor sees only assigned students');
select set_eq($$ select id from public.student_courses $$, array[tests.uid('sc_s1_a1'), tests.uid('sc_s1_a2')],
              'mentor sees only mentee enrolments');
select set_eq($$ select id from public.attendance_records $$, array[tests.uid('att_s1_a1'), tests.uid('att_s1_a2')],
              'mentor sees only mentee attendance');
select set_eq($$ select id from public.academic_records $$, array[tests.uid('ar_s1')],
              'mentor sees only mentee academic records');
select set_eq($$ select id from public.risk_predictions $$, array[tests.uid('pred_s1')],
              'mentor sees only mentee predictions');
select set_eq($$ select prediction_id from public.risk_factors $$, array[tests.uid('pred_s1')],
              'mentor sees only mentee risk factors');
select set_eq($$ select id from public.interventions $$, array[tests.uid('iv_s1')],
              'mentor sees only mentee interventions');
select set_eq($$ select distinct student_id from public.engagement_events $$, array[tests.uid('student_s1')],
              'mentor sees only mentee engagement');
select set_eq($$ select id from public.assignment_submissions $$, array[tests.uid('sub_s1_a1')],
              'mentor sees only mentee submissions');
select set_eq($$ select id from public.assignments $$, array[tests.uid('asg_a1'), tests.uid('asg_a2')],
              'mentor sees assignments of courses their mentees take');
select set_eq($$ select id from public.institutions $$, array[tests.uid('inst_a')],
              'mentor sees only their own institution');
select is_empty(format('select * from public.students where institution_id = %L', tests.uid('inst_b')),
                'mentor cannot access students of another institution');
select is_empty(format('select * from public.risk_predictions where student_id = %L', tests.uid('student_s3')),
                'mentor cannot access predictions of another institution');
select is_empty(format('select * from public.students where id = %L', tests.uid('student_s2')),
                'mentor cannot access unassigned students of their own institution');
select set_eq($$ select id from public.profiles $$, array[tests.uid('user_m1')],
              'mentor sees only their own profile');
select is_empty($$ select id from public.audit_logs $$, 'mentor cannot read audit logs');

-- ------------------------------------------------------------ interventions
select lives_ok(
  format($$ select public.create_intervention(%L, 'peer_tutoring', 'Arrange peer tutoring sessions') $$,
         tests.uid('student_s1')),
  'mentor can create an intervention for a mentee (RPC)');
select is(
  (select created_by::text || '/' || source from public.interventions
   where student_id = tests.uid('student_s1') and intervention_type = 'peer_tutoring'),
  tests.uid('user_m1')::text || '/mentor',
  'created_by and source are set by the server, not the client');
select throws_ok(
  format($$ select public.create_intervention(%L, 'mentor_meeting', 'Check in') $$, tests.uid('student_s2')),
  '42501', 'sews:forbidden', 'mentor cannot create interventions for unassigned students');
select throws_ok(
  format($$ select public.create_intervention(%L, 'mentor_meeting', 'Check in') $$, tests.uid('student_s3')),
  '42501', 'sews:forbidden', 'mentor cannot create interventions in another institution');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, source, reason)
            values (%L, 'mentor_meeting', 'mentor', 'Direct insert') $$, tests.uid('student_s1')),
  '42501', null, 'interventions cannot be inserted directly (RPC only)');
select is(tests.affected_rows(format('update public.interventions set notes = %L where id = %L',
                                     'Updated staff note', tests.uid('iv_s1'))),
          1, 'mentor can edit notes on a mentee intervention');
select throws_ok(
  format('update public.interventions set status = %L where id = %L', 'completed', tests.uid('iv_s1')),
  '42501', null, 'status cannot be changed directly (RPC only)');
select is(tests.affected_rows(format('update public.interventions set notes = %L where id = %L',
                                     'x', tests.uid('iv_s3'))),
          0, 'mentor cannot edit interventions in another institution');

-- ------------------------------------------------------ no protected writes
select is(tests.affected_rows(format('update public.student_courses set marks = 99 where id = %L', tests.uid('sc_s1_a1'))),
          0, 'mentor cannot change marks');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, credits_registered,
            credits_earned, result_status) values (%L, '2026-27', 1, 0, 0, 'pending') $$, tests.uid('student_s1')),
  '42501', null, 'mentor cannot create academic records');
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance)
            values (%L, date '2026-09-21', 0.9, 'high', 'forged', 'forged', 'forged', 'synthetic') $$,
         tests.uid('student_s1')),
  '42501', null, 'mentor cannot insert risk predictions');
select is(tests.affected_rows(format('update public.mentor_assignments set ends_on = null where id = %L',
                                     tests.uid('ma_m1_s1'))),
          0, 'mentor cannot modify mentor assignments');

-- ------------------------------------------------- scope ends with assignment
select tests.clear_authentication();
update public.mentor_assignments
   set starts_on = current_date - 10, ends_on = current_date - 1
 where id = tests.uid('ma_m1_s1');
select tests.authenticate_as(tests.uid('user_m1'));
select is_empty($$ select id from public.students $$, 'mentor loses access when the assignment has ended');
select is_empty($$ select id from public.risk_predictions $$, 'ended assignment also hides predictions');

-- ------------------------------------------------- other institution's mentor
select tests.authenticate_as(tests.uid('user_m2'));
select set_eq($$ select id from public.students $$, array[tests.uid('student_s3')],
              'institution B mentor sees only their own mentee');
select is_empty(format('select * from public.students where id = %L', tests.uid('student_s1')),
                'institution B mentor cannot access institution A students');

-- ------------------------------------------------------ role is re-checked
select tests.clear_authentication();
update public.mentor_assignments set ends_on = null where id = tests.uid('ma_m1_s1');
update public.profiles set role = 'faculty' where id = tests.uid('user_m1');
select tests.authenticate_as(tests.uid('user_m1'));
select is_empty($$ select id from public.students $$,
                'a user whose mentor role was removed loses mentor access');

select * from finish();
rollback;
