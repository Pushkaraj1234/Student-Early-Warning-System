-- SEWS 0008 — RPC functions exposed to signed-in users.
-- All are SECURITY DEFINER with an empty search_path, derive identity from auth.uid()
-- only, and are not executable by anon. Errors use stable 'sews:<code>' messages
-- that the mobile app maps to user-facing text.
-- Idempotent: safe to re-run.

-- ------------------------------------------------------- claim_student_record
-- Links the signed-in account to the institution-created student record whose
-- institutional email equals the account's CONFIRMED email. Idempotent.
create or replace function public.claim_student_record()
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_role text;
  v_email text;
  v_email_confirmed_at timestamptz;
  v_student_id uuid;
  v_institution_id uuid;
  v_matches integer;
begin
  if v_user_id is null then
    raise exception 'sews:not_authenticated' using errcode = '42501';
  end if;

  select p.role into v_role from public.profiles p where p.id = v_user_id;
  if v_role is distinct from 'student' then
    raise exception 'sews:not_a_student' using errcode = '42501';
  end if;

  select s.id into v_student_id from public.students s where s.user_id = v_user_id;
  if v_student_id is not null then
    return v_student_id;
  end if;

  select lower(u.email), u.email_confirmed_at
    into v_email, v_email_confirmed_at
  from auth.users u
  where u.id = v_user_id;

  if v_email_confirmed_at is null then
    raise exception 'sews:email_not_confirmed' using errcode = 'P0001';
  end if;

  select count(*) into v_matches
  from public.students s
  where s.institutional_email = v_email and s.user_id is null;

  if v_matches = 0 then
    raise exception 'sews:no_matching_student_record' using errcode = 'P0001';
  elsif v_matches > 1 then
    raise exception 'sews:ambiguous_student_record' using errcode = 'P0001';
  end if;

  update public.students s
     set user_id = v_user_id
   where s.institutional_email = v_email and s.user_id is null
  returning s.id, s.institution_id into v_student_id, v_institution_id;

  update public.profiles p
     set institution_id = v_institution_id
   where p.id = v_user_id;

  return v_student_id;
end;
$$;

-- -------------------------------------------------------- complete_onboarding
create or replace function public.complete_onboarding(p_privacy_notice_version text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
begin
  if v_user_id is null then
    raise exception 'sews:not_authenticated' using errcode = '42501';
  end if;

  if p_privacy_notice_version is null
     or p_privacy_notice_version !~ '^v[0-9]+(\.[0-9]+){0,2}$' then
    raise exception 'sews:invalid_privacy_notice_version' using errcode = '22023';
  end if;

  if private.current_student_id() is null then
    raise exception 'sews:student_record_not_linked' using errcode = 'P0001';
  end if;

  update public.profiles p
     set onboarding_completed_at = coalesce(p.onboarding_completed_at, now()),
         privacy_notice_version = p_privacy_notice_version
   where p.id = v_user_id;
end;
$$;

-- ------------------------------------------------ get_my_recommended_actions
-- Student-safe projection of open interventions: no notes, no staff identifiers.
create or replace function public.get_my_recommended_actions()
returns table (
  id uuid,
  intervention_type text,
  status text,
  due_on date,
  prediction_id uuid,
  created_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  select i.id, i.intervention_type, i.status, i.due_on, i.prediction_id, i.created_at
  from public.interventions i
  where i.student_id = private.current_student_id()
    and i.status in ('recommended', 'planned', 'in_progress')
  order by i.created_at desc
  limit 20;
$$;

-- ---------------------------------------------------------- admin_set_user_role
-- An admin may change the role of another user in their own institution.
create or replace function public.admin_set_user_role(p_user_id uuid, p_role text)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor_id uuid := (select auth.uid());
  v_actor_institution_id uuid;
  v_target_institution_id uuid;
begin
  if v_actor_id is null then
    raise exception 'sews:not_authenticated' using errcode = '42501';
  end if;

  if p_role is null or p_role not in ('student', 'mentor', 'faculty', 'admin') then
    raise exception 'sews:invalid_role' using errcode = '22023';
  end if;

  select p.institution_id into v_actor_institution_id
  from public.profiles p
  where p.id = v_actor_id and p.role = 'admin';

  if v_actor_institution_id is null then
    raise exception 'sews:not_an_admin' using errcode = '42501';
  end if;

  if p_user_id = v_actor_id then
    raise exception 'sews:cannot_change_own_role' using errcode = 'P0001';
  end if;

  select p.institution_id into v_target_institution_id
  from public.profiles p
  where p.id = p_user_id;

  if v_target_institution_id is distinct from v_actor_institution_id then
    raise exception 'sews:user_not_in_institution' using errcode = '42501';
  end if;

  if p_role <> 'student' and exists (select 1 from public.students s where s.user_id = p_user_id) then
    raise exception 'sews:linked_student_cannot_be_staff' using errcode = 'P0001';
  end if;

  update public.profiles p set role = p_role where p.id = p_user_id;
end;
$$;

revoke all on function
  public.claim_student_record(),
  public.complete_onboarding(text),
  public.get_my_recommended_actions(),
  public.admin_set_user_role(uuid, text)
from public, anon;

grant execute on function
  public.claim_student_record(),
  public.complete_onboarding(text),
  public.get_my_recommended_actions(),
  public.admin_set_user_role(uuid, text)
to authenticated, service_role;
