-- V4: model registry lifecycle, live-prediction gating, identity/ML separation, monitoring RLS.
begin;
select plan(35);

select tests.create_fixture();

-- ============================================================ lifecycle
select throws_ok(
  $$ insert into public.model_registry (model_name, version, target, dataset_version, feature_version,
                                       data_provenance, training_timestamp, status)
     values ('m', 'direct-prod-1', 'academic', 'd', 'f', 'institutional', now(), 'production') $$,
  '23514', 'sews:models_start_in_development', 'models are registered in development');

insert into public.model_registry (id, model_name, version, target, dataset_version, feature_version,
                                   data_provenance, training_timestamp)
values (tests.uid('model_inst'), 'inst-model', 'inst-model-1', 'academic', 'inst-ds-1', 'inst-fs-1',
        'institutional', now());

select throws_ok(
  format($$ update public.model_registry set status = 'validated' where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:validation_metrics_required', 'validation requires metrics');
select lives_ok(
  format($$ update public.model_registry set status = 'validated', validation_metrics = '{"test": {"pr_auc": 0.7}}'
            where id = %L $$, tests.uid('model_inst')),
  'a model with validation metrics can be marked validated');
select throws_ok(
  format($$ update public.model_registry set status = 'production' where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:invalid_model_transition', 'validated models must pass through staging');
select lives_ok(
  format($$ update public.model_registry set status = 'staging' where id = %L $$, tests.uid('model_inst')),
  'validated → staging');
select throws_ok(
  format($$ update public.model_registry set status = 'production' where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:calibration_evaluation_required', 'production requires a calibration evaluation');
select throws_ok(
  format($$ update public.model_registry set status = 'production', calibration_metrics = '{"ece": 0.04}'
            where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:production_requires_approval', 'production requires a recorded approval');
select lives_ok(
  format($$ update public.model_registry set status = 'production', calibration_metrics = '{"ece": 0.04}',
            approved_by = %L, approved_at = now() where id = %L $$, tests.uid('user_a1'), tests.uid('model_inst')),
  'an approved, calibrated, validated institutional model can go to production');

update public.model_registry set status = 'validated', validation_metrics = '{"test": {}}' where id = tests.uid('model_test');
update public.model_registry set status = 'staging' where id = tests.uid('model_test');
select throws_ok(
  format($$ update public.model_registry set status = 'production', calibration_metrics = '{"ece": 0.1}',
            approved_by = %L, approved_at = now() where id = %L $$, tests.uid('user_a1'), tests.uid('model_test')),
  '23514', 'sews:production_requires_institutional_data', 'benchmark/synthetic models can never go to production');

insert into public.model_registry (id, model_name, version, target, dataset_version, feature_version,
                                   data_provenance, training_timestamp)
values (tests.uid('model_inst2'), 'inst-model', 'inst-model-2', 'academic', 'inst-ds-2', 'inst-fs-2',
        'institutional', now());
update public.model_registry set status = 'validated', validation_metrics = '{"test": {}}' where id = tests.uid('model_inst2');
update public.model_registry set status = 'staging' where id = tests.uid('model_inst2');
select throws_ok(
  format($$ update public.model_registry set status = 'production', calibration_metrics = '{"ece": 0.1}',
            approved_by = %L, approved_at = now() where id = %L $$, tests.uid('user_a1'), tests.uid('model_inst2')),
  '23505', null, 'only one production model per target and scope');
select throws_ok(
  format($$ update public.model_registry set dataset_version = 'other' where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:model_identity_is_immutable', 'registered lineage cannot be edited');
select throws_ok(
  format($$ update public.model_registry set status = 'development' where id = %L $$, tests.uid('model_inst')),
  '23514', 'sews:invalid_model_transition', 'production models can only be retired');

-- ================================================================ gating
select set_config('sews.environment', 'production', true);
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, date '2026-09-30', 0.3, 'watch', 'x', 'x', 'x', 'synthetic', %L) $$,
         tests.uid('student_s1'), tests.uid('model_test_dev')),
  '23514', 'sews:prediction_requires_registered_model', 'predictions require a registered model');
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, date '2026-09-30', 0.3, 'watch', 'x', 'x', 'x', 'synthetic', %L) $$,
         tests.uid('student_s1'), tests.uid('model_test')),
  '23514', 'sews:model_not_approved_for_live_predictions', 'non-production models cannot score in production');
select lives_ok(
  format($$ insert into public.risk_predictions (id, student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, %L, date '2026-09-30', 0.3, 'watch', 'forged', 'forged', 'forged', 'synthetic', %L) $$,
         tests.uid('pred_live'), tests.uid('student_s1'), tests.uid('model_inst')),
  'a production model can score');
select results_eq(
  format($$ select model_version, feature_version, dataset_version, data_provenance from public.risk_predictions
            where id = %L $$, tests.uid('pred_live')),
  $$ values ('inst-model-1'::text, 'inst-fs-1'::text, 'inst-ds-1'::text, 'institutional'::text) $$,
  'lineage is copied from the registry, not from the caller');
select set_config('sews.environment', 'development', true);
insert into public.model_registry (id, model_name, version, target, institution_id, dataset_version, feature_version,
                                   data_provenance, training_timestamp)
values (tests.uid('model_b'), 'inst-b-model', 'inst-b-model-1', 'academic', tests.uid('inst_b'), 'b-ds', 'b-fs',
        'institutional', now());
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance, model_registry_id)
            values (%L, date '2026-09-30', 0.3, 'watch', 'x', 'x', 'x', 'synthetic', %L) $$,
         tests.uid('student_s1'), tests.uid('model_b')),
  '23514', 'sews:model_institution_mismatch', 'an institution-specific model cannot score another institution');

-- ================================================================ privacy
select isnt(private.ml_subject_id_for(tests.uid('student_s1')), tests.uid('student_s1'),
            'the ML identifier is not the student id');
select is(private.ml_subject_id_for(tests.uid('student_s1')),
          (select ml_subject_id from private.ml_subject_map where student_id = tests.uid('student_s1')),
          'the ML identifier is stable');
select throws_ok(
  format($$ insert into private.feature_snapshots (ml_subject_id, as_of, feature_version, features)
            values (%L, now(), 'fs-1', '{"attendance_rate_last_14d": 0.8, "email": "x@y.z"}') $$,
         private.ml_subject_id_for(tests.uid('student_s1'))),
  '23514', null, 'feature snapshots reject identity fields');
select lives_ok(
  format($$ insert into private.feature_snapshots (ml_subject_id, as_of, feature_version, features)
            values (%L, now(), 'fs-1', '{"attendance_rate_last_14d": 0.8}') $$,
         private.ml_subject_id_for(tests.uid('student_s2'))),
  'feature snapshots store features under the ML identifier');
delete from public.students where id = tests.uid('student_s2');
select is((select count(*)::int from private.feature_snapshots), 0,
          'erasing a student also erases their ML identifier and feature snapshots');

-- =========================================================== monitoring RLS
insert into public.model_monitoring_snapshots (id, model_registry_id, window_start, window_end, n_predictions,
                                               level_distribution, probability_quantiles, feature_stats)
values (tests.uid('snap_inst'), tests.uid('model_inst'), date '2026-09-01', date '2026-09-30', 10,
        '{"stable": 6, "watch": 2, "elevated": 1, "high": 1}', '{"p50": 0.3}', '{"clicks_last_7d": {"mean": 12}}');
insert into public.drift_alerts (id, model_registry_id, monitoring_snapshot_id, alert_type, subject, statistic, value,
                                 threshold, severity)
values (tests.uid('alert_inst'), tests.uid('model_inst'), tests.uid('snap_inst'), 'feature_drift', 'clicks_last_7d',
        'psi', 0.31, 0.25, 'critical'),
       (tests.uid('alert_b'), tests.uid('model_b'), null, 'prediction_drift', 'prediction', 'psi', 0.12, 0.10, 'warning');
insert into public.system_events (component, event_type, severity, institution_id, details) values
  ('scoring', 'prediction_failure', 'error', tests.uid('inst_a'), '{"error_code": "feature_missing"}'),
  ('scoring', 'prediction_failure', 'error', tests.uid('inst_b'), '{"error_code": "feature_missing"}'),
  ('api', 'latency_breach', 'warning', null, '{"p95_ms": 1200}');

select tests.authenticate_as(tests.uid('user_a1'));
select is_empty(format('select 1 from public.model_registry where institution_id = %L', tests.uid('inst_b')),
                'an admin cannot see another institution''s models');
select is((select count(*)::int from public.model_monitoring_snapshots), 1, 'an admin sees monitoring for visible models');
select lives_ok(format($$ select public.acknowledge_drift_alert(%L) $$, tests.uid('alert_inst')),
                'an admin can acknowledge a drift alert');
select throws_ok(format($$ select public.acknowledge_drift_alert(%L) $$, tests.uid('alert_inst')),
                 'P0001', 'sews:alert_not_open', 'an alert is acknowledged once');
select throws_ok(format($$ select public.acknowledge_drift_alert(%L) $$, tests.uid('alert_b')),
                 '42501', 'sews:forbidden', 'an admin cannot acknowledge another institution''s alert');
select is_empty(format('select 1 from public.system_events where institution_id = %L', tests.uid('inst_b')),
                'an admin sees only their own institution''s and global system events');
select is((select version from public.get_platform_versions() where component = 'database_schema'), '4.0.0',
          'platform versions are exposed to signed-in users');

select tests.authenticate_as(tests.uid('user_a2'));
select isnt_empty(format('select 1 from public.model_registry where id = %L', tests.uid('model_b')),
                  'the other institution''s admin sees their own model');

select tests.authenticate_as(tests.uid('user_m1'));
select is_empty($$ select 1 from public.model_registry $$, 'mentors cannot read the model registry');
select is_empty($$ select 1 from public.model_monitoring_snapshots $$, 'mentors cannot read monitoring');
select throws_ok(format($$ select public.acknowledge_drift_alert(%L) $$, tests.uid('alert_inst')),
                 '42501', 'sews:forbidden', 'mentors cannot acknowledge alerts');

select tests.authenticate_as(tests.uid('user_s1'));
select is_empty($$ select 1 from public.system_events $$, 'students cannot read system events');

select tests.clear_authentication();
select throws_ok(
  $$ insert into public.system_events (component, event_type, severity, details)
     values ('api', 'prediction_failure', 'error', '{"student_id": "abc"}') $$,
  '23514', null, 'operational events cannot carry student identifiers');

select * from finish();
rollback;
