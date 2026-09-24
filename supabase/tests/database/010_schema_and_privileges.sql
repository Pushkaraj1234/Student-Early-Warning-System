-- Structural guarantees: exact table set, RLS everywhere, no anon privileges,
-- hardened SECURITY DEFINER functions, server-only tables, required indexes.
begin;
select plan(36);

select tables_are(
  'public',
  array[
    'academic_records', 'academic_terms', 'assignment_submissions', 'assignments', 'attendance_records',
    'audit_logs', 'course_faculty', 'courses', 'departments', 'drift_alerts', 'engagement_events',
    'institutions', 'intervention_outcome_measures', 'interventions', 'lms_integrations',
    'mentor_assignments', 'model_monitoring_snapshots', 'model_registry', 'notifications', 'profiles',
    'programmes', 'risk_factors', 'risk_predictions', 'student_checkins', 'student_courses', 'students',
    'system_events'
  ],
  'public schema contains exactly the SEWS tables'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity $$,
  'every public table has RLS enabled'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r'
       and not exists (select 1 from pg_policy p where p.polrelid = c.oid) $$,
  'every public table has at least one explicit policy'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r'
       and has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') $$,
  'anon has no table privileges on any public table'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r'
       and has_any_column_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,REFERENCES') $$,
  'anon has no column privileges on any public table'
);

select is(has_schema_privilege('anon', 'private', 'USAGE'), false, 'anon cannot use the private schema');

select is(has_function_privilege('anon', 'public.claim_student_record()', 'EXECUTE'), false,
          'anon cannot execute claim_student_record');
select is(has_function_privilege('anon', 'public.complete_onboarding(text)', 'EXECUTE'), false,
          'anon cannot execute complete_onboarding');
select is(has_function_privilege('anon', 'public.get_my_recommended_actions()', 'EXECUTE'), false,
          'anon cannot execute get_my_recommended_actions');
select is(has_function_privilege('anon', 'public.admin_set_user_role(uuid, text)', 'EXECUTE'), false,
          'anon cannot execute admin_set_user_role');

select is_empty(
  $$ select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname in ('public', 'private') and p.prosecdef
       and not coalesce(array_to_string(p.proconfig, ',') like '%search_path=%', false) $$,
  'every SECURITY DEFINER function pins search_path'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'r'
       and has_table_privilege('authenticated', c.oid, 'TRUNCATE,REFERENCES,TRIGGER') $$,
  'authenticated has no TRUNCATE/REFERENCES/TRIGGER privileges'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public'
       and c.relname in ('risk_predictions', 'risk_factors', 'engagement_events', 'audit_logs', 'notifications',
                         'model_registry', 'model_monitoring_snapshots', 'drift_alerts', 'system_events',
                         'intervention_outcome_measures')
       and has_table_privilege('authenticated', c.oid, 'INSERT,DELETE') $$,
  'server-only tables cannot be inserted into or deleted from by authenticated'
);

select is_empty(
  $$ select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public'
       and c.relname in ('risk_predictions', 'risk_factors', 'engagement_events', 'audit_logs')
       and has_any_column_privilege('authenticated', c.oid, 'UPDATE') $$,
  'predictions, factors, engagement and audit rows are immutable to authenticated'
);

select is_empty(
  $$ select column_name from information_schema.column_privileges
     where table_schema = 'public' and table_name = 'profiles' and grantee = 'authenticated'
       and privilege_type = 'UPDATE' and column_name <> 'full_name' $$,
  'authenticated can update only profiles.full_name'
);

select is_empty(
  $$ select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and has_function_privilege('anon', p.oid, 'EXECUTE') $$,
  'anon cannot execute any public function');
select is(has_any_column_privilege('authenticated', 'public.interventions', 'INSERT'), false,
          'interventions are created only through RPCs');
select is(has_table_privilege('authenticated', 'private.feature_snapshots', 'SELECT,INSERT,UPDATE,DELETE'), false,
          'feature snapshots are not reachable by API users');
select is(has_table_privilege('authenticated', 'private.ml_subject_map', 'SELECT,INSERT,UPDATE,DELETE'), false,
          'the ML identity map is not reachable by API users');
select isnt_empty(
  $$ select 1 from pg_publication_tables where pubname = 'supabase_realtime' and tablename = 'notifications' $$,
  'notifications are published to Realtime');
select is_empty(
  $$ select tablename from pg_publication_tables where pubname = 'supabase_realtime' and tablename <> 'notifications' $$,
  'no other table is published to Realtime');

select has_index('public', 'students', 'students_programme_id_idx', 'index: students.programme_id');
select has_index('public', 'courses', 'courses_programme_id_idx', 'index: courses.programme_id');
select has_index('public', 'student_courses', 'student_courses_course_id_idx', 'index: student_courses.course_id');
select has_index('public', 'student_courses', 'student_courses_institution_id_idx', 'index: student_courses.institution_id');
select has_index('public', 'attendance_records', 'attendance_records_student_date_idx', 'index: attendance (student_id, attendance_date)');
select has_index('public', 'attendance_records', 'attendance_records_course_date_idx', 'index: attendance (course_id, attendance_date)');
select has_index('public', 'assignments', 'assignments_course_year_due_idx', 'index: assignments due dates');
select has_index('public', 'assignment_submissions', 'assignment_submissions_student_id_idx', 'index: submissions.student_id');
select has_index('public', 'risk_predictions', 'risk_predictions_prediction_date_idx', 'index: risk_predictions.prediction_date');
select has_index('public', 'interventions', 'interventions_status_idx', 'index: interventions.status');
select has_index('public', 'interventions', 'interventions_student_created_idx', 'index: interventions (student_id, created_at)');
select has_index('public', 'notifications', 'notifications_recipient_created_idx', 'index: notifications (recipient_id, created_at)');
select has_index('public', 'audit_logs', 'audit_logs_institution_created_idx', 'index: audit_logs (institution_id, created_at)');
select has_index('public', 'engagement_events', 'engagement_events_student_occurred_idx', 'index: engagement (student_id, occurred_at)');
select has_index('public', 'mentor_assignments', 'mentor_assignments_institution_id_idx', 'index: mentor_assignments.institution_id');

select * from finish();
rollback;
