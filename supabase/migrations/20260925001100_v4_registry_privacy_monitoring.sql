-- SEWS 0011 (V4) — model registry and lifecycle, prediction gating, identity/ML separation,
-- monitoring snapshots, drift alerts, system events and platform versions.
-- Idempotent: safe to re-run.

create or replace function private.has_identity_keys(p_doc jsonb)
returns boolean
language sql immutable
set search_path = ''
as $$
  select p_doc ?| array['full_name', 'name', 'email', 'institutional_email', 'phone', 'phone_number',
                        'roll_number', 'user_id', 'student_id'];
$$;

revoke all on function private.has_identity_keys(jsonb) from public, anon;
grant execute on function private.has_identity_keys(jsonb) to authenticated, service_role;

-- ============================================================= model_registry
create table if not exists public.model_registry (
  id                   uuid primary key default gen_random_uuid(),
  model_name           text not null,
  version              text not null,
  target               text not null,
  institution_id       uuid references public.institutions (id) on delete restrict,
  dataset_version      text not null,
  feature_version      text not null,
  data_provenance      text not null,
  training_timestamp   timestamptz not null,
  validation_metrics   jsonb not null default '{}'::jsonb,
  calibration_metrics  jsonb not null default '{}'::jsonb,
  status               text not null default 'development',
  artifact_sha256      text,
  approved_by          uuid references public.profiles (id) on delete set null,
  approved_at          timestamptz,
  status_changed_at    timestamptz not null default now(),
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint model_registry_version_key unique (version),
  constraint model_registry_name_format check (model_name ~ '^[a-z0-9][a-z0-9_-]{0,63}$'),
  constraint model_registry_version_format check (version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint model_registry_dataset_version_format check (dataset_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint model_registry_feature_version_format check (feature_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint model_registry_target_check check (target in ('academic', 'dropout', 'course_failure', 'engagement')),
  constraint model_registry_provenance_check check (data_provenance in ('benchmark', 'synthetic', 'institutional')),
  constraint model_registry_status_check
    check (status in ('development', 'validated', 'staging', 'production', 'retired')),
  constraint model_registry_sha_format check (artifact_sha256 is null or artifact_sha256 ~ '^[0-9a-f]{64}$'),
  constraint model_registry_metrics_objects
    check (jsonb_typeof(validation_metrics) = 'object' and jsonb_typeof(calibration_metrics) = 'object')
);

-- At most one production model per target and institution scope (NULL = all institutions).
create unique index if not exists model_registry_one_production
  on public.model_registry (target, coalesce(institution_id, '00000000-0000-0000-0000-000000000000'::uuid))
  where status = 'production';

drop trigger if exists set_updated_at on public.model_registry;
create trigger set_updated_at before update on public.model_registry
  for each row execute function private.set_updated_at();

-- Lifecycle: development → validated → staging → production → retired (any state may retire).
--   validated  requires validation metrics
--   production requires institutional training data, calibration evaluation and a recorded approval
create or replace function private.enforce_model_lifecycle()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if new.status <> 'development' then
      raise exception 'sews:models_start_in_development' using errcode = '23514';
    end if;
    return new;
  end if;

  if (new.version, new.target, new.dataset_version, new.feature_version, new.data_provenance,
      new.training_timestamp, new.institution_id, new.model_name)
     is distinct from
     (old.version, old.target, old.dataset_version, old.feature_version, old.data_provenance,
      old.training_timestamp, old.institution_id, old.model_name) then
    raise exception 'sews:model_identity_is_immutable' using errcode = '23514';
  end if;

  if new.status is distinct from old.status then
    if not (
      (old.status = 'development' and new.status in ('validated', 'retired'))
      or (old.status = 'validated' and new.status in ('staging', 'retired'))
      or (old.status = 'staging' and new.status in ('production', 'validated', 'retired'))
      or (old.status = 'production' and new.status = 'retired')
    ) then
      raise exception 'sews:invalid_model_transition' using errcode = '23514';
    end if;
    if new.status = 'validated' and new.validation_metrics = '{}'::jsonb then
      raise exception 'sews:validation_metrics_required' using errcode = '23514';
    end if;
    if new.status = 'production' then
      if new.data_provenance <> 'institutional' then
        raise exception 'sews:production_requires_institutional_data' using errcode = '23514';
      end if;
      if new.calibration_metrics = '{}'::jsonb then
        raise exception 'sews:calibration_evaluation_required' using errcode = '23514';
      end if;
      if new.approved_by is null or new.approved_at is null then
        raise exception 'sews:production_requires_approval' using errcode = '23514';
      end if;
    end if;
    new.status_changed_at := now();
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_model_lifecycle() from public, anon, authenticated;

drop trigger if exists enforce_model_lifecycle on public.model_registry;
create trigger enforce_model_lifecycle before insert or update on public.model_registry
  for each row execute function private.enforce_model_lifecycle();

alter table public.model_registry enable row level security;
revoke all on table public.model_registry from anon, authenticated;
grant select on table public.model_registry to authenticated;
grant all on table public.model_registry to service_role;

-- Admins read global models and their own institution's models. Registration and promotion are
-- server-side (ML governance), never from the mobile app.
drop policy if exists model_registry_select on public.model_registry;
create policy model_registry_select on public.model_registry for select to authenticated
  using (
    (select private.current_profile_role()) = 'admin'
    and (institution_id is null or private.is_admin_of(institution_id))
  );

-- ======================================================== prediction gating
alter table public.risk_predictions
  add column if not exists model_registry_id uuid references public.model_registry (id) on delete restrict;
create index if not exists risk_predictions_model_registry_id_idx on public.risk_predictions (model_registry_id);

-- Every new prediction must come from a registered model in status 'production'. A development
-- database may opt in to non-production models with `set sews.environment = 'development'`
-- (synthetic demo data only). Model lineage columns are copied from the registry, so they
-- cannot disagree with it.
create or replace function private.check_registered_model()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select * into v from public.model_registry r where r.id = new.model_registry_id;
  if not found then
    raise exception 'sews:prediction_requires_registered_model' using errcode = '23514';
  end if;
  if v.status <> 'production' and not (
    coalesce(current_setting('sews.environment', true), '') = 'development'
    and v.status in ('development', 'validated', 'staging')
  ) then
    raise exception 'sews:model_not_approved_for_live_predictions' using errcode = '23514';
  end if;
  if v.institution_id is not null and v.institution_id <> private.student_institution_id(new.student_id) then
    raise exception 'sews:model_institution_mismatch' using errcode = '23514';
  end if;
  new.model_version := v.version;
  new.target := v.target;
  new.feature_version := v.feature_version;
  new.dataset_version := v.dataset_version;
  new.data_provenance := v.data_provenance;
  return new;
end;
$$;

revoke all on function private.check_registered_model() from public, anon, authenticated;

-- Named to fire before compute_risk_trajectory (triggers fire in name order).
drop trigger if exists check_registered_model on public.risk_predictions;
create trigger check_registered_model before insert on public.risk_predictions
  for each row execute function private.check_registered_model();

-- =================================================== identity vs ML data
-- Random, non-derivable ML identifiers. Feature snapshots never contain identity fields and are
-- not reachable through the Data API (private schema, no client privileges).
create table if not exists private.ml_subject_map (
  student_id     uuid primary key references public.students (id) on delete cascade,
  ml_subject_id  uuid not null unique default gen_random_uuid(),
  created_at     timestamptz not null default now()
);

create table if not exists private.feature_snapshots (
  id               uuid primary key default gen_random_uuid(),
  ml_subject_id    uuid not null references private.ml_subject_map (ml_subject_id) on delete cascade,
  as_of            timestamptz not null,
  feature_version  text not null,
  features         jsonb not null,
  created_at       timestamptz not null default now(),
  constraint feature_snapshots_key unique (ml_subject_id, as_of, feature_version),
  constraint feature_snapshots_object check (jsonb_typeof(features) = 'object'),
  constraint feature_snapshots_no_identity check (not private.has_identity_keys(features))
);

revoke all on table private.ml_subject_map, private.feature_snapshots from public, anon, authenticated;
grant all on table private.ml_subject_map, private.feature_snapshots to service_role;

create or replace function private.ml_subject_id_for(p_student_id uuid)
returns uuid
language plpgsql security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  insert into private.ml_subject_map (student_id) values (p_student_id) on conflict (student_id) do nothing;
  select m.ml_subject_id into v_id from private.ml_subject_map m where m.student_id = p_student_id;
  return v_id;
end;
$$;

revoke all on function private.ml_subject_id_for(uuid) from public, anon, authenticated;
grant execute on function private.ml_subject_id_for(uuid) to service_role;

-- ======================================================= monitoring tables
create table if not exists public.model_monitoring_snapshots (
  id                     uuid primary key default gen_random_uuid(),
  model_registry_id      uuid not null references public.model_registry (id) on delete cascade,
  window_start           date not null,
  window_end             date not null,
  n_predictions          integer not null,
  level_distribution     jsonb not null,
  probability_quantiles  jsonb not null,
  feature_stats          jsonb not null,
  labels_available       integer not null default 0,
  performance            jsonb,
  created_at             timestamptz not null default now(),
  constraint model_monitoring_snapshots_key unique (model_registry_id, window_start, window_end),
  constraint model_monitoring_snapshots_window check (window_end >= window_start),
  constraint model_monitoring_snapshots_counts check (n_predictions >= 0 and labels_available >= 0),
  constraint model_monitoring_snapshots_no_identity
    check (not private.has_identity_keys(feature_stats) and not private.has_identity_keys(level_distribution))
);

create table if not exists public.drift_alerts (
  id                      uuid primary key default gen_random_uuid(),
  model_registry_id       uuid not null references public.model_registry (id) on delete cascade,
  monitoring_snapshot_id  uuid references public.model_monitoring_snapshots (id) on delete set null,
  alert_type              text not null,
  subject                 text not null,
  statistic               text not null,
  value                   numeric not null,
  threshold               numeric not null,
  severity                text not null,
  status                  text not null default 'open',
  acknowledged_by         uuid references public.profiles (id) on delete set null,
  acknowledged_at         timestamptz,
  created_at              timestamptz not null default now(),
  constraint drift_alerts_type_check check (alert_type in (
    'feature_drift', 'missingness_drift', 'prediction_drift', 'outcome_drift', 'performance_drop'
  )),
  constraint drift_alerts_subject_format check (subject ~ '^[a-z][a-z0-9_]{0,63}$'),
  constraint drift_alerts_statistic_check check (statistic in ('psi', 'missing_rate_change', 'rate_change', 'metric_drop')),
  constraint drift_alerts_severity_check check (severity in ('warning', 'critical')),
  constraint drift_alerts_status_check check (status in ('open', 'acknowledged', 'resolved')),
  constraint drift_alerts_ack_check check ((status = 'open') = (acknowledged_at is null))
);

create index if not exists drift_alerts_model_status_idx on public.drift_alerts (model_registry_id, status, created_at desc);

create table if not exists public.system_events (
  id              uuid primary key default gen_random_uuid(),
  occurred_at     timestamptz not null default now(),
  component       text not null,
  event_type      text not null,
  severity        text not null,
  institution_id  uuid references public.institutions (id) on delete set null,
  details         jsonb not null default '{}'::jsonb,
  constraint system_events_component_check check (component in (
    'api', 'scoring', 'notifications', 'ingestion', 'database', 'monitoring'
  )),
  constraint system_events_type_check check (event_type in (
    'prediction_failure', 'model_failure', 'notification_failure', 'database_error', 'ingestion_error',
    'latency_breach', 'drift_alert'
  )),
  constraint system_events_severity_check check (severity in ('info', 'warning', 'error', 'critical')),
  constraint system_events_details_object check (jsonb_typeof(details) = 'object'),
  constraint system_events_no_identity check (not private.has_identity_keys(details))
);

create index if not exists system_events_occurred_idx on public.system_events (occurred_at desc);

alter table public.model_monitoring_snapshots enable row level security;
alter table public.drift_alerts enable row level security;
alter table public.system_events enable row level security;
revoke all on table public.model_monitoring_snapshots, public.drift_alerts, public.system_events
  from anon, authenticated;
grant select on table public.model_monitoring_snapshots, public.drift_alerts, public.system_events to authenticated;
grant all on table public.model_monitoring_snapshots, public.drift_alerts, public.system_events to service_role;

-- Visible exactly when the model is visible (the subquery is filtered by model_registry RLS).
drop policy if exists model_monitoring_snapshots_select on public.model_monitoring_snapshots;
create policy model_monitoring_snapshots_select on public.model_monitoring_snapshots for select to authenticated
  using (exists (select 1 from public.model_registry r where r.id = model_monitoring_snapshots.model_registry_id));
drop policy if exists drift_alerts_select on public.drift_alerts;
create policy drift_alerts_select on public.drift_alerts for select to authenticated
  using (exists (select 1 from public.model_registry r where r.id = drift_alerts.model_registry_id));
drop policy if exists system_events_select on public.system_events;
create policy system_events_select on public.system_events for select to authenticated
  using (
    (select private.current_profile_role()) = 'admin'
    and (institution_id is null or private.is_admin_of(institution_id))
  );

create or replace function public.acknowledge_drift_alert(p_alert_id uuid)
returns void
language plpgsql security definer
set search_path = ''
as $$
declare
  v record;
begin
  select a.status, r.institution_id into v
  from public.drift_alerts a join public.model_registry r on r.id = a.model_registry_id
  where a.id = p_alert_id for update of a;
  if not found
     or private.current_profile_role() is distinct from 'admin'
     or (v.institution_id is not null and not private.is_admin_of(v.institution_id)) then
    raise exception 'sews:forbidden' using errcode = '42501';
  end if;
  if v.status <> 'open' then
    raise exception 'sews:alert_not_open' using errcode = 'P0001';
  end if;
  update public.drift_alerts a
     set status = 'acknowledged', acknowledged_by = (select auth.uid()), acknowledged_at = now()
   where a.id = p_alert_id;
end;
$$;

-- ============================================================= versions
-- Versioned components (see docs/architecture/versioning.md). The app refuses to run when it is
-- older than minimum_mobile_app.
create or replace function public.get_platform_versions()
returns table (component text, version text)
language sql
immutable
set search_path = ''
as $$
  values ('database_schema', '4.0.0'), ('minimum_mobile_app', '2.0.0'), ('inference_api', '1.0.0');
$$;

revoke all on function public.acknowledge_drift_alert(uuid), public.get_platform_versions() from public, anon;
grant execute on function public.acknowledge_drift_alert(uuid), public.get_platform_versions()
  to authenticated, service_role;

do $$
declare
  v_table text;
begin
  foreach v_table in array array['model_registry', 'drift_alerts'] loop
    execute format('drop trigger if exists write_audit_log on public.%I', v_table);
    execute format(
      'create trigger write_audit_log after insert or update or delete on public.%I '
      'for each row execute function private.write_audit_log()', v_table);
  end loop;
end
$$;
