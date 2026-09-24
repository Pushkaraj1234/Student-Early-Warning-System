-- Student scope: own records only; academic, predictive and role data are read-only.
begin;
select plan(46);

select tests.create_fixture();
select tests.authenticate_as(tests.uid('user_s1'));

-- ------------------------------------------------------------ reads: own only
select set_eq($$ select id from public.students $$, array[tests.uid('student_s1')],
              'student sees only their own student record');
select set_eq($$ select id from public.student_courses $$, array[tests.uid('sc_s1_a1'), tests.uid('sc_s1_a2')],
              'student sees only their own enrolments');
select set_eq($$ select id from public.attendance_records $$, array[tests.uid('att_s1_a1'), tests.uid('att_s1_a2')],
              'student sees only their own attendance');
select set_eq($$ select id from public.academic_records $$, array[tests.uid('ar_s1')],
              'student sees only their own academic records');
select set_eq($$ select id from public.assignments $$, array[tests.uid('asg_a1'), tests.uid('asg_a2')],
              'student sees assignments only for courses they are enrolled in');
select set_eq($$ select id from public.assignment_submissions $$, array[tests.uid('sub_s1_a1')],
              'student sees only their own submissions');
select set_eq($$ select distinct student_id from public.engagement_events $$, array[tests.uid('student_s1')],
              'student sees only their own engagement events');
select set_eq($$ select id from public.risk_predictions $$, array[tests.uid('pred_s1')],
              'student sees only their own risk predictions');
select set_eq($$ select prediction_id from public.risk_factors $$, array[tests.uid('pred_s1')],
              'student sees only the factors of their own predictions');
select is_empty($$ select id from public.interventions $$,
                'student has no direct access to interventions (staff notes)');
select set_eq($$ select id from public.notifications $$, array[tests.uid('notif_s1')],
              'student sees only their own notifications');
select set_eq($$ select id from public.profiles $$, array[tests.uid('user_s1')],
              'student sees only their own profile');
select set_eq($$ select id from public.institutions $$, array[tests.uid('inst_a')],
              'student sees only their own institution');
select set_eq($$ select id from public.mentor_assignments $$, array[tests.uid('ma_m1_s1')],
              'student sees only their own mentor assignment');
select is_empty($$ select id from public.course_faculty $$, 'student cannot read course_faculty');
select is_empty($$ select id from public.audit_logs $$, 'student cannot read audit logs');

-- --------------------------------------- explicit queries for another student
select is_empty(format('select * from public.students where id = %L', tests.uid('student_s2')),
                'student cannot query another student record by id');
select is_empty(format('select * from public.risk_predictions where student_id = %L', tests.uid('student_s2')),
                'student cannot query another student''s predictions');
select is_empty(format('select * from public.academic_records where student_id = %L', tests.uid('student_s3')),
                'student cannot query another institution''s academic records');
select is_empty(format('select * from public.attendance_records where student_id = %L', tests.uid('student_s2')),
                'student cannot query another student''s attendance');

-- ------------------------------------------------ protected academic records
select is(tests.affected_rows(format('update public.student_courses set marks = 99 where id = %L', tests.uid('sc_s1_a1'))),
          0, 'student cannot change their own marks');
select is(tests.affected_rows(format('update public.academic_records set sgpa = 10 where id = %L', tests.uid('ar_s1'))),
          0, 'student cannot change their own SGPA');
select is(tests.affected_rows(format('delete from public.academic_records where id = %L', tests.uid('ar_s1'))),
          0, 'student cannot delete their own academic record');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, sgpa, cgpa,
            credits_registered, credits_earned, result_status)
            values (%L, '2025-26', 2, 10, 10, 20, 20, 'pass') $$, tests.uid('student_s1')),
  '42501', null, 'student cannot insert academic records');
select throws_ok(
  format($$ insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date, status)
            values (%L, %L, %L, date '2026-09-02', 'present') $$,
         tests.uid('sc_s1_a1'), tests.uid('student_s1'), tests.uid('course_a1')),
  '42501', null, 'student cannot insert attendance');
select is(tests.affected_rows(format('update public.attendance_records set status = %L where id = %L',
                                     'present', tests.uid('att_s1_a2'))),
          0, 'student cannot change their own attendance');
select is(tests.affected_rows(format('update public.students set full_name = %L where id = %L',
                                     'Changed Name', tests.uid('student_s1'))),
          0, 'student cannot edit their institutional student record');
select throws_ok(
  format('update public.students set user_id = %L where id = %L', tests.uid('user_s1'), tests.uid('student_s2')),
  '42501', null, 'student cannot re-link a student record (column not writable)');

-- ------------------------------------------------------------ role integrity
select throws_ok(
  format('update public.profiles set role = %L where id = %L', 'admin', tests.uid('user_s1')),
  '42501', null, 'student cannot change their own role');
select throws_ok(
  format('update public.profiles set institution_id = %L where id = %L', tests.uid('inst_b'), tests.uid('user_s1')),
  '42501', null, 'student cannot change their own institution');
select is(tests.affected_rows(format('update public.profiles set full_name = %L where id = %L',
                                     'Test Student One Renamed', tests.uid('user_s1'))),
          1, 'student can update their own display name');
select is(tests.affected_rows(format('update public.profiles set full_name = %L where id = %L',
                                     'Hijacked', tests.uid('user_s2'))),
          0, 'student cannot update another user''s display name');
select throws_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_s2'), 'mentor'),
  '42501', 'sews:not_an_admin', 'student cannot assign roles');

-- --------------------------------------------------- predictions are server-only
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance)
            values (%L, date '2026-09-21', 0.01, 'stable', 'forged', 'forged', 'forged', 'synthetic') $$,
         tests.uid('student_s1')),
  '42501', null, 'student cannot insert risk predictions');
select throws_ok(
  format('update public.risk_predictions set risk_level = %L where id = %L', 'stable', tests.uid('pred_s1')),
  '42501', null, 'student cannot update risk predictions');
select throws_ok(
  format('delete from public.risk_predictions where id = %L', tests.uid('pred_s1')),
  '42501', null, 'student cannot delete risk predictions');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, source)
            values (%L, 'mentor_meeting', 'mentor') $$, tests.uid('student_s1')),
  '42501', null, 'student cannot create interventions');
select throws_ok(
  format($$ insert into public.assignment_submissions (assignment_id, student_id, status, submitted_at)
            values (%L, %L, 'submitted', now()) $$, tests.uid('asg_a2'), tests.uid('student_s1')),
  '42501', null, 'student cannot record submissions directly');

-- --------------------------------------------------------------- notifications
select throws_ok(
  format($$ insert into public.notifications (recipient_id, notification_type, title, body)
            values (%L, 'system', 'x', 'y') $$, tests.uid('user_s1')),
  '42501', null, 'student cannot create notifications');
select is(tests.affected_rows(format('update public.notifications set read_at = now() where id = %L', tests.uid('notif_s1'))),
          1, 'student can mark their own notification as read');
select is(tests.affected_rows(format('update public.notifications set read_at = now() where id = %L', tests.uid('notif_s2'))),
          0, 'student cannot mark another user''s notification as read');
select throws_ok(
  format('update public.notifications set title = %L where id = %L', 'changed', tests.uid('notif_s1')),
  '42501', null, 'student cannot rewrite notification content');

-- ------------------------------------------------ recommended actions (RPC)
select set_eq($$ select id from public.get_my_recommended_actions() $$, array[tests.uid('iv_s1')],
              'get_my_recommended_actions returns only the caller''s own actions');
select is_empty(
  $$ select 1 from pg_proc where proname = 'get_my_recommended_actions' and 'notes' = any(proargnames) $$,
  'get_my_recommended_actions never exposes staff notes');

-- ------------------------------------------------------- a second student
select tests.authenticate_as(tests.uid('user_s2'));
select set_eq($$ select id from public.students $$, array[tests.uid('student_s2')],
              'second student sees only their own record');
select is_empty(format('select * from public.risk_factors where prediction_id = %L', tests.uid('pred_s1')),
                'second student cannot read the first student''s risk factors');

select * from finish();
rollback;
