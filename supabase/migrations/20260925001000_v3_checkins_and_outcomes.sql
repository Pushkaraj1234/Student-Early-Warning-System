-- SEWS 0010 (V3) — optional student check-ins and intervention outcome measures.
--
-- Check-ins ask only about SUPPORT NEEDS (academic difficulty, workload, time management, course
-- difficulty, financial difficulty, study challenges). They never ask about, record or infer
-- mental-health conditions. Nothing is inferred from them automatically except that an explicit
-- request (contact / financial difficulty) alerts the student's mentor for human follow-up.
--
-- Outcome measures are DESCRIPTIVE before/after indicators around an intervention. They do not
-- show that an intervention caused a change (see docs/ml/intervention-outcomes.md).
-- Idempotent: safe to re-run.

create or replace function private.has_no_duplicates(p_values text[])
returns boolean
language sql immutable
set search_path = ''
as $$
  select cardinality(p_values) = (select count(distinct v) from unnest(p_values) as v);
$$;

revoke all on function private.has_no_duplicates(text[]) from public, anon;
grant execute on function private.has_no_duplicates(text[]) to authenticated, service_role;

-- ============================================================ student_checkins
create table if not exists public.student_checkins (
  id             uuid primary key default gen_random_uuid(),
  student_id     uuid not null references public.students (id) on delete cascade,
  support_needs  text[] not null default '{}',
  wants_contact  boolean not null default false,
  comment        text,
  submitted_at   timestamptz not null default now(),
  constraint student_checkins_needs_check check (
    support_needs <@ array['academic_difficulty', 'workload', 'time_management', 'course_difficulty',
                           'financial_difficulty', 'study_challenges']::text[]
    and private.has_no_duplicates(support_needs)
  ),
  constraint student_checkins_comment_length check (comment is null or char_length(btrim(comment)) between 1 and 500),
  constraint student_checkins_not_empty check (cardinality(support_needs) > 0 or wants_contact or comment is not null)
);

create index if not exists student_checkins_student_submitted_idx
  on public.student_checkins (student_id, submitted_at desc);

-- Server time only; at most 3 check-ins per student per 24 hours.
create or replace function private.guard_student_checkin()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
begin
  new.submitted_at := now();
  if (select count(*) from public.student_checkins c
      where c.student_id = new.student_id and c.submitted_at > now() - interval '24 hours') >= 3 then
    raise exception 'sews:rate_limited' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

create or replace function private.notify_checkin()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_student record;
  v_mentor uuid;
begin
  if not (new.wants_contact or 'financial_difficulty' = any (new.support_needs)) then
    return null;
  end if;
  select s.full_name, s.roll_number into v_student from public.students s where s.id = new.student_id;
  for v_mentor in select private.active_mentor_ids(new.student_id) loop
    perform private.notify(
      v_mentor, 'student_checkin', 'A student asked for support',
      format('%s (%s) submitted a check-in that needs follow-up. Open SEWS to review it.',
             v_student.full_name, v_student.roll_number),
      'You have a new update in SEWS.'
    );
  end loop;
  return null;
end;
$$;

revoke all on function private.guard_student_checkin(), private.notify_checkin() from public, anon, authenticated;

drop trigger if exists guard_student_checkin on public.student_checkins;
create trigger guard_student_checkin before insert on public.student_checkins
  for each row execute function private.guard_student_checkin();
drop trigger if exists notify_checkin on public.student_checkins;
create trigger notify_checkin after insert on public.student_checkins
  for each row execute function private.notify_checkin();

alter table public.student_checkins enable row level security;
revoke all on table public.student_checkins from anon, authenticated;
grant select on table public.student_checkins to authenticated;
grant insert (student_id, support_needs, wants_contact, comment) on table public.student_checkins to authenticated;
grant all on table public.student_checkins to service_role;

drop policy if exists student_checkins_select on public.student_checkins;
create policy student_checkins_select on public.student_checkins for select to authenticated
  using (private.can_view_student_personal(student_id));
drop policy if exists student_checkins_insert on public.student_checkins;
create policy student_checkins_insert on public.student_checkins for insert to authenticated
  with check (student_id = (select private.current_student_id()));
-- UPDATE / DELETE: no policy (append-only; erasure cascades from students).

-- =============================================== intervention_outcome_measures
create table if not exists public.intervention_outcome_measures (
  id               uuid primary key default gen_random_uuid(),
  intervention_id  uuid not null references public.interventions (id) on delete cascade,
  indicator        text not null,
  baseline_value   numeric,
  followup_value   numeric,
  baseline_start   date not null,
  baseline_end     date not null,
  followup_start   date not null,
  followup_end     date not null,
  method_version   text not null,
  computed_at      timestamptz not null default now(),
  constraint intervention_outcome_measures_key unique (intervention_id, indicator, method_version),
  constraint intervention_outcome_measures_indicator_check check (indicator in (
    'attendance_rate', 'assignment_completion_rate', 'mean_score_pct', 'risk_probability'
  )),
  constraint intervention_outcome_measures_windows_check check (
    baseline_end >= baseline_start and followup_end >= followup_start and followup_start > baseline_end
  ),
  constraint intervention_outcome_measures_method_format check (method_version ~ '^[a-z0-9][a-z0-9._-]{0,63}$')
);

alter table public.intervention_outcome_measures enable row level security;
revoke all on table public.intervention_outcome_measures from anon, authenticated;
grant select on table public.intervention_outcome_measures to authenticated;
grant all on table public.intervention_outcome_measures to service_role;

-- Visible exactly when the intervention is visible (mentor of the student / institution admin).
drop policy if exists intervention_outcome_measures_select on public.intervention_outcome_measures;
create policy intervention_outcome_measures_select on public.intervention_outcome_measures
  for select to authenticated
  using (exists (select 1 from public.interventions i where i.id = intervention_outcome_measures.intervention_id));

do $$
declare
  v_table text;
begin
  foreach v_table in array array['student_checkins'] loop
    execute format('drop trigger if exists write_audit_log on public.%I', v_table);
    execute format(
      'create trigger write_audit_log after insert or update or delete on public.%I '
      'for each row execute function private.write_audit_log()', v_table);
  end loop;
end
$$;
