-- Schema 4.1.0: rule suggestions record the rule-set version that produced them.
begin;
select plan(13);

select tests.create_fixture();

select has_column('public', 'interventions', 'rule_version', 'interventions record the rule-set version');
select is((select version from public.get_platform_versions() where component = 'database_schema'), '4.1.0',
          'the schema version reflects the rules-version change');

-- ============================================================ server-side writes
select tests.clear_authentication();
select lives_ok(
  format($$ insert into public.interventions (id, student_id, intervention_type, status, source, reason, priority,
                                              rule_id, rule_version)
            values (%L, %L, 'attendance_follow_up', 'recommended', 'model_rule',
                    'Attendance in the last 14 days was 50%%, below the 75%% requirement.', 'high',
                    'attendance.below_requirement', 'rules-1.0.0') $$,
         tests.uid('iv_rule_s1'), tests.uid('student_s1')),
  'rule output is stored with its rule id and rule-set version');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, status, source, reason, rule_id)
            values (%L, 'study_planning', 'recommended', 'model_rule', 'Rule output', 'engagement.inactive') $$,
         tests.uid('student_s1')),
  '23514', 'sews:rule_id_and_version_required_together', 'a rule id without a rule-set version is refused');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, status, source, reason, rule_version)
            values (%L, 'study_planning', 'recommended', 'model_rule', 'Rule output', 'rules-1.0.0') $$,
         tests.uid('student_s1')),
  '23514', 'sews:rule_id_and_version_required_together', 'a rule-set version without a rule id is refused');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, status, source, reason, rule_id, rule_version)
            values (%L, 'study_planning', 'recommended', 'model_rule', 'Rule output', 'engagement.inactive', 'v1') $$,
         tests.uid('student_s1')),
  '23514', null, 'a malformed rule-set version is refused');
select throws_ok(
  format($$ insert into public.interventions (student_id, intervention_type, status, source, reason, rule_id, rule_version)
            values (%L, 'study_planning', 'recommended', 'mentor', 'Staff idea', 'engagement.inactive', 'rules-1.0.0') $$,
         tests.uid('student_s1')),
  '23514', 'sews:rule_provenance_only_for_rule_output', 'staff-created interventions cannot claim rule provenance');
select throws_ok(
  format($$ update public.interventions set rule_version = 'rules-9.9.9' where id = %L $$, tests.uid('iv_rule_s1')),
  '23514', 'sews:rule_provenance_is_immutable', 'the stored rule-set version cannot be changed');
select throws_ok(
  format($$ update public.interventions set rule_id = 'assignments.missed' where id = %L $$, tests.uid('iv_rule_s1')),
  '23514', 'sews:rule_provenance_is_immutable', 'the stored rule id cannot be changed');

-- A suggestion created before schema 4.1.0 (rule id, no version) keeps working through the workflow.
alter table public.interventions disable trigger enforce_rule_provenance;
insert into public.interventions (id, student_id, intervention_type, status, source, reason, rule_id)
values (tests.uid('iv_legacy_s1'), tests.uid('student_s1'), 'study_planning', 'recommended', 'model_rule',
        'Suggestion stored before rule-set versions were recorded', 'legacy_rule');
alter table public.interventions enable trigger enforce_rule_provenance;
select lives_ok(
  format($$ update public.interventions set status = 'pending' where id = %L $$, tests.uid('iv_legacy_s1')),
  'a suggestion stored before rule-set versions were recorded can still be offered');
select is((select rule_version from public.interventions where id = tests.uid('iv_legacy_s1')), null,
          'older suggestions are not back-filled with a version that cannot be proven');

-- ==================================================================== clients
select tests.authenticate_as(tests.uid('user_m1'));
select isnt_empty(format('select 1 from public.interventions where id = %L and rule_version = %L',
                         tests.uid('iv_rule_s1'), 'rules-1.0.0'),
                  'the mentor sees which rule-set version produced the suggestion');
select throws_ok(
  format($$ update public.interventions set rule_version = 'rules-2.0.0' where id = %L $$, tests.uid('iv_rule_s1')),
  '42501', null, 'clients cannot write rule provenance');

select * from finish();
rollback;
