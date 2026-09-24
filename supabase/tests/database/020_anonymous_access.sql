-- Anonymous (signed-out) callers are denied everywhere.
begin;
select plan(31);

select tests.create_fixture();
select tests.authenticate_as_anon();

select throws_ok(
  format('select * from public.%I', t),
  '42501', null,
  format('anon cannot read %s', t)
)
from unnest(array[
  'institutions', 'departments', 'programmes', 'profiles', 'students', 'courses',
  'mentor_assignments', 'course_faculty', 'student_courses', 'academic_records',
  'attendance_records', 'assignments', 'assignment_submissions', 'engagement_events',
  'risk_predictions', 'risk_factors', 'interventions', 'notifications', 'audit_logs',
  'academic_terms', 'lms_integrations', 'student_checkins', 'intervention_outcome_measures',
  'model_registry', 'model_monitoring_snapshots', 'drift_alerts', 'system_events'
]) as t;

select throws_ok(
  $$ insert into public.institutions (code, name) values ('ANON_X', 'Anon Institution') $$,
  '42501', null, 'anon cannot insert institutions'
);

select throws_ok(
  format('update public.academic_records set sgpa = 10 where id = %L', tests.uid('ar_s1')),
  '42501', null, 'anon cannot update academic records'
);

select throws_ok(
  $$ select public.claim_student_record() $$,
  '42501', null, 'anon cannot call claim_student_record'
);

select throws_ok(
  $$ select * from public.get_my_recommended_actions() $$,
  '42501', null, 'anon cannot call get_my_recommended_actions'
);

select * from finish();
rollback;
