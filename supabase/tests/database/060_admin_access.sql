-- Admin scope: full administrative access within their own institution only.
begin;
select plan(32);

select tests.create_fixture();
select tests.authenticate_as(tests.uid('user_a1'));

-- --------------------------------------------------- reads: own institution
select set_eq($$ select id from public.students $$,
              array[tests.uid('student_s1'), tests.uid('student_s2'), tests.uid('student_s4')],
              'admin sees all students of their institution');
select set_eq($$ select id from public.risk_predictions $$, array[tests.uid('pred_s1'), tests.uid('pred_s2')],
              'admin sees predictions of their institution only');
select set_eq($$ select id from public.interventions $$, array[tests.uid('iv_s1'), tests.uid('iv_s2')],
              'admin sees interventions of their institution only');
select set_eq($$ select id from public.academic_records $$, array[tests.uid('ar_s1'), tests.uid('ar_s2')],
              'admin sees academic records of their institution only');
select set_eq($$ select id from public.institutions $$, array[tests.uid('inst_a')],
              'admin sees only their own institution');
select set_eq($$ select id from public.profiles $$,
              array[tests.uid('user_s1'), tests.uid('user_s2'), tests.uid('user_m1'),
                    tests.uid('user_f1'), tests.uid('user_a1')],
              'admin sees profiles of their institution only');
select is_empty(format('select * from public.students where institution_id = %L', tests.uid('inst_b')),
                'admin cannot access another institution''s students');
select is_empty(format('select * from public.profiles where institution_id = %L', tests.uid('inst_b')),
                'admin cannot access another institution''s profiles');
select is_empty(format('select * from public.audit_logs where institution_id is distinct from %L', tests.uid('inst_a')),
                'admin sees only their institution''s audit entries');
select isnt_empty($$ select * from public.audit_logs $$, 'admin can read their institution''s audit trail');
select is_empty($$ select * from public.notifications $$, 'admin cannot read other users'' notifications');

-- ---------------------------------------------------------------- writes
select is(tests.affected_rows(format('update public.institutions set name = %L where id = %L',
                                     'Test Institution A Renamed', tests.uid('inst_a'))),
          1, 'admin can rename their own institution');
select is(tests.affected_rows(format('update public.institutions set name = %L where id = %L',
                                     'Hijacked', tests.uid('inst_b'))),
          0, 'admin cannot rename another institution');
select lives_ok(
  format($$ insert into public.courses (institution_id, department_id, code, title, credits, semester_number)
            values (%L, %L, 'TA201', 'New Course', 4, 2) $$, tests.uid('inst_a'), tests.uid('dept_a')),
  'admin can create courses in their institution');
select throws_ok(
  format($$ insert into public.courses (institution_id, department_id, code, title, credits, semester_number)
            values (%L, %L, 'TB201', 'Foreign Course', 4, 2) $$, tests.uid('inst_b'), tests.uid('dept_b')),
  '42501', null, 'admin cannot create courses in another institution');
select throws_ok(
  format($$ insert into public.students (institution_id, programme_id, roll_number, full_name, institutional_email,
            admission_year, current_semester) values (%L, %L, 'TB999', 'Foreign Student', 'x@test-b.example.com', 2026, 1) $$,
         tests.uid('inst_b'), tests.uid('prog_b')),
  '42501', null, 'admin cannot create students in another institution');
select lives_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, sgpa, cgpa,
            credits_registered, credits_earned, result_status) values (%L, '2025-26', 2, 8.5, 8.25, 20, 20, 'pass') $$,
         tests.uid('student_s1')),
  'admin can publish semester results for their students');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, credits_registered,
            credits_earned, result_status) values (%L, '2025-26', 2, 0, 0, 'pending') $$, tests.uid('student_s3')),
  '42501', null, 'admin cannot publish results for another institution');
select is(tests.affected_rows(format('update public.academic_records set sgpa = 9 where id = %L', tests.uid('ar_s3'))),
          0, 'admin cannot change another institution''s results');
select lives_ok(
  format($$ insert into public.mentor_assignments (institution_id, mentor_id, student_id)
            values (%L, %L, %L) $$, tests.uid('inst_a'), tests.uid('user_m1'), tests.uid('student_s2')),
  'admin can assign a mentor of their institution');
select throws_ok(
  format($$ insert into public.mentor_assignments (institution_id, mentor_id, student_id)
            values (%L, %L, %L) $$, tests.uid('inst_a'), tests.uid('user_m2'), tests.uid('student_s4')),
  '23514', null, 'admin cannot assign a mentor from another institution');
select throws_ok(
  format($$ insert into public.risk_predictions (student_id, prediction_date, risk_probability, risk_level,
            model_version, feature_version, dataset_version, data_provenance)
            values (%L, date '2026-09-21', 0.5, 'watch', 'forged', 'forged', 'forged', 'synthetic') $$,
         tests.uid('student_s1')),
  '42501', null, 'admin cannot insert risk predictions (server-side only)');
select throws_ok(
  format('delete from public.students where id = %L', tests.uid('student_s2')),
  '42501', null, 'admin cannot delete students (service-role erasure only)');

-- --------------------------------------------------------------- roles
select lives_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_f1'), 'mentor'),
  'admin can change the role of a staff member in their institution');
select is((select role from public.profiles where id = tests.uid('user_f1')), 'mentor',
          'the role change took effect');
select throws_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_m2'), 'faculty'),
  '42501', 'sews:user_not_in_institution', 'admin cannot change roles in another institution');
select throws_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_a1'), 'mentor'),
  'P0001', 'sews:cannot_change_own_role', 'admin cannot change their own role');
select throws_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_m1'), 'superuser'),
  '22023', 'sews:invalid_role', 'invalid roles are rejected');
select throws_ok(
  format('select public.admin_set_user_role(%L, %L)', tests.uid('user_s1'), 'admin'),
  'P0001', 'sews:linked_student_cannot_be_staff', 'a linked student account cannot become staff');
select throws_ok(
  format('update public.profiles set role = %L where id = %L', 'admin', tests.uid('user_m1')),
  '42501', null, 'roles cannot be changed by direct UPDATE, even by an admin');

-- --------------------------------------------------- other institution's admin
select tests.authenticate_as(tests.uid('user_a2'));
select set_eq($$ select id from public.students $$, array[tests.uid('student_s3')],
              'institution B admin sees only institution B students');
select is_empty(
  format('select * from public.risk_predictions where student_id in (%L, %L)', tests.uid('student_s1'), tests.uid('student_s2')),
  'institution B admin cannot read institution A predictions');

select * from finish();
rollback;
