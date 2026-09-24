-- SEWS 0004 — risk predictions, risk factors, interventions, notifications, audit logs.
--
-- risk_predictions / risk_factors are written ONLY server-side (service role) by the
-- scoring job and are immutable to API users. risk_level is decided by the model's
-- stored thresholds, never by the client. data_provenance records whether the model
-- was trained on benchmark, synthetic or institutional data so the app can say so.
-- Idempotent: safe to re-run.

-- ------------------------------------------------------------ risk_predictions
create table if not exists public.risk_predictions (
  id                uuid primary key default gen_random_uuid(),
  student_id        uuid not null references public.students (id) on delete cascade,
  prediction_date   date not null,
  risk_probability  numeric(6, 5) not null,
  risk_level        text not null,
  model_version     text not null,
  feature_version   text not null,
  dataset_version   text not null,
  data_provenance   text not null,
  created_at        timestamptz not null default now(),
  constraint risk_predictions_student_date_model_key unique (student_id, prediction_date, model_version),
  constraint risk_predictions_probability_check check (risk_probability >= 0 and risk_probability <= 1),
  constraint risk_predictions_risk_level_check check (risk_level in ('stable', 'watch', 'elevated', 'high')),
  constraint risk_predictions_model_version_format check (model_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint risk_predictions_feature_version_format check (feature_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint risk_predictions_dataset_version_format check (dataset_version ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$'),
  constraint risk_predictions_provenance_check
    check (data_provenance in ('benchmark', 'synthetic', 'institutional'))
);

create index if not exists risk_predictions_prediction_date_idx on public.risk_predictions (prediction_date);

-- ---------------------------------------------------------------- risk_factors
-- One row per top-k model factor (e.g. SHAP contribution) of a prediction.
-- `feature` is the machine feature key; the app maps it to a display label and
-- never invents factors that are not stored here.
create table if not exists public.risk_factors (
  id             uuid primary key default gen_random_uuid(),
  prediction_id  uuid not null references public.risk_predictions (id) on delete cascade,
  rank           smallint not null,
  feature        text not null,
  feature_value  numeric,
  contribution   numeric not null,
  direction      text not null,
  created_at     timestamptz not null default now(),
  constraint risk_factors_prediction_rank_key unique (prediction_id, rank),
  constraint risk_factors_prediction_feature_key unique (prediction_id, feature),
  constraint risk_factors_rank_check check (rank between 1 and 20),
  constraint risk_factors_feature_format check (feature ~ '^[a-z][a-z0-9_]{0,63}$'),
  constraint risk_factors_direction_check check (direction in ('increases_risk', 'decreases_risk')),
  constraint risk_factors_direction_sign_check check (
    (direction = 'increases_risk' and contribution >= 0)
    or (direction = 'decreases_risk' and contribution <= 0)
  )
);

-- --------------------------------------------------------------- interventions
-- notes are staff-only. Students read their recommended actions through
-- public.get_my_recommended_actions(), which never returns notes or staff ids.
create table if not exists public.interventions (
  id                 uuid primary key default gen_random_uuid(),
  student_id         uuid not null references public.students (id) on delete cascade,
  prediction_id      uuid references public.risk_predictions (id) on delete set null,
  intervention_type  text not null,
  status             text not null default 'recommended',
  source             text not null,
  created_by         uuid references public.profiles (id) on delete set null,
  assigned_to        uuid references public.profiles (id) on delete set null,
  due_on             date,
  notes              text,
  outcome            text,
  completed_at       timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  constraint interventions_type_check check (intervention_type in (
    'mentor_meeting', 'academic_counselling', 'attendance_follow_up',
    'assignment_support', 'peer_tutoring', 'wellbeing_referral'
  )),
  constraint interventions_status_check
    check (status in ('recommended', 'planned', 'in_progress', 'completed', 'cancelled')),
  constraint interventions_source_check check (source in ('model_rule', 'mentor', 'admin')),
  constraint interventions_notes_length check (notes is null or char_length(notes) <= 2000),
  constraint interventions_outcome_check
    check (outcome is null or outcome in ('improved', 'no_change', 'worsened', 'not_assessed')),
  constraint interventions_completion_check check ((status = 'completed') = (completed_at is not null)),
  constraint interventions_outcome_requires_completion check (outcome is null or status = 'completed')
);

create index if not exists interventions_student_created_idx
  on public.interventions (student_id, created_at desc);
create index if not exists interventions_status_idx on public.interventions (status);
create index if not exists interventions_prediction_id_idx on public.interventions (prediction_id);
create index if not exists interventions_assigned_to_idx on public.interventions (assigned_to);

-- --------------------------------------------------------------- notifications
create table if not exists public.notifications (
  id                 uuid primary key default gen_random_uuid(),
  recipient_id       uuid not null references public.profiles (id) on delete cascade,
  notification_type  text not null,
  title              text not null,
  body               text not null,
  read_at            timestamptz,
  created_at         timestamptz not null default now(),
  constraint notifications_type_check check (notification_type in (
    'risk_update', 'intervention', 'assignment_due', 'attendance_alert', 'system'
  )),
  constraint notifications_title_length check (char_length(btrim(title)) between 1 and 120),
  constraint notifications_body_length check (char_length(btrim(body)) between 1 and 1000)
);

create index if not exists notifications_recipient_created_idx
  on public.notifications (recipient_id, created_at desc);

-- ------------------------------------------------------------------ audit_logs
-- Written only by the private.write_audit_log trigger (0007). Stores who changed
-- which record and which columns — deliberately NOT row contents, so the audit
-- trail does not duplicate personal data. actor_id and record_id are intentionally
-- not foreign keys: the audit trail must survive deletion of the actor or record.
create table if not exists public.audit_logs (
  id               uuid primary key default gen_random_uuid(),
  institution_id   uuid references public.institutions (id) on delete set null,
  actor_id         uuid,
  action           text not null,
  table_name       text not null,
  record_id        uuid not null,
  changed_columns  text[] not null default '{}',
  created_at       timestamptz not null default now(),
  constraint audit_logs_action_check check (action in ('insert', 'update', 'delete')),
  constraint audit_logs_table_name_format check (table_name ~ '^[a-z_]{1,63}$')
);

create index if not exists audit_logs_institution_created_idx
  on public.audit_logs (institution_id, created_at desc);

-- ---------------------------------------------------------- updated_at triggers
drop trigger if exists set_updated_at on public.interventions;
create trigger set_updated_at before update on public.interventions
  for each row execute function private.set_updated_at();

-- --------------------------------------------- lock down until 0006 grants
alter table public.risk_predictions enable row level security;
alter table public.risk_factors enable row level security;
alter table public.interventions enable row level security;
alter table public.notifications enable row level security;
alter table public.audit_logs enable row level security;

revoke all on table
  public.risk_predictions, public.risk_factors, public.interventions,
  public.notifications, public.audit_logs
  from anon, authenticated;
