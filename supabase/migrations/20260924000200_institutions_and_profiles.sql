-- SEWS 0002 — institutions, departments, programmes, profiles.
-- ON DELETE policy: reference data (institutions/departments/programmes) uses RESTRICT
-- so an accidental delete cannot cascade through an institution's records.
-- profiles.id is auth.users.id and cascades when the auth user is deleted.
-- RLS is enabled and API privileges revoked here; grants/policies are in 0006.
-- Idempotent: safe to re-run.

-- ---------------------------------------------------------------- institutions
create table if not exists public.institutions (
  id          uuid primary key default gen_random_uuid(),
  code        text not null,
  name        text not null,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint institutions_code_key unique (code),
  constraint institutions_code_format check (code ~ '^[A-Z0-9][A-Z0-9_-]{1,31}$'),
  constraint institutions_name_length check (char_length(btrim(name)) between 2 and 200)
);

-- ----------------------------------------------------------------- departments
create table if not exists public.departments (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  code            text not null,
  name            text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint departments_institution_code_key unique (institution_id, code),
  constraint departments_id_institution_key unique (id, institution_id),
  constraint departments_code_format check (code ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'),
  constraint departments_name_length check (char_length(btrim(name)) between 2 and 200)
);

-- ------------------------------------------------------------------ programmes
create table if not exists public.programmes (
  id                  uuid primary key default gen_random_uuid(),
  institution_id      uuid not null references public.institutions (id) on delete restrict,
  department_id       uuid not null,
  code                text not null,
  name                text not null,
  degree_level        text not null,
  duration_semesters  smallint not null,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  -- Composite FK guarantees the department belongs to the same institution.
  constraint programmes_department_fkey foreign key (department_id, institution_id)
    references public.departments (id, institution_id) on delete restrict,
  constraint programmes_institution_code_key unique (institution_id, code),
  constraint programmes_id_institution_key unique (id, institution_id),
  constraint programmes_code_format check (code ~ '^[A-Z0-9][A-Z0-9_-]{0,31}$'),
  constraint programmes_name_length check (char_length(btrim(name)) between 2 and 200),
  constraint programmes_degree_level_check
    check (degree_level in ('diploma', 'undergraduate', 'postgraduate', 'doctoral')),
  constraint programmes_duration_check check (duration_semesters between 1 and 12)
);

-- -------------------------------------------------------------------- profiles
create table if not exists public.profiles (
  id                       uuid primary key references auth.users (id) on delete cascade,
  institution_id           uuid references public.institutions (id) on delete restrict,
  role                     text not null default 'student',
  full_name                text,
  onboarding_completed_at  timestamptz,
  privacy_notice_version   text,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  constraint profiles_role_check check (role in ('student', 'mentor', 'faculty', 'admin')),
  -- Staff accounts are always institution-scoped. Students get an institution when
  -- they claim their student record (public.claim_student_record).
  constraint profiles_staff_institution_check check (role = 'student' or institution_id is not null),
  constraint profiles_full_name_length
    check (full_name is null or char_length(btrim(full_name)) between 1 and 120),
  constraint profiles_privacy_notice_version_format
    check (privacy_notice_version is null or privacy_notice_version ~ '^v[0-9]+(\.[0-9]+){0,2}$')
);

create index if not exists profiles_institution_id_idx on public.profiles (institution_id);

-- ---------------------------------------------------------- updated_at triggers
drop trigger if exists set_updated_at on public.institutions;
create trigger set_updated_at before update on public.institutions
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.departments;
create trigger set_updated_at before update on public.departments
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.programmes;
create trigger set_updated_at before update on public.programmes
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.profiles;
create trigger set_updated_at before update on public.profiles
  for each row execute function private.set_updated_at();

-- ------------------------------------------------ profile creation on sign-up
-- Every new auth user gets a 'student' profile. Any role or institution sent by the
-- client in user metadata is deliberately ignored: roles are assigned only
-- server-side (service role or public.admin_set_user_role).
create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_full_name text;
begin
  v_full_name := nullif(btrim(coalesce(new.raw_user_meta_data ->> 'full_name', '')), '');
  if v_full_name is not null then
    v_full_name := left(v_full_name, 120);
  end if;

  insert into public.profiles (id, full_name)
  values (new.id, v_full_name)
  on conflict (id) do nothing;

  return new;
end;
$$;

revoke all on function private.handle_new_user() from public, anon, authenticated;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function private.handle_new_user();

-- --------------------------------------------- lock down until 0006 grants
alter table public.institutions enable row level security;
alter table public.departments enable row level security;
alter table public.programmes enable row level security;
alter table public.profiles enable row level security;

revoke all on table public.institutions, public.departments, public.programmes, public.profiles
  from anon, authenticated;
