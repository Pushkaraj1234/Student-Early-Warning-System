-- V3: optional student check-ins (support needs only) and intervention outcome measures.
begin;
select plan(23);

select tests.create_fixture();

-- ================================================================== check-ins
select tests.authenticate_as(tests.uid('user_s1'));
select lives_ok(
  format($$ insert into public.student_checkins (student_id, support_needs) values (%L, array['workload']) $$,
         tests.uid('student_s1')),
  'a student can submit an optional check-in');
select throws_ok(
  format($$ insert into public.student_checkins (student_id, support_needs, submitted_at)
            values (%L, array['workload'], now() - interval '3 days') $$, tests.uid('student_s1')),
  '42501', null, 'the submission time is set by the server');
select throws_ok(
  format($$ insert into public.student_checkins (student_id, support_needs) values (%L, array['workload']) $$,
         tests.uid('student_s2')),
  '42501', null, 'a student cannot submit a check-in for someone else');
select throws_ok(
  format($$ insert into public.student_checkins (student_id, support_needs) values (%L, array['depression']) $$,
         tests.uid('student_s1')),
  '23514', null, 'check-ins cannot record mental-health conditions (support needs only)');
select throws_ok(
  format($$ insert into public.student_checkins (student_id, support_needs) values (%L, array['workload', 'workload']) $$,
         tests.uid('student_s1')),
  '23514', null, 'duplicate needs are rejected');
select throws_ok(
  format($$ insert into public.student_checkins (student_id) values (%L) $$, tests.uid('student_s1')),
  '23514', null, 'an empty check-in is rejected');
select lives_ok(
  format($$ insert into public.student_checkins (student_id, support_needs, wants_contact)
            values (%L, array['financial_difficulty'], true) $$, tests.uid('student_s1')),
  'a student can explicitly ask for contact');
select lives_ok(
  format($$ insert into public.student_checkins (student_id, comment) values (%L, 'Exams are close') $$,
         tests.uid('student_s1')),
  'a comment-only check-in is allowed');
select throws_ok(
  format($$ insert into public.student_checkins (student_id, support_needs) values (%L, array['workload']) $$,
         tests.uid('student_s1')),
  'P0001', 'sews:rate_limited', 'at most three check-ins per day');
select throws_ok(
  $$ update public.student_checkins set wants_contact = false $$,
  '42501', null, 'check-ins are append-only');

select tests.clear_authentication();
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_m1') and notification_type = 'student_checkin'),
          1, 'only the explicit request (contact / financial difficulty) alerts the mentor');

select tests.authenticate_as(tests.uid('user_m1'));
select is((select count(*)::int from public.student_checkins), 3, 'the mentor sees the mentee''s check-ins');
select tests.authenticate_as(tests.uid('user_m2'));
select is_empty($$ select * from public.student_checkins $$, 'another institution''s mentor sees none');
select tests.authenticate_as(tests.uid('user_f1'));
select is_empty($$ select * from public.student_checkins $$, 'faculty cannot read check-ins');
select tests.authenticate_as(tests.uid('user_s2'));
select is_empty($$ select * from public.student_checkins $$, 'other students cannot read check-ins');
select tests.authenticate_as(tests.uid('user_a1'));
select is((select count(*)::int from public.student_checkins), 3, 'the institution admin can read check-ins');

-- ========================================================= outcome measures
select tests.clear_authentication();
select lives_ok(
  format($$ insert into public.intervention_outcome_measures (intervention_id, indicator, baseline_value, followup_value,
            baseline_start, baseline_end, followup_start, followup_end, method_version)
            values (%L, 'attendance_rate', 0.55, 0.72, date '2026-08-01', date '2026-08-14',
                    date '2026-09-01', date '2026-09-14', 'outcomes-1.0.0') $$, tests.uid('iv_s1')),
  'the outcome job records before/after indicators');
select throws_ok(
  format($$ insert into public.intervention_outcome_measures (intervention_id, indicator, baseline_start, baseline_end,
            followup_start, followup_end, method_version)
            values (%L, 'happiness', date '2026-08-01', date '2026-08-14', date '2026-09-01', date '2026-09-14', 'm1') $$,
         tests.uid('iv_s1')),
  '23514', null, 'only defined indicators can be recorded');
select throws_ok(
  format($$ insert into public.intervention_outcome_measures (intervention_id, indicator, baseline_start, baseline_end,
            followup_start, followup_end, method_version)
            values (%L, 'mean_score_pct', date '2026-08-01', date '2026-08-14', date '2026-08-10', date '2026-09-14', 'm1') $$,
         tests.uid('iv_s1')),
  '23514', null, 'the follow-up window must start after the baseline window');

select tests.authenticate_as(tests.uid('user_m1'));
select is((select count(*)::int from public.intervention_outcome_measures), 1,
          'the mentor sees outcome measures of mentee interventions');
select throws_ok(
  format($$ insert into public.intervention_outcome_measures (intervention_id, indicator, baseline_start, baseline_end,
            followup_start, followup_end, method_version)
            values (%L, 'risk_probability', date '2026-08-01', date '2026-08-14', date '2026-09-01', date '2026-09-14', 'm1') $$,
         tests.uid('iv_s1')),
  '42501', null, 'outcome measures are written server-side only');
select tests.authenticate_as(tests.uid('user_s1'));
select is_empty($$ select * from public.intervention_outcome_measures $$, 'students cannot read outcome measures');
select tests.authenticate_as(tests.uid('user_m2'));
select is_empty($$ select * from public.intervention_outcome_measures $$,
                'another institution''s mentor cannot read them');

select * from finish();
rollback;
