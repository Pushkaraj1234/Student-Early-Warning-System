-- Sign-up never trusts client-supplied roles; students link their record only via a
-- confirmed institutional email; onboarding is recorded server-side.
begin;
select plan(18);

select tests.create_fixture();

-- ------------------------------------------------ sign-up ignores client roles
select tests.create_user(
  tests.uid('user_meta'), 'meta@test-a.example.com', true,
  jsonb_build_object('full_name', 'Meta Person', 'role', 'admin', 'institution_id', tests.uid('inst_b'))
);
select is((select role from public.profiles where id = tests.uid('user_meta')), 'student',
          'a role sent in sign-up metadata is ignored (profile is student)');
select is((select institution_id from public.profiles where id = tests.uid('user_meta')), null::uuid,
          'an institution sent in sign-up metadata is ignored');
select is((select full_name from public.profiles where id = tests.uid('user_meta')), 'Meta Person',
          'the display name from sign-up metadata is kept');

-- The trigger must also work when the auth service (not a superuser) inserts the user.
select case when pg_has_role(session_user, 'supabase_auth_admin', 'MEMBER')
  then lives_ok(
    format($$ do $do$ begin
                perform set_config('role', 'supabase_auth_admin', true);
                insert into auth.users (id, email, email_confirmed_at, raw_user_meta_data, raw_app_meta_data, aud, role)
                values (%L, 'authsvc@test-a.example.com', now(), '{}', '{}', 'authenticated', 'authenticated');
                perform set_config('role', session_user::text, true);
              end $do$ $$, tests.uid('user_authsvc')),
    'sign-up performed by the auth service role succeeds')
  else skip('cannot assume supabase_auth_admin in this environment', 1)
end;
select case when pg_has_role(session_user, 'supabase_auth_admin', 'MEMBER')
  then isnt_empty(format('select 1 from public.profiles where id = %L', tests.uid('user_authsvc')),
                  'the auth service sign-up created a profile')
  else skip('cannot assume supabase_auth_admin in this environment', 1)
end;

-- ------------------------------------------------------- claim_student_record
select tests.authenticate_as(tests.uid('user_s4'));
select throws_ok($$ select public.claim_student_record() $$, 'P0001', 'sews:email_not_confirmed',
                 'an unconfirmed email cannot claim a student record');

select tests.clear_authentication();
update auth.users set email_confirmed_at = now() where id = tests.uid('user_s4');
select tests.authenticate_as(tests.uid('user_s4'));

select is(public.claim_student_record(), tests.uid('student_s4'),
          'a confirmed institutional email claims the matching student record');
select is((select institution_id from public.profiles where id = tests.uid('user_s4')), tests.uid('inst_a'),
          'claiming sets the profile institution server-side');
select set_eq($$ select id from public.students $$, array[tests.uid('student_s4')],
              'after claiming, the student sees exactly their record');
select is(public.claim_student_record(), tests.uid('student_s4'), 'claiming is idempotent');

-- -------------------------------------------------------- complete_onboarding
select throws_ok($$ select public.complete_onboarding('latest') $$, '22023', 'sews:invalid_privacy_notice_version',
                 'an invalid privacy notice version is rejected');
select lives_ok($$ select public.complete_onboarding('v1') $$, 'a linked student can complete onboarding');
select isnt((select onboarding_completed_at from public.profiles where id = tests.uid('user_s4')), null::timestamptz,
            'onboarding completion time is recorded');
select is((select privacy_notice_version from public.profiles where id = tests.uid('user_s4')), 'v1',
          'the accepted privacy notice version is recorded');

-- --------------------------------------------------------------- failure paths
select tests.clear_authentication();
select tests.create_user(tests.uid('user_nomatch'), 'nomatch@test-a.example.com');
select tests.authenticate_as(tests.uid('user_nomatch'));
select throws_ok($$ select public.claim_student_record() $$, 'P0001', 'sews:no_matching_student_record',
                 'an email with no institutional record cannot claim anything');
select throws_ok($$ select public.complete_onboarding('v1') $$, 'P0001', 'sews:student_record_not_linked',
                 'onboarding requires a linked student record');

select tests.authenticate_as(tests.uid('user_m1'));
select throws_ok($$ select public.claim_student_record() $$, '42501', 'sews:not_a_student',
                 'staff accounts cannot claim student records');
select is_empty($$ select * from public.get_my_recommended_actions() $$,
                'staff accounts get no student recommended actions');

select * from finish();
rollback;
