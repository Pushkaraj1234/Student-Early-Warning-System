-- SEWS 0009 (V2) — longitudinal monitoring.
--   * academic_terms: gives the "current semester" feature window
--   * lms_integrations + canonical engagement_events (vendor-neutral, no raw payloads)
--   * risk trajectory computed in the database for every new prediction
--   * intervention workflow (create / assign / offer / accept / decline / complete / cancel)
--   * notification types, generic push previews, delivery state, mentor messages
--   * Realtime publication for notifications (RLS applies to postgres_changes)
--   * mentor caseload and weekly trend functions (SECURITY INVOKER: RLS decides scope)
-- Idempotent: safe to re-run.

-- ============================================================ academic_terms
-- Indian semester calendar: odd semesters (1,3,5,…) run in the 'odd' term, even semesters in
-- the 'even' term of the same academic year. The institution records the actual dates.
create table if not exists public.academic_terms (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  academic_year   text not null,
  term            text not null,
  starts_on       date not null,
  ends_on         date not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint academic_terms_key unique (institution_id, academic_year, term),
  constraint academic_terms_year_format check (academic_year ~ '^[0-9]{4}-[0-9]{2}$'),
  constraint academic_terms_term_check check (term in ('odd', 'even', 'summer')),
  constraint academic_terms_dates_check check (ends_on > starts_on)
);

drop trigger if exists set_updated_at on public.academic_terms;
create trigger set_updated_at before update on public.academic_terms
  for each row execute function private.set_updated_at();

alter table public.academic_terms enable row level security;
revoke all on table public.academic_terms from anon, authenticated;
grant select, delete on table public.academic_terms to authenticated;
grant insert (institution_id, academic_year, term, starts_on, ends_on) on table public.academic_terms to authenticated;
grant update (starts_on, ends_on) on table public.academic_terms to authenticated;
grant all on table public.academic_terms to service_role;

drop policy if exists academic_terms_select on public.academic_terms;
create policy academic_terms_select on public.academic_terms for select to authenticated
  using (institution_id = (select private.current_institution_id()));
drop policy if exists academic_terms_insert on public.academic_terms;
create policy academic_terms_insert on public.academic_terms for insert to authenticated
  with check (private.is_admin_of(institution_id));
drop policy if exists academic_terms_update on public.academic_terms;
create policy academic_terms_update on public.academic_terms for update to authenticated
  using (private.is_admin_of(institution_id)) with check (private.is_admin_of(institution_id));
drop policy if exists academic_terms_delete on public.academic_terms;
create policy academic_terms_delete on public.academic_terms for delete to authenticated
  using (private.is_admin_of(institution_id));

-- ========================================================== lms_integrations
-- Registry of connected LMS sources. Credentials are NEVER stored here: they live in the
-- ingestion service's secret store. Adapters (services/sews_services/lms) normalise vendor
-- events into engagement_events.
create table if not exists public.lms_integrations (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  provider        text not null,
  display_name    text not null,
  status          text not null default 'active',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint lms_integrations_key unique (institution_id, provider, display_name),
  constraint lms_integrations_provider_check
    check (provider in ('moodle', 'canvas', 'google_classroom', 'blackboard', 'csv_import')),
  constraint lms_integrations_name_length check (char_length(btrim(display_name)) between 2 and 100),
  constraint lms_integrations_status_check check (status in ('active', 'paused', 'retired'))
);

drop trigger if exists set_updated_at on public.lms_integrations;
create trigger set_updated_at before update on public.lms_integrations
  for each row execute function private.set_updated_at();

alter table public.lms_integrations enable row level security;
revoke all on table public.lms_integrations from anon, authenticated;
grant select on table public.lms_integrations to authenticated;
grant insert (institution_id, provider, display_name, status) on table public.lms_integrations to authenticated;
grant update (display_name, status) on table public.lms_integrations to authenticated;
grant all on table public.lms_integrations to service_role;

drop policy if exists lms_integrations_select on public.lms_integrations;
create policy lms_integrations_select on public.lms_integrations for select to authenticated
  using (private.is_admin_of(institution_id));
drop policy if exists lms_integrations_insert on public.lms_integrations;
create policy lms_integrations_insert on public.lms_integrations for insert to authenticated
  with check (private.is_admin_of(institution_id));
drop policy if exists lms_integrations_update on public.lms_integrations;
create policy lms_integrations_update on public.lms_integrations for update to authenticated
  using (private.is_admin_of(institution_id)) with check (private.is_admin_of(institution_id));

-- ========================================================= engagement_events
-- Canonical, vendor-neutral event vocabulary. Legacy values are mapped.
alter table public.engagement_events drop constraint if exists engagement_events_event_type_check;
update public.engagement_events set event_type = 'resource_view'
  where event_type in ('content_view', 'resource_download');
update public.engagement_events set event_type = 'forum_activity' where event_type = 'forum_post';
alter table public.engagement_events add constraint engagement_events_event_type_check check (event_type in (
  'lms_login', 'resource_view', 'assignment_view', 'assignment_submission', 'quiz_attempt', 'forum_activity'
));

alter table public.engagement_events
  add column if not exists integration_id uuid references public.lms_integrations (id) on delete set null;
-- SHA-256 of the provider's event id: de-duplicates re-imports without storing the raw id.
alter table public.engagement_events add column if not exists external_event_hash text;
alter table public.engagement_events drop constraint if exists engagement_events_external_hash_format;
alter table public.engagement_events add constraint engagement_events_external_hash_format
  check (external_event_hash is null or external_event_hash ~ '^[0-9a-f]{64}$');
create unique index if not exists engagement_events_dedupe
  on public.engagement_events (integration_id, external_event_hash)
  where integration_id is not null and external_event_hash is not null;

-- ============================================================ risk trajectory
alter table public.risk_predictions add column if not exists target text not null default 'academic';
alter table public.risk_predictions add column if not exists scored_at timestamptz not null default now();
alter table public.risk_predictions
  add column if not exists previous_prediction_id uuid references public.risk_predictions (id) on delete set null;
alter table public.risk_predictions add column if not exists risk_delta numeric(6, 5);
alter table public.risk_predictions add column if not exists days_since_previous integer;
alter table public.risk_predictions add column if not exists risk_velocity_per_week numeric(8, 5);
alter table public.risk_predictions add column if not exists trajectory text not null default 'insufficient_history';

alter table public.risk_predictions drop constraint if exists risk_predictions_target_check;
alter table public.risk_predictions add constraint risk_predictions_target_check
  check (target in ('academic', 'dropout', 'course_failure', 'engagement'));
alter table public.risk_predictions drop constraint if exists risk_predictions_trajectory_check;
alter table public.risk_predictions add constraint risk_predictions_trajectory_check
  check (trajectory in ('improving', 'stable', 'increasing', 'rapidly_increasing', 'insufficient_history'));

-- One prediction per student, date, model version AND target.
alter table public.risk_predictions drop constraint if exists risk_predictions_student_date_model_key;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'risk_predictions_student_date_model_target_key') then
    alter table public.risk_predictions add constraint risk_predictions_student_date_model_target_key
      unique (student_id, prediction_date, model_version, target);
  end if;
end
$$;

create index if not exists risk_predictions_student_target_date_idx
  on public.risk_predictions (student_id, target, prediction_date desc);

-- Thresholds (see docs/ml/risk-trajectory.md for the rationale; PROVISIONAL until validated on
-- institutional data). Single source of truth for the database and the documentation.
create or replace function private.trajectory_thresholds(
  out stable_band numeric, out rapid_velocity_per_week numeric, out min_days_for_velocity integer
)
language sql immutable
set search_path = ''
as $$
  select 0.05::numeric, 0.10::numeric, 7;
$$;

create or replace function private.classify_trajectory(p_delta numeric, p_velocity_per_week numeric)
returns text
language sql immutable
set search_path = ''
as $$
  select case
    when p_delta is null then 'insufficient_history'
    when p_delta <= -t.stable_band then 'improving'
    when p_delta < t.stable_band then 'stable'
    when p_velocity_per_week is not null and p_velocity_per_week >= t.rapid_velocity_per_week then 'rapidly_increasing'
    else 'increasing'
  end
  from private.trajectory_thresholds() t;
$$;

-- Compares with the previous prediction of the SAME student, target and model version only:
-- probabilities from different model versions are not comparable. Velocity is computed only
-- when predictions are at least min_days_for_velocity apart.
create or replace function private.compute_risk_trajectory()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_prev record;
  v_days integer;
  v_t record;
begin
  select * into v_t from private.trajectory_thresholds();
  select rp.id, rp.risk_probability, rp.prediction_date
    into v_prev
  from public.risk_predictions rp
  where rp.student_id = new.student_id
    and rp.target = new.target
    and rp.model_version = new.model_version
    and rp.prediction_date < new.prediction_date
  order by rp.prediction_date desc, rp.scored_at desc
  limit 1;

  if not found then
    new.previous_prediction_id := null;
    new.risk_delta := null;
    new.days_since_previous := null;
    new.risk_velocity_per_week := null;
    new.trajectory := 'insufficient_history';
    return new;
  end if;

  v_days := new.prediction_date - v_prev.prediction_date;
  new.previous_prediction_id := v_prev.id;
  new.risk_delta := round(new.risk_probability - v_prev.risk_probability, 5);
  new.days_since_previous := v_days;
  new.risk_velocity_per_week := case
    when v_days >= v_t.min_days_for_velocity then round(new.risk_delta / (v_days / 7.0), 5)
  end;
  new.trajectory := private.classify_trajectory(new.risk_delta, new.risk_velocity_per_week);
  return new;
end;
$$;

revoke all on function private.trajectory_thresholds(), private.classify_trajectory(numeric, numeric),
  private.compute_risk_trajectory() from public, anon, authenticated;
grant execute on function private.trajectory_thresholds(), private.classify_trajectory(numeric, numeric)
  to service_role;

drop trigger if exists compute_risk_trajectory on public.risk_predictions;
create trigger compute_risk_trajectory before insert on public.risk_predictions
  for each row execute function private.compute_risk_trajectory();

-- ======================================================= notifications (V2)
alter table public.notifications drop constraint if exists notifications_type_check;
alter table public.notifications add constraint notifications_type_check check (notification_type in (
  'risk_update', 'intervention', 'assignment_due', 'attendance_alert', 'system',
  'new_intervention', 'risk_change', 'mentor_message', 'academic_signal', 'student_checkin'
));

-- Push previews come from a fixed, non-sensitive vocabulary; details stay in-app behind RLS.
alter table public.notifications add column if not exists preview text not null default 'You have a new update in SEWS.';
alter table public.notifications drop constraint if exists notifications_preview_check;
alter table public.notifications add constraint notifications_preview_check check (preview in (
  'You have a new update in SEWS.', 'You have a new message in SEWS.', 'A support option is available in SEWS.'
));
alter table public.notifications
  add column if not exists sender_id uuid references public.profiles (id) on delete set null;
alter table public.notifications add column if not exists delivery_status text not null default 'pending';
alter table public.notifications add column if not exists delivery_attempts integer not null default 0;
alter table public.notifications add column if not exists last_delivery_error text;
alter table public.notifications add column if not exists delivered_at timestamptz;
alter table public.notifications drop constraint if exists notifications_delivery_status_check;
alter table public.notifications add constraint notifications_delivery_status_check
  check (delivery_status in ('pending', 'sent', 'failed', 'skipped'));
alter table public.notifications drop constraint if exists notifications_delivery_error_check;
alter table public.notifications add constraint notifications_delivery_error_check check (
  last_delivery_error is null
  or last_delivery_error in ('no_device_token', 'provider_unavailable', 'invalid_token', 'rate_limited', 'unknown')
);
alter table public.notifications drop constraint if exists notifications_delivery_consistency;
alter table public.notifications add constraint notifications_delivery_consistency check (
  (delivery_status = 'sent') = (delivered_at is not null) and delivery_attempts >= 0
);
create index if not exists notifications_sender_created_idx on public.notifications (sender_id, created_at desc)
  where sender_id is not null;
create index if not exists notifications_delivery_pending_idx on public.notifications (created_at)
  where delivery_status = 'pending';

-- Internal helper used by triggers and RPCs.
create or replace function private.notify(
  p_recipient uuid, p_type text, p_title text, p_body text, p_preview text, p_sender uuid default null
)
returns void
language plpgsql security definer
set search_path = ''
as $$
begin
  if p_recipient is null then
    return;
  end if;
  insert into public.notifications (recipient_id, notification_type, title, body, preview, sender_id)
  values (p_recipient, p_type, left(p_title, 120), left(p_body, 1000), p_preview, p_sender);
end;
$$;

-- Active mentors of a student (profile ids).
create or replace function private.active_mentor_ids(p_student_id uuid)
returns setof uuid
language sql stable security definer
set search_path = ''
as $$
  select ma.mentor_id
  from public.mentor_assignments ma
  join public.profiles p on p.id = ma.mentor_id
  where ma.student_id = p_student_id
    and p.role = 'mentor'
    and p.institution_id = ma.institution_id
    and ma.starts_on <= current_date
    and (ma.ends_on is null or ma.ends_on >= current_date);
$$;

revoke all on function private.notify(uuid, text, text, text, text, uuid), private.active_mentor_ids(uuid)
  from public, anon, authenticated;

-- Risk change → the student's mentors (academic target only, to avoid alert fatigue). Students
-- are not sent risk-change alerts: they see their signal in the app without a push.
create or replace function private.notify_risk_change()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_prev_level text;
  v_student record;
  v_mentor uuid;
begin
  if new.target <> 'academic' then
    return null;
  end if;
  if new.previous_prediction_id is not null then
    select rp.risk_level into v_prev_level from public.risk_predictions rp where rp.id = new.previous_prediction_id;
  end if;
  if not (new.trajectory in ('increasing', 'rapidly_increasing')
          or (new.risk_level = 'high' and v_prev_level is distinct from 'high')) then
    return null;
  end if;
  select s.full_name, s.roll_number into v_student from public.students s where s.id = new.student_id;
  for v_mentor in select private.active_mentor_ids(new.student_id) loop
    perform private.notify(
      v_mentor, 'risk_change', 'Early-warning signal increased',
      format('%s (%s): signal is now %s; trajectory %s.', v_student.full_name, v_student.roll_number,
             new.risk_level, replace(new.trajectory, '_', ' ')),
      'You have a new update in SEWS.'
    );
  end loop;
  return null;
end;
$$;

drop trigger if exists notify_risk_change on public.risk_predictions;
create trigger notify_risk_change after insert on public.risk_predictions
  for each row execute function private.notify_risk_change();

-- Important academic signal: a semester result recorded as Fail → the student's mentors.
create or replace function private.notify_academic_signal()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_student record;
  v_mentor uuid;
begin
  if new.result_status <> 'fail' or (tg_op = 'UPDATE' and old.result_status = 'fail') then
    return null;
  end if;
  select s.full_name, s.roll_number into v_student from public.students s where s.id = new.student_id;
  for v_mentor in select private.active_mentor_ids(new.student_id) loop
    perform private.notify(
      v_mentor, 'academic_signal', 'Semester result needs attention',
      format('%s (%s): semester %s (%s) result recorded as Fail.', v_student.full_name, v_student.roll_number,
             new.semester, new.academic_year),
      'You have a new update in SEWS.'
    );
  end loop;
  return null;
end;
$$;

drop trigger if exists notify_academic_signal on public.academic_records;
create trigger notify_academic_signal after insert or update of result_status on public.academic_records
  for each row execute function private.notify_academic_signal();

revoke all on function private.notify_risk_change(), private.notify_academic_signal()
  from public, anon, authenticated;

-- Realtime: only notifications are published (live alert badges). Supabase Realtime applies the
-- table's RLS SELECT policy (recipient only) to postgres_changes subscribers.
do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime')
     and not exists (
       select 1 from pg_publication_tables
       where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'notifications'
     ) then
    alter publication supabase_realtime add table public.notifications;
  end if;
end
$$;

-- ============================================================ interventions (V2)
update public.interventions set status = 'pending' where status = 'planned';
update public.interventions set status = 'accepted' where status = 'in_progress';

alter table public.interventions drop constraint if exists interventions_status_check;
alter table public.interventions add constraint interventions_status_check
  check (status in ('recommended', 'pending', 'accepted', 'declined', 'completed', 'cancelled'));

alter table public.interventions drop constraint if exists interventions_type_check;
alter table public.interventions add constraint interventions_type_check check (intervention_type in (
  'mentor_meeting', 'academic_counselling', 'attendance_follow_up', 'assignment_support', 'peer_tutoring',
  'wellbeing_referral', 'study_planning', 'academic_tutoring', 'financial_support_referral'
));

alter table public.interventions add column if not exists reason text;
update public.interventions set reason = 'Recorded before reasons were required.' where reason is null;
alter table public.interventions alter column reason set not null;
alter table public.interventions drop constraint if exists interventions_reason_length;
alter table public.interventions add constraint interventions_reason_length
  check (char_length(btrim(reason)) between 3 and 500);

alter table public.interventions add column if not exists priority text not null default 'medium';
alter table public.interventions drop constraint if exists interventions_priority_check;
alter table public.interventions add constraint interventions_priority_check check (priority in ('low', 'medium', 'high'));

alter table public.interventions add column if not exists rule_id text;
alter table public.interventions drop constraint if exists interventions_rule_id_format;
alter table public.interventions add constraint interventions_rule_id_format
  check (rule_id is null or rule_id ~ '^[a-z0-9_.-]{1,64}$');
alter table public.interventions add column if not exists reviewed_by uuid references public.profiles (id) on delete set null;
alter table public.interventions add column if not exists reviewed_at timestamptz;
alter table public.interventions add column if not exists assigned_at timestamptz;
alter table public.interventions add column if not exists offered_at timestamptz;
alter table public.interventions add column if not exists responded_at timestamptz;
alter table public.interventions add column if not exists cancelled_at timestamptz;
alter table public.interventions add column if not exists decline_reason text;
alter table public.interventions drop constraint if exists interventions_decline_reason_check;
alter table public.interventions add constraint interventions_decline_reason_check check (
  decline_reason is null
  or (status = 'declined'
      and decline_reason in ('not_needed', 'already_receiving_support', 'not_convenient', 'other'))
);

-- No duplicate open interventions of the same type for a student.
create unique index if not exists interventions_one_open_per_type
  on public.interventions (student_id, intervention_type)
  where status in ('recommended', 'pending', 'accepted');

-- State machine. recommended → pending | cancelled; pending → accepted | declined | cancelled;
-- accepted → completed | cancelled. Timestamps are set here, never by clients.
create or replace function private.enforce_intervention_workflow()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.source = 'model_rule' and new.status <> 'recommended' then
      raise exception 'sews:rule_recommendations_require_review' using errcode = '23514';
    end if;
    if new.status not in ('recommended', 'pending') then
      raise exception 'sews:invalid_initial_intervention_status' using errcode = '23514';
    end if;
    if new.status = 'pending' then
      new.offered_at := now();
    end if;
    if new.assigned_to is not null then
      new.assigned_at := now();
    end if;
    return new;
  end if;

  if new.student_id is distinct from old.student_id or new.source is distinct from old.source
     or new.created_by is distinct from old.created_by
     or new.intervention_type is distinct from old.intervention_type then
    raise exception 'sews:intervention_identity_is_immutable' using errcode = '23514';
  end if;

  if new.status is distinct from old.status then
    if not (
      (old.status = 'recommended' and new.status in ('pending', 'cancelled'))
      or (old.status = 'pending' and new.status in ('accepted', 'declined', 'cancelled'))
      or (old.status = 'accepted' and new.status in ('completed', 'cancelled'))
    ) then
      raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
    end if;
    case new.status
      when 'pending' then new.offered_at := now();
      when 'accepted' then new.responded_at := now();
      when 'declined' then new.responded_at := now();
      when 'completed' then new.completed_at := now();
      when 'cancelled' then new.cancelled_at := now();
      else null;
    end case;
  end if;

  if new.assigned_to is distinct from old.assigned_to and new.assigned_to is not null then
    new.assigned_at := now();
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_intervention_workflow() from public, anon, authenticated;

drop trigger if exists enforce_intervention_workflow on public.interventions;
create trigger enforce_intervention_workflow before insert or update on public.interventions
  for each row execute function private.enforce_intervention_workflow();

-- The assigned staff member can also see and annotate the intervention (needed to complete it).
drop policy if exists interventions_select on public.interventions;
create policy interventions_select on public.interventions for select to authenticated
  using (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
    or assigned_to = (select auth.uid())
  );
drop policy if exists interventions_update on public.interventions;
create policy interventions_update on public.interventions for update to authenticated
  using (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
    or assigned_to = (select auth.uid())
  )
  with check (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
    or assigned_to = (select auth.uid())
  );

-- Clients change interventions only through the RPCs below (plus editing notes/due date).
revoke insert (student_id, prediction_id, intervention_type, status, source, assigned_to, due_on, notes)
  on table public.interventions from authenticated;
revoke update (status, assigned_to, outcome, completed_at) on table public.interventions from authenticated;
revoke delete on table public.interventions from authenticated;
grant update (notes, due_on) on table public.interventions to authenticated;

-- ------------------------------------------------------ intervention RPC helpers
create or replace function private.can_manage_student(p_student_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select private.is_mentor_of(p_student_id) or private.is_admin_of(private.student_institution_id(p_student_id));
$$;

revoke all on function private.can_manage_student(uuid) from public, anon;
grant execute on function private.can_manage_student(uuid) to authenticated, service_role;

create or replace function private.notify_intervention_offered(p_intervention_id uuid)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select i.id, i.intervention_type, i.assigned_to, i.created_by, s.user_id, s.full_name, s.roll_number
    into v
  from public.interventions i join public.students s on s.id = i.student_id
  where i.id = p_intervention_id;
  perform private.notify(v.user_id, 'new_intervention', 'A support option is available',
                         'Open SEWS to see the details and respond.', 'A support option is available in SEWS.');
  if v.assigned_to is not null and v.assigned_to is distinct from (select auth.uid()) then
    perform private.notify(v.assigned_to, 'new_intervention', 'Intervention assigned to you',
                           format('%s (%s): %s.', v.full_name, v.roll_number, replace(v.intervention_type, '_', ' ')),
                           'You have a new update in SEWS.');
  end if;
end;
$$;

revoke all on function private.notify_intervention_offered(uuid) from public, anon, authenticated;

-- --------------------------------------------------------------- RPCs
create or replace function public.create_intervention(
  p_student_id uuid,
  p_intervention_type text,
  p_reason text,
  p_priority text default 'medium',
  p_assigned_to uuid default null,
  p_due_on date default null,
  p_prediction_id uuid default null
)
returns uuid
language plpgsql security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_source text;
  v_id uuid;
begin
  if v_uid is null then
    raise exception 'sews:not_authenticated' using errcode = '42501';
  end if;
  if private.is_mentor_of(p_student_id) then
    v_source := 'mentor';
  elsif private.is_admin_of(private.student_institution_id(p_student_id)) then
    v_source := 'admin';
  else
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if p_reason is null or char_length(btrim(p_reason)) not between 3 and 500 then
    raise exception 'sews:invalid_reason' using errcode = '22023';
  end if;
  if p_priority is null or p_priority not in ('low', 'medium', 'high') then
    raise exception 'sews:invalid_priority' using errcode = '22023';
  end if;
  begin
    insert into public.interventions (student_id, prediction_id, intervention_type, status, source,
                                      assigned_to, due_on, reason, priority)
    values (p_student_id, p_prediction_id, p_intervention_type, 'pending', v_source,
            p_assigned_to, p_due_on, btrim(p_reason), p_priority)
    returning id into v_id;
  exception when unique_violation then
    raise exception 'sews:duplicate_intervention' using errcode = '23505';
  end;
  perform private.notify_intervention_offered(v_id);
  return v_id;
end;
$$;

-- Human review of a rule-engine recommendation: it becomes visible to the student only now.
create or replace function public.approve_recommendation(p_intervention_id uuid, p_assigned_to uuid default null)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v record;
begin
  select i.student_id, i.status into v from public.interventions i where i.id = p_intervention_id for update;
  if not found or not private.can_manage_student(v.student_id) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status <> 'recommended' then
    raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
  end if;
  update public.interventions i
     set status = 'pending', reviewed_by = v_uid, reviewed_at = now(),
         assigned_to = coalesce(p_assigned_to, i.assigned_to)
   where i.id = p_intervention_id;
  perform private.notify_intervention_offered(p_intervention_id);
end;
$$;

create or replace function public.assign_intervention(p_intervention_id uuid, p_assigned_to uuid)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select i.student_id, i.status, i.intervention_type into v
  from public.interventions i where i.id = p_intervention_id for update;
  if not found or not private.can_manage_student(v.student_id) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status not in ('recommended', 'pending', 'accepted') then
    raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
  end if;
  if p_assigned_to is null then
    raise exception 'sews:invalid_assignee' using errcode = '22023';
  end if;
  update public.interventions i set assigned_to = p_assigned_to where i.id = p_intervention_id;
  if p_assigned_to is distinct from (select auth.uid()) then
    perform private.notify(p_assigned_to, 'new_intervention', 'Intervention assigned to you',
                           replace(v.intervention_type, '_', ' '), 'You have a new update in SEWS.');
  end if;
end;
$$;

-- The student accepts or declines an offered (pending) intervention.
create or replace function public.respond_to_intervention(
  p_intervention_id uuid, p_accept boolean, p_decline_reason text default null
)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
  v_student uuid := private.current_student_id();
begin
  select i.student_id, i.status, i.assigned_to, i.reviewed_by, i.created_by into v
  from public.interventions i where i.id = p_intervention_id for update;
  if not found or v_student is null or v.student_id <> v_student then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status <> 'pending' then
    raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
  end if;
  if p_accept is null then
    raise exception 'sews:invalid_response' using errcode = '22023';
  end if;
  if p_accept then
    update public.interventions i set status = 'accepted', decline_reason = null where i.id = p_intervention_id;
  else
    if p_decline_reason is not null
       and p_decline_reason not in ('not_needed', 'already_receiving_support', 'not_convenient', 'other') then
      raise exception 'sews:invalid_decline_reason' using errcode = '22023';
    end if;
    update public.interventions i set status = 'declined', decline_reason = p_decline_reason
     where i.id = p_intervention_id;
  end if;
  perform private.notify(coalesce(v.assigned_to, v.reviewed_by, v.created_by), 'intervention',
                         case when p_accept then 'A student accepted a support option'
                              else 'A student declined a support option' end,
                         'Open SEWS to see the intervention.', 'You have a new update in SEWS.');
end;
$$;

create or replace function public.complete_intervention(p_intervention_id uuid, p_outcome text)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select i.student_id, i.status, i.assigned_to into v
  from public.interventions i where i.id = p_intervention_id for update;
  if not found or not (v.assigned_to = (select auth.uid()) or private.can_manage_student(v.student_id)) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status <> 'accepted' then
    raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
  end if;
  if p_outcome is null or p_outcome not in ('improved', 'no_change', 'worsened', 'not_assessed') then
    raise exception 'sews:invalid_outcome' using errcode = '22023';
  end if;
  update public.interventions i set status = 'completed', outcome = p_outcome where i.id = p_intervention_id;
end;
$$;

create or replace function public.cancel_intervention(p_intervention_id uuid)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select i.student_id, i.status, i.created_by into v
  from public.interventions i where i.id = p_intervention_id for update;
  if not found or not (v.created_by = (select auth.uid()) or private.can_manage_student(v.student_id)) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status not in ('recommended', 'pending', 'accepted') then
    raise exception 'sews:invalid_intervention_transition' using errcode = '23514';
  end if;
  update public.interventions i set status = 'cancelled' where i.id = p_intervention_id;
end;
$$;

-- Students see only interventions that were offered to them (never unreviewed recommendations).
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
    and i.status in ('pending', 'accepted')
  order by i.created_at desc
  limit 20;
$$;

-- -------------------------------------------------------- mentor messages
-- At most 20 messages per mentor per rolling hour.
create or replace function public.send_mentor_message(p_student_id uuid, p_body text)
returns uuid
language plpgsql security definer
set search_path = ''
as $$
declare
  v_uid uuid := (select auth.uid());
  v_user uuid;
  v_id uuid;
begin
  if v_uid is null or not private.is_mentor_of(p_student_id) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if p_body is null or char_length(btrim(p_body)) not between 1 and 1000 then
    raise exception 'sews:invalid_message' using errcode = '22023';
  end if;
  if (select count(*) from public.notifications n
      where n.sender_id = v_uid and n.created_at > now() - interval '1 hour') >= 20 then
    raise exception 'sews:rate_limited' using errcode = 'P0001';
  end if;
  select s.user_id into v_user from public.students s where s.id = p_student_id;
  if v_user is null then
    raise exception 'sews:student_not_linked' using errcode = 'P0001';
  end if;
  insert into public.notifications (recipient_id, notification_type, title, body, preview, sender_id)
  values (v_user, 'mentor_message', 'Message from your mentor', btrim(p_body), 'You have a new message in SEWS.', v_uid)
  returning id into v_id;
  return v_id;
end;
$$;

-- -------------------------------------------------- mentor / trend queries
-- SECURITY INVOKER: every row is filtered by the caller's RLS policies.
create or replace function public.get_mentor_caseload()
returns table (
  student_id uuid,
  full_name text,
  roll_number text,
  current_semester smallint,
  risk_level text,
  risk_probability numeric,
  trajectory text,
  risk_delta numeric,
  prediction_date date,
  data_provenance text,
  open_interventions integer
)
language sql
stable
security invoker
set search_path = ''
as $$
  select s.id, s.full_name, s.roll_number, s.current_semester,
         lp.risk_level, lp.risk_probability, lp.trajectory, lp.risk_delta, lp.prediction_date, lp.data_provenance,
         (select count(*)::integer from public.interventions i
          where i.student_id = s.id and i.status in ('recommended', 'pending', 'accepted'))
  from public.students s
  left join lateral (
    select rp.risk_level, rp.risk_probability, rp.trajectory, rp.risk_delta, rp.prediction_date, rp.data_provenance
    from public.risk_predictions rp
    where rp.student_id = s.id and rp.target = 'academic'
    order by rp.prediction_date desc, rp.scored_at desc
    limit 1
  ) lp on true
  where private.is_mentor_of(s.id)
  order by case lp.risk_level when 'high' then 0 when 'elevated' then 1 when 'watch' then 2
                              when 'stable' then 3 else 4 end,
           s.full_name;
$$;

create or replace function public.get_student_weekly_trends(p_student_id uuid, p_weeks integer default 12)
returns table (
  week_start date,
  attendance_attended integer,
  attendance_counted integer,
  assignments_due integer,
  assignments_submitted integer,
  mean_score_pct numeric,
  engagement_events integer,
  quiz_attempts integer
)
language plpgsql
stable
security invoker
set search_path = ''
as $$
begin
  if p_weeks is null or p_weeks < 1 or p_weeks > 52 then
    raise exception 'sews:invalid_argument' using errcode = '22023';
  end if;
  if not private.can_view_student(p_student_id) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  return query
  with weeks as (
    select (date_trunc('week', current_date)::date - 7 * g) as ws
    from generate_series(0, p_weeks - 1) as g
  )
  select
    w.ws,
    (select count(*) filter (where a.status in ('present', 'late'))::integer
     from public.attendance_records a
     where a.student_id = p_student_id and a.attendance_date >= w.ws and a.attendance_date < w.ws + 7),
    (select count(*) filter (where a.status in ('present', 'late', 'absent'))::integer
     from public.attendance_records a
     where a.student_id = p_student_id and a.attendance_date >= w.ws and a.attendance_date < w.ws + 7),
    (select count(*)::integer
     from public.assignments asg
     join public.student_courses sc
       on sc.course_id = asg.course_id and sc.academic_year = asg.academic_year and sc.student_id = p_student_id
     where asg.due_at >= w.ws and asg.due_at < w.ws + 7),
    (select count(*)::integer
     from public.assignment_submissions sub
     join public.assignments asg on asg.id = sub.assignment_id
     where sub.student_id = p_student_id and sub.status in ('submitted', 'late')
       and asg.due_at >= w.ws and asg.due_at < w.ws + 7),
    (select round(avg(sub.score / asg.max_score * 100), 1)
     from public.assignment_submissions sub
     join public.assignments asg on asg.id = sub.assignment_id
     where sub.student_id = p_student_id and sub.score is not null
       and asg.due_at >= w.ws and asg.due_at < w.ws + 7),
    (select coalesce(sum(e.event_count), 0)::integer
     from public.engagement_events e
     where e.student_id = p_student_id and e.occurred_at >= w.ws and e.occurred_at < w.ws + 7),
    (select coalesce(sum(e.event_count) filter (where e.event_type = 'quiz_attempt'), 0)::integer
     from public.engagement_events e
     where e.student_id = p_student_id and e.occurred_at >= w.ws and e.occurred_at < w.ws + 7)
  from weeks w
  order by w.ws;
end;
$$;

revoke all on function
  public.create_intervention(uuid, text, text, text, uuid, date, uuid),
  public.approve_recommendation(uuid, uuid),
  public.assign_intervention(uuid, uuid),
  public.respond_to_intervention(uuid, boolean, text),
  public.complete_intervention(uuid, text),
  public.cancel_intervention(uuid),
  public.get_my_recommended_actions(),
  public.send_mentor_message(uuid, text),
  public.get_mentor_caseload(),
  public.get_student_weekly_trends(uuid, integer)
from public, anon;

grant execute on function
  public.create_intervention(uuid, text, text, text, uuid, date, uuid),
  public.approve_recommendation(uuid, uuid),
  public.assign_intervention(uuid, uuid),
  public.respond_to_intervention(uuid, boolean, text),
  public.complete_intervention(uuid, text),
  public.cancel_intervention(uuid),
  public.get_my_recommended_actions(),
  public.send_mentor_message(uuid, text),
  public.get_mentor_caseload(),
  public.get_student_weekly_trends(uuid, integer)
to authenticated, service_role;

-- Audit the new tables.
do $$
declare
  v_table text;
begin
  foreach v_table in array array['academic_terms', 'lms_integrations'] loop
    execute format('drop trigger if exists write_audit_log on public.%I', v_table);
    execute format(
      'create trigger write_audit_log after insert or update or delete on public.%I '
      'for each row execute function private.write_audit_log()', v_table);
  end loop;
end
$$;
