-- SEWS 0003 — students, courses, scope tables and academic event data.
--
-- Scope tables (not in the original entity list, required to express authorization):
--   mentor_assignments  — which mentor may see which student (mentor scope)
--   course_faculty      — which faculty member teaches which course (faculty scope)
--
-- ON DELETE policy:
--   * Student-owned personal data (enrolments, results, attendance, submissions,
--     engagement, mentor links) CASCADE from students, so an erasure request removes
--     it completely. Deleting a student is a service-role-only operation.
--   * Reference data (courses/programmes/departments) is RESTRICT.
--   * "who recorded this" columns SET NULL when the staff profile is deleted.
-- Composite foreign keys (x_id, institution_id) prevent rows that mix institutions,
-- which the RLS policies rely on.
-- Idempotent: safe to re-run.

-- -------------------------------------------------------------------- students
create table if not exists public.students (
  id                   uuid primary key default gen_random_uuid(),
  institution_id       uuid not null references public.institutions (id) on delete restrict,
  programme_id         uuid not null,
  user_id              uuid references public.profiles (id) on delete set null,
  roll_number          text not null,
  full_name            text not null,
  institutional_email  text not null,
  admission_year       smallint not null,
  current_semester     smallint not null,
  status               text not null default 'active',
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint students_programme_fkey foreign key (programme_id, institution_id)
    references public.programmes (id, institution_id) on delete restrict,
  constraint students_user_id_key unique (user_id),
  constraint students_institution_roll_key unique (institution_id, roll_number),
  constraint students_institution_email_key unique (institution_id, institutional_email),
  constraint students_id_institution_key unique (id, institution_id),
  constraint students_roll_number_format check (roll_number ~ '^[A-Za-z0-9/_-]{1,32}$'),
  constraint students_full_name_length check (char_length(btrim(full_name)) between 1 and 120),
  constraint students_email_format check (
    institutional_email = lower(institutional_email)
    and char_length(institutional_email) <= 254
    and institutional_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'
  ),
  constraint students_admission_year_check check (admission_year between 2000 and 2100),
  constraint students_current_semester_check check (current_semester between 1 and 12),
  constraint students_status_check check (status in ('active', 'on_leave', 'graduated', 'withdrawn'))
);

create index if not exists students_programme_id_idx on public.students (programme_id);

-- --------------------------------------------------------------------- courses
create table if not exists public.courses (
  id               uuid primary key default gen_random_uuid(),
  institution_id   uuid not null references public.institutions (id) on delete restrict,
  department_id    uuid not null,
  programme_id     uuid,
  code             text not null,
  title            text not null,
  credits          numeric(3, 1) not null,
  semester_number  smallint not null,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  constraint courses_department_fkey foreign key (department_id, institution_id)
    references public.departments (id, institution_id) on delete restrict,
  constraint courses_programme_fkey foreign key (programme_id, institution_id)
    references public.programmes (id, institution_id) on delete restrict,
  constraint courses_institution_code_key unique (institution_id, code),
  constraint courses_id_institution_key unique (id, institution_id),
  constraint courses_code_format check (code ~ '^[A-Z0-9][A-Z0-9_-]{1,19}$'),
  constraint courses_title_length check (char_length(btrim(title)) between 2 and 200),
  constraint courses_credits_check check (credits > 0 and credits <= 30),
  constraint courses_semester_number_check check (semester_number between 1 and 12)
);

create index if not exists courses_programme_id_idx on public.courses (programme_id);

-- ---------------------------------------------------------- mentor_assignments
create table if not exists public.mentor_assignments (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  mentor_id       uuid not null references public.profiles (id) on delete cascade,
  student_id      uuid not null,
  starts_on       date not null default current_date,
  ends_on         date,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint mentor_assignments_student_fkey foreign key (student_id, institution_id)
    references public.students (id, institution_id) on delete cascade,
  constraint mentor_assignments_dates_check check (ends_on is null or ends_on >= starts_on)
);

-- One open-ended (current) mentor per student.
create unique index if not exists mentor_assignments_one_open_per_student
  on public.mentor_assignments (student_id) where ends_on is null;
create index if not exists mentor_assignments_student_id_idx on public.mentor_assignments (student_id);
create index if not exists mentor_assignments_mentor_id_idx on public.mentor_assignments (mentor_id);
create index if not exists mentor_assignments_institution_id_idx on public.mentor_assignments (institution_id);

-- -------------------------------------------------------------- course_faculty
create table if not exists public.course_faculty (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  course_id       uuid not null,
  faculty_id      uuid not null references public.profiles (id) on delete cascade,
  created_at      timestamptz not null default now(),
  constraint course_faculty_course_fkey foreign key (course_id, institution_id)
    references public.courses (id, institution_id) on delete cascade,
  constraint course_faculty_course_faculty_key unique (course_id, faculty_id)
);

create index if not exists course_faculty_faculty_id_idx on public.course_faculty (faculty_id);
create index if not exists course_faculty_institution_id_idx on public.course_faculty (institution_id);

-- ------------------------------------------------------------- student_courses
-- One row per student per course per academic year. marks is a percentage (0–100).
-- grade uses the UGC CBCS 10-point letter scale; grade_points is derived from it.
create table if not exists public.student_courses (
  id                   uuid primary key default gen_random_uuid(),
  institution_id       uuid not null references public.institutions (id) on delete restrict,
  student_id           uuid not null,
  course_id            uuid not null,
  academic_year        text not null,
  semester             smallint not null,
  status               text not null default 'enrolled',
  marks                numeric(5, 2),
  grade                text,
  grade_points         smallint generated always as (
    case grade
      when 'O'  then 10
      when 'A+' then 9
      when 'A'  then 8
      when 'B+' then 7
      when 'B'  then 6
      when 'C'  then 5
      when 'P'  then 4
      when 'F'  then 0
      when 'Ab' then 0
    end
  ) stored,
  result_published_at  timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint student_courses_student_fkey foreign key (student_id, institution_id)
    references public.students (id, institution_id) on delete cascade,
  constraint student_courses_course_fkey foreign key (course_id, institution_id)
    references public.courses (id, institution_id) on delete restrict,
  constraint student_courses_student_course_year_key unique (student_id, course_id, academic_year),
  constraint student_courses_id_student_course_key unique (id, student_id, course_id),
  constraint student_courses_academic_year_format check (academic_year ~ '^[0-9]{4}-[0-9]{2}$'),
  constraint student_courses_semester_check check (semester between 1 and 12),
  constraint student_courses_status_check check (status in ('enrolled', 'completed', 'withdrawn')),
  constraint student_courses_marks_check check (marks is null or (marks >= 0 and marks <= 100)),
  constraint student_courses_grade_check
    check (grade is null or grade in ('O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'Ab')),
  constraint student_courses_grade_requires_completion check (grade is null or status = 'completed')
);

create index if not exists student_courses_course_id_idx on public.student_courses (course_id);
create index if not exists student_courses_institution_id_idx on public.student_courses (institution_id);

-- ------------------------------------------------------------ academic_records
-- Semester-level results (SGPA/CGPA on the 10-point scale).
create table if not exists public.academic_records (
  id                  uuid primary key default gen_random_uuid(),
  student_id          uuid not null references public.students (id) on delete cascade,
  academic_year       text not null,
  semester            smallint not null,
  sgpa                numeric(4, 2),
  cgpa                numeric(4, 2),
  credits_registered  numeric(5, 1) not null default 0,
  credits_earned      numeric(5, 1) not null default 0,
  result_status       text not null default 'pending',
  published_at        timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint academic_records_student_year_semester_key unique (student_id, academic_year, semester),
  constraint academic_records_academic_year_format check (academic_year ~ '^[0-9]{4}-[0-9]{2}$'),
  constraint academic_records_semester_check check (semester between 1 and 12),
  constraint academic_records_sgpa_check check (sgpa is null or (sgpa >= 0 and sgpa <= 10)),
  constraint academic_records_cgpa_check check (cgpa is null or (cgpa >= 0 and cgpa <= 10)),
  constraint academic_records_credits_check
    check (credits_registered >= 0 and credits_earned >= 0 and credits_earned <= credits_registered),
  constraint academic_records_result_status_check
    check (result_status in ('pending', 'pass', 'fail', 'withheld')),
  constraint academic_records_published_requires_gpa
    check (result_status in ('pending', 'withheld') or (sgpa is not null and cgpa is not null))
);

-- ---------------------------------------------------------- attendance_records
-- Linked to the enrolment (composite FK) so attendance cannot be recorded for a
-- course the student is not enrolled in. 'late' counts as attended; 'excused'
-- sessions are excluded from attendance-rate denominators (see data dictionary).
create table if not exists public.attendance_records (
  id                 uuid primary key default gen_random_uuid(),
  student_course_id  uuid not null,
  student_id         uuid not null,
  course_id          uuid not null,
  attendance_date    date not null,
  session_number     smallint not null default 1,
  status             text not null,
  recorded_by        uuid references public.profiles (id) on delete set null,
  recorded_at        timestamptz not null default now(),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  constraint attendance_records_enrolment_fkey foreign key (student_course_id, student_id, course_id)
    references public.student_courses (id, student_id, course_id) on delete cascade,
  constraint attendance_records_session_key unique (student_course_id, attendance_date, session_number),
  constraint attendance_records_session_number_check check (session_number between 1 and 12),
  constraint attendance_records_status_check check (status in ('present', 'absent', 'late', 'excused'))
);

create index if not exists attendance_records_student_date_idx
  on public.attendance_records (student_id, attendance_date);
create index if not exists attendance_records_course_date_idx
  on public.attendance_records (course_id, attendance_date);

-- ----------------------------------------------------------------- assignments
create table if not exists public.assignments (
  id              uuid primary key default gen_random_uuid(),
  institution_id  uuid not null references public.institutions (id) on delete restrict,
  course_id       uuid not null,
  academic_year   text not null,
  title           text not null,
  max_score       numeric(6, 2) not null,
  due_at          timestamptz not null,
  created_by      uuid references public.profiles (id) on delete set null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint assignments_course_fkey foreign key (course_id, institution_id)
    references public.courses (id, institution_id) on delete restrict,
  constraint assignments_academic_year_format check (academic_year ~ '^[0-9]{4}-[0-9]{2}$'),
  constraint assignments_title_length check (char_length(btrim(title)) between 2 and 200),
  constraint assignments_max_score_check check (max_score > 0 and max_score <= 1000)
);

create index if not exists assignments_course_year_due_idx
  on public.assignments (course_id, academic_year, due_at);
create index if not exists assignments_institution_id_idx on public.assignments (institution_id);

-- ------------------------------------------------------ assignment_submissions
create table if not exists public.assignment_submissions (
  id             uuid primary key default gen_random_uuid(),
  assignment_id  uuid not null references public.assignments (id) on delete cascade,
  student_id     uuid not null references public.students (id) on delete cascade,
  status         text not null,
  submitted_at   timestamptz,
  score          numeric(6, 2),
  graded_at      timestamptz,
  recorded_by    uuid references public.profiles (id) on delete set null,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  constraint assignment_submissions_assignment_student_key unique (assignment_id, student_id),
  constraint assignment_submissions_status_check
    check (status in ('submitted', 'late', 'missing', 'excused')),
  constraint assignment_submissions_submitted_at_check
    check ((status in ('submitted', 'late')) = (submitted_at is not null)),
  constraint assignment_submissions_score_check
    check (score is null or (score >= 0 and status in ('submitted', 'late'))),
  constraint assignment_submissions_graded_check check ((score is null) = (graded_at is null))
);

create index if not exists assignment_submissions_student_id_idx
  on public.assignment_submissions (student_id);

-- ----------------------------------------------------------- engagement_events
-- Aggregated activity counts from an LMS or the app. Written server-side only.
create table if not exists public.engagement_events (
  id           uuid primary key default gen_random_uuid(),
  student_id   uuid not null references public.students (id) on delete cascade,
  course_id    uuid references public.courses (id) on delete set null,
  event_type   text not null,
  event_count  integer not null default 1,
  source       text not null,
  occurred_at  timestamptz not null,
  recorded_at  timestamptz not null default now(),
  created_at   timestamptz not null default now(),
  constraint engagement_events_event_type_check check (event_type in (
    'lms_login', 'content_view', 'resource_download', 'forum_post', 'quiz_attempt', 'assignment_view'
  )),
  constraint engagement_events_event_count_check check (event_count between 1 and 10000),
  constraint engagement_events_source_check check (source in ('lms', 'app', 'import'))
);

create index if not exists engagement_events_student_occurred_idx
  on public.engagement_events (student_id, occurred_at);
create index if not exists engagement_events_course_id_idx on public.engagement_events (course_id);

-- ---------------------------------------------------------- updated_at triggers
drop trigger if exists set_updated_at on public.students;
create trigger set_updated_at before update on public.students
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.courses;
create trigger set_updated_at before update on public.courses
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.mentor_assignments;
create trigger set_updated_at before update on public.mentor_assignments
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.student_courses;
create trigger set_updated_at before update on public.student_courses
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.academic_records;
create trigger set_updated_at before update on public.academic_records
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.attendance_records;
create trigger set_updated_at before update on public.attendance_records
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.assignments;
create trigger set_updated_at before update on public.assignments
  for each row execute function private.set_updated_at();

drop trigger if exists set_updated_at on public.assignment_submissions;
create trigger set_updated_at before update on public.assignment_submissions
  for each row execute function private.set_updated_at();

-- --------------------------------------------- lock down until 0006 grants
alter table public.students enable row level security;
alter table public.courses enable row level security;
alter table public.mentor_assignments enable row level security;
alter table public.course_faculty enable row level security;
alter table public.student_courses enable row level security;
alter table public.academic_records enable row level security;
alter table public.attendance_records enable row level security;
alter table public.assignments enable row level security;
alter table public.assignment_submissions enable row level security;
alter table public.engagement_events enable row level security;

revoke all on table
  public.students, public.courses, public.mentor_assignments, public.course_faculty,
  public.student_courses, public.academic_records, public.attendance_records,
  public.assignments, public.assignment_submissions, public.engagement_events
  from anon, authenticated;
