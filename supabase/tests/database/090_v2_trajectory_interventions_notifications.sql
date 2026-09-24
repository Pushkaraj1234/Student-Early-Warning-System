-- V2: risk trajectory, intervention workflow, notifications (types, previews, delivery state,
-- mentor messages), mentor caseload and weekly trends.
begin;
select plan(63);

select tests.create_fixture();

-- ============================================================ trajectory rules
select is(private.classify_trajectory(null, null), 'insufficient_history', 'no previous prediction');
select is(private.classify_trajectory(-0.05, null), 'improving', 'a drop of 0.05 or more is improving');
select is(private.classify_trajectory(-0.0499, null), 'stable', 'changes inside the ±0.05 band are stable');
select is(private.classify_trajectory(0.0499, null), 'stable', 'a rise below 0.05 is stable');
select is(private.classify_trajectory(0.05, null), 'increasing', 'a rise of 0.05 without velocity is increasing');
select is(private.classify_trajectory(0.20, 0.0999), 'increasing', 'velocity below 0.10/week is increasing');
select is(private.classify_trajectory(0.20, 0.10), 'rapidly_increasing', 'velocity of 0.10/week or more is rapid');

-- S1: 0.10 on 2026-09-20 → 0.20 on 2026-09-27 (7 days): delta 0.10, velocity 0.10/week.
insert into public.risk_predictions (id, student_id, prediction_date, risk_probability, risk_level, model_version,
                                     feature_version, dataset_version, data_provenance, model_registry_id,
                                     trajectory, risk_delta)
values (tests.uid('pred_s1_b'), tests.uid('student_s1'), date '2026-09-27', 0.20, 'watch', 'x', 'x', 'x', 'synthetic',
        tests.uid('model_test'), 'improving', 0.99);
select results_eq(
  format($$ select previous_prediction_id, risk_delta, days_since_previous, risk_velocity_per_week, trajectory
            from public.risk_predictions where id = %L $$, tests.uid('pred_s1_b')),
  format($$ values (%L::uuid, 0.10000::numeric(6,5), 7, 0.10000::numeric(8,5), 'rapidly_increasing'::text) $$,
         tests.uid('pred_s1')),
  'trajectory is computed by the database; client-supplied values are ignored');

-- S2: 0.60 → 0.66 after 4 days: no velocity (< 7 days apart) → increasing.
insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level, model_version,
                                     feature_version, dataset_version, data_provenance, model_registry_id)
values (tests.uid('student_s2'), date '2026-09-24', 0.66, 'elevated', 'x', 'x', 'x', 'synthetic', tests.uid('model_test'));
select results_eq(
  format($$ select risk_velocity_per_week, trajectory from public.risk_predictions
            where student_id = %L and prediction_date = date '2026-09-24' $$, tests.uid('student_s2')),
  $$ values (null::numeric(8,5), 'increasing'::text) $$,
  'velocity is not computed for predictions less than 7 days apart');

-- S3: 0.80 → 0.72 after 14 days → improving, velocity -0.04/week.
insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level, model_version,
                                     feature_version, dataset_version, data_provenance, model_registry_id)
values (tests.uid('student_s3'), date '2026-10-04', 0.72, 'elevated', 'x', 'x', 'x', 'synthetic', tests.uid('model_test'));
select results_eq(
  format($$ select risk_delta, risk_velocity_per_week, trajectory from public.risk_predictions
            where student_id = %L and prediction_date = date '2026-10-04' $$, tests.uid('student_s3')),
  $$ values (-0.08000::numeric(6,5), -0.04000::numeric(8,5), 'improving'::text) $$,
  'a falling probability is improving');

-- A different model version is never compared with the previous one.
insert into public.model_registry (id, model_name, version, target, dataset_version, feature_version,
                                   data_provenance, training_timestamp)
values (tests.uid('model_test_2'), 'test-model', 'test-model-2', 'academic', 'ds-test-2', 'fs-test-2',
        'synthetic', now());
insert into public.risk_predictions (id, student_id, prediction_date, risk_probability, risk_level, model_version,
                                     feature_version, dataset_version, data_provenance, model_registry_id)
values (tests.uid('pred_s1_v2'), tests.uid('student_s1'), date '2026-10-04', 0.90, 'high', 'x', 'x', 'x', 'synthetic',
        tests.uid('model_test_2'));
select is((select trajectory from public.risk_predictions where id = tests.uid('pred_s1_v2')), 'insufficient_history',
          'predictions from different model versions are not compared');

insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level, model_version,
                                     feature_version, dataset_version, data_provenance, model_registry_id)
values (tests.uid('student_s1'), date '2026-10-11', 0.22, 'watch', 'x', 'x', 'x', 'synthetic', tests.uid('model_test'));
select is((select trajectory from public.risk_predictions
           where student_id = tests.uid('student_s1') and prediction_date = date '2026-10-11'),
          'stable', 'a small change within the same model version is stable');

-- ===================================================== risk-change notifications
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_m1') and notification_type = 'risk_change'),
          2, 'the mentor is alerted for rapidly increasing risk and for a new high level');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_m2') and notification_type = 'risk_change'),
          1, 'the only alert for S3 is its first high level (fixture); the improving update adds none');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_s1') and notification_type = 'risk_change'),
          0, 'students are not sent risk-change alerts');

insert into public.academic_records (student_id, academic_year, semester, sgpa, cgpa, credits_registered,
                                     credits_earned, result_status)
values (tests.uid('student_s1'), '2025-26', 2, 3.5, 5.75, 20, 12, 'fail');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_m1') and notification_type = 'academic_signal'),
          1, 'a failed semester result alerts the mentor (important academic signal)');
select is_empty(
  $$ select preview from public.notifications
     where preview not in ('You have a new update in SEWS.', 'You have a new message in SEWS.',
                           'A support option is available in SEWS.') $$,
  'every notification has a generic push preview');
select throws_ok(
  format($$ insert into public.notifications (recipient_id, notification_type, title, body, preview)
            values (%L, 'system', 't', 'b', 'Your risk is HIGH') $$, tests.uid('user_s1')),
  '23514', null, 'sensitive text cannot be used as a push preview');

-- ========================================================= intervention workflow
select tests.authenticate_as(tests.uid('user_m1'));
select lives_ok(
  format($$ select public.create_intervention(%L, 'academic_tutoring', 'Scores fell in Test Course A1', 'high', %L) $$,
         tests.uid('student_s1'), tests.uid('user_f1')),
  'mentor creates and assigns an intervention');
select throws_ok(
  format($$ select public.create_intervention(%L, 'academic_tutoring', 'Duplicate request') $$, tests.uid('student_s1')),
  '23505', 'sews:duplicate_intervention', 'duplicate open interventions of the same type are rejected');
select throws_ok(
  format($$ select public.create_intervention(%L, 'study_planning', '  ') $$, tests.uid('student_s1')),
  '22023', 'sews:invalid_reason', 'a reason is required');
select throws_ok(
  format($$ select public.create_intervention(%L, 'study_planning', 'Valid reason', 'urgent') $$, tests.uid('student_s1')),
  '22023', 'sews:invalid_priority', 'priority must be low/medium/high');
select throws_ok(
  format($$ select public.create_intervention(%L, 'detention', 'Not a support action') $$, tests.uid('student_s1')),
  '23514', null, 'only support intervention types exist');
select throws_ok(
  format($$ select public.assign_intervention(%L, %L) $$,
         (select id from public.interventions where intervention_type = 'academic_tutoring'), tests.uid('user_m2')),
  '23514', null, 'interventions cannot be assigned to staff of another institution');
select throws_ok(
  format($$ select public.approve_recommendation(%L) $$, tests.uid('iv_s3')),
  '42501', 'sews:forbidden', 'a mentor cannot review another institution''s recommendation');

select tests.clear_authentication();
select results_eq(
  $$ select status, source, created_by, assigned_to, offered_at is not null, assigned_at is not null, priority
     from public.interventions where intervention_type = 'academic_tutoring' $$,
  format($$ values ('pending'::text, 'mentor'::text, %L::uuid, %L::uuid, true, true, 'high'::text) $$,
         tests.uid('user_m1'), tests.uid('user_f1')),
  'created_by, source, status and timestamps are recorded server-side');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_f1') and notification_type = 'new_intervention'),
          1, 'the assignee is notified');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_s1') and notification_type = 'new_intervention'),
          1, 'the student is notified of the new support option');

-- The student responds.
select tests.authenticate_as(tests.uid('user_s1'));
select set_eq($$ select intervention_type from public.get_my_recommended_actions() $$,
              array['mentor_meeting', 'academic_tutoring'], 'the student sees offered interventions');
select throws_ok(
  format($$ select public.respond_to_intervention(%L, false, 'too_busy') $$, tests.uid('iv_s1')),
  '22023', 'sews:invalid_decline_reason', 'decline reasons are a controlled list');
select lives_ok(
  format($$ select public.respond_to_intervention(%L, false, 'not_convenient') $$, tests.uid('iv_s1')),
  'the student can decline an offered intervention');
select lives_ok(
  format($$ select public.respond_to_intervention(%L, true) $$,
         (select id from public.get_my_recommended_actions() where intervention_type = 'academic_tutoring')),
  'the student can accept an offered intervention');
select throws_ok(
  format($$ select public.respond_to_intervention(%L, true) $$, tests.uid('iv_s1')),
  '23514', 'sews:invalid_intervention_transition', 'a declined intervention cannot be accepted');

select tests.authenticate_as(tests.uid('user_s2'));
select throws_ok(
  format($$ select public.respond_to_intervention(%L, true) $$, tests.uid('iv_s1')),
  '42501', 'sews:forbidden', 'a student cannot respond to another student''s intervention');
select is_empty($$ select * from public.get_my_recommended_actions() $$,
                'unreviewed rule recommendations are hidden from the student');
select throws_ok(
  format($$ select public.create_intervention(%L, 'mentor_meeting', 'Self-created') $$, tests.uid('student_s2')),
  '42501', 'sews:forbidden', 'students cannot create interventions');

select tests.authenticate_as(tests.uid('user_f1'));
select throws_ok(
  format($$ select public.create_intervention(%L, 'mentor_meeting', 'Faculty-created') $$, tests.uid('student_s1')),
  '42501', 'sews:forbidden', 'faculty cannot create interventions');
select throws_ok(
  format($$ select public.complete_intervention(%L, 'great') $$,
         (select id from public.interventions where intervention_type = 'academic_tutoring')),
  '22023', 'sews:invalid_outcome', 'outcomes are a controlled list');
select lives_ok(
  format($$ select public.complete_intervention(%L, 'improved') $$,
         (select id from public.interventions where intervention_type = 'academic_tutoring')),
  'the assignee can complete an accepted intervention with an outcome');

select tests.clear_authentication();
select results_eq(
  $$ select status, outcome, responded_at is not null, completed_at is not null from public.interventions
     where intervention_type = 'academic_tutoring' $$,
  $$ values ('completed'::text, 'improved'::text, true, true) $$,
  'acceptance and completion are timestamped');
select results_eq(
  format($$ select status, decline_reason from public.interventions where id = %L $$, tests.uid('iv_s1')),
  $$ values ('declined'::text, 'not_convenient'::text) $$,
  'the decline and its reason are recorded');
select is((select count(*)::int from public.notifications
           where recipient_id = tests.uid('user_f1') and notification_type = 'intervention'),
          1, 'the assignee is told when the student accepts');

select tests.authenticate_as(tests.uid('user_a1'));
select lives_ok(format($$ select public.approve_recommendation(%L) $$, tests.uid('iv_s2')),
                'an admin can review a rule recommendation');
select tests.authenticate_as(tests.uid('user_s2'));
select set_eq($$ select id from public.get_my_recommended_actions() $$, array[tests.uid('iv_s2')],
              'after human review the student can see it');
select tests.authenticate_as(tests.uid('user_a1'));
select lives_ok(format($$ select public.cancel_intervention(%L) $$, tests.uid('iv_s2')),
                'staff can cancel an offered intervention');
select throws_ok(format($$ select public.cancel_intervention(%L) $$, tests.uid('iv_s2')),
                 '23514', 'sews:invalid_intervention_transition', 'a cancelled intervention cannot be cancelled again');

select tests.clear_authentication();
select throws_ok(
  format($$ update public.interventions set status = 'completed' where id = %L $$, tests.uid('iv_s3')),
  '23514', 'sews:invalid_intervention_transition', 'the state machine applies even to server-side updates');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, status, source, reason)
            values (%L, 'mentor_meeting', 'pending', 'model_rule', 'Rule output') $$, tests.uid('student_s1')),
  '23514', 'sews:rule_recommendations_require_review', 'rule output always requires human review');

-- ===================================================== mentor messages & delivery
select tests.authenticate_as(tests.uid('user_m1'));
select lives_ok(format($$ select public.send_mentor_message(%L, 'Can we meet on Friday?') $$, tests.uid('student_s1')),
                'a mentor can message a mentee');
select throws_ok(format($$ select public.send_mentor_message(%L, 'Hello') $$, tests.uid('student_s2')),
                 '42501', 'sews:forbidden', 'a mentor cannot message students outside their caseload');
select throws_ok(format($$ select public.send_mentor_message(%L, '   ') $$, tests.uid('student_s1')),
                 '22023', 'sews:invalid_message', 'empty messages are rejected');

select tests.authenticate_as(tests.uid('user_s1'));
select results_eq(
  $$ select sender_id, preview, delivery_status from public.notifications where notification_type = 'mentor_message' $$,
  format($$ values (%L::uuid, 'You have a new message in SEWS.'::text, 'pending'::text) $$, tests.uid('user_m1')),
  'the student receives the message with a generic preview and pending delivery');
select throws_ok(
  $$ update public.notifications set delivery_status = 'sent' $$,
  '42501', null, 'clients cannot change delivery state');
select tests.authenticate_as(tests.uid('user_s2'));
select is_empty($$ select * from public.notifications where notification_type = 'mentor_message' $$,
                'other students cannot see the message');

select tests.clear_authentication();
select throws_ok(
  $$ update public.notifications set delivery_status = 'sent' where notification_type = 'mentor_message' $$,
  '23514', null, 'sent requires a delivery timestamp');
select lives_ok(
  $$ update public.notifications set delivery_status = 'sent', delivered_at = now(), delivery_attempts = 1
     where notification_type = 'mentor_message' $$,
  'the delivery worker records a successful delivery');
insert into public.notifications (recipient_id, notification_type, title, body, sender_id)
select tests.uid('user_s1'), 'mentor_message', 'm', 'm', tests.uid('user_m1') from generate_series(1, 19);
select tests.authenticate_as(tests.uid('user_m1'));
select throws_ok(format($$ select public.send_mentor_message(%L, 'One more') $$, tests.uid('student_s1')),
                 'P0001', 'sews:rate_limited', 'mentor messages are rate limited');

-- ================================================== caseload and weekly trends
select set_eq($$ select student_id from public.get_mentor_caseload() $$, array[tests.uid('student_s1')],
              'the caseload contains only assigned students');
select is((select risk_level from public.get_mentor_caseload()), 'watch',
          'the caseload shows the latest academic prediction');
select tests.authenticate_as(tests.uid('user_m2'));
select set_eq($$ select student_id from public.get_mentor_caseload() $$, array[tests.uid('student_s3')],
              'another institution''s mentor sees only their own caseload');
select tests.authenticate_as(tests.uid('user_s1'));
select is_empty($$ select * from public.get_mentor_caseload() $$, 'students have no caseload');
select is((select count(*)::int from public.get_student_weekly_trends(tests.uid('student_s1'), 8)), 8,
          'a student gets their own weekly trends');
select throws_ok(format($$ select * from public.get_student_weekly_trends(%L) $$, tests.uid('student_s2')),
                 '42501', 'sews:forbidden', 'a student cannot read another student''s trends');

select * from finish();
rollback;
