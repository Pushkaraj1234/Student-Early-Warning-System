-- SEWS 0005 — authorization helpers (used by RLS policies) and integrity triggers.
--
-- Helpers are SECURITY DEFINER so they read the scope tables without recursing into
-- RLS, pin search_path to '' and fully qualify every name. They derive identity only
-- from auth.uid() (the verified JWT subject) and the role stored in public.profiles —
-- never from anything the client sends.
-- Idempotent: safe to re-run.

-- ------------------------------------------------------------ identity helpers
create or replace function private.current_profile_role()
returns text
language sql stable security definer
set search_path = ''
as $$
  select p.role from public.profiles p where p.id = (select auth.uid());
$$;

create or replace function private.current_institution_id()
returns uuid
language sql stable security definer
set search_path = ''
as $$
  select p.institution_id from public.profiles p where p.id = (select auth.uid());
$$;

-- The caller's own students.id, only while the caller's role is 'student'.
create or replace function private.current_student_id()
returns uuid
language sql stable security definer
set search_path = ''
as $$
  select s.id
  from public.students s
  join public.profiles p on p.id = s.user_id
  where s.user_id = (select auth.uid())
    and p.role = 'student';
$$;

create or replace function private.is_admin_of(p_institution_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = (select auth.uid())
      and p.role = 'admin'
      and p.institution_id = p_institution_id
  );
$$;

create or replace function private.student_institution_id(p_student_id uuid)
returns uuid
language sql stable security definer
set search_path = ''
as $$
  select s.institution_id from public.students s where s.id = p_student_id;
$$;

-- ---------------------------------------------------------------- scope helpers
-- Mentor scope: an active mentor assignment, while the caller is a mentor of the
-- same institution.
create or replace function private.is_mentor_of(p_student_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.mentor_assignments ma
    join public.profiles p on p.id = ma.mentor_id
    where ma.mentor_id = (select auth.uid())
      and ma.student_id = p_student_id
      and p.role = 'mentor'
      and p.institution_id = ma.institution_id
      and ma.starts_on <= current_date
      and (ma.ends_on is null or ma.ends_on >= current_date)
  );
$$;

-- Faculty scope: the caller is assigned to teach the course.
create or replace function private.teaches_course(p_course_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.course_faculty cf
    join public.profiles p on p.id = cf.faculty_id
    where cf.faculty_id = (select auth.uid())
      and cf.course_id = p_course_id
      and p.role = 'faculty'
      and p.institution_id = cf.institution_id
  );
$$;

-- Faculty scope over a student: the student is enrolled in a course the caller teaches.
create or replace function private.teaches_student(p_student_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.student_courses sc
    join public.course_faculty cf on cf.course_id = sc.course_id
    join public.profiles p on p.id = cf.faculty_id
    where sc.student_id = p_student_id
      and cf.faculty_id = (select auth.uid())
      and p.role = 'faculty'
      and p.institution_id = cf.institution_id
  );
$$;

-- Personal/predictive data: the student, their mentor, or their institution's admin.
-- Faculty are deliberately excluded (course-scoped data only).
create or replace function private.can_view_student_personal(p_student_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select coalesce(p_student_id = private.current_student_id(), false)
      or private.is_mentor_of(p_student_id)
      or private.is_admin_of(private.student_institution_id(p_student_id));
$$;

-- Basic student record: personal scope plus faculty teaching the student.
create or replace function private.can_view_student(p_student_id uuid)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select private.can_view_student_personal(p_student_id)
      or private.teaches_student(p_student_id);
$$;

-- The calling student is enrolled in the course for that academic year.
create or replace function private.is_enrolled_self(p_course_id uuid, p_academic_year text)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.student_courses sc
    where sc.student_id = private.current_student_id()
      and sc.course_id = p_course_id
      and sc.academic_year = p_academic_year
  );
$$;

-- The calling mentor has an active mentee enrolled in the course for that year.
create or replace function private.mentors_student_in_course(p_course_id uuid, p_academic_year text)
returns boolean
language sql stable security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.student_courses sc
    join public.mentor_assignments ma on ma.student_id = sc.student_id
    join public.profiles p on p.id = ma.mentor_id
    where sc.course_id = p_course_id
      and sc.academic_year = p_academic_year
      and ma.mentor_id = (select auth.uid())
      and p.role = 'mentor'
      and p.institution_id = ma.institution_id
      and ma.starts_on <= current_date
      and (ma.ends_on is null or ma.ends_on >= current_date)
  );
$$;

create or replace function private.assignment_course_id(p_assignment_id uuid)
returns uuid
language sql stable security definer
set search_path = ''
as $$
  select a.course_id from public.assignments a where a.id = p_assignment_id;
$$;

revoke all on function
  private.current_profile_role(),
  private.current_institution_id(),
  private.current_student_id(),
  private.is_admin_of(uuid),
  private.student_institution_id(uuid),
  private.is_mentor_of(uuid),
  private.teaches_course(uuid),
  private.teaches_student(uuid),
  private.can_view_student_personal(uuid),
  private.can_view_student(uuid),
  private.is_enrolled_self(uuid, text),
  private.mentors_student_in_course(uuid, text),
  private.assignment_course_id(uuid)
from public, anon;

grant execute on function
  private.current_profile_role(),
  private.current_institution_id(),
  private.current_student_id(),
  private.is_admin_of(uuid),
  private.student_institution_id(uuid),
  private.is_mentor_of(uuid),
  private.teaches_course(uuid),
  private.teaches_student(uuid),
  private.can_view_student_personal(uuid),
  private.can_view_student(uuid),
  private.is_enrolled_self(uuid, text),
  private.mentors_student_in_course(uuid, text),
  private.assignment_course_id(uuid)
to authenticated, service_role;

-- ------------------------------------------------------------ stamping triggers
-- Who recorded a row is taken from the verified JWT, never from client input.
-- recorded_at is the time the system learned the fact (used for as-of features).
create or replace function private.stamp_recorded_by()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.recorded_by := coalesce((select auth.uid()), new.recorded_by);
  new.recorded_at := now();
  return new;
end;
$$;

create or replace function private.stamp_created_by()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.created_by := coalesce((select auth.uid()), new.created_by);
  return new;
end;
$$;

-- assignment_submissions has recorded_by but no recorded_at column.
create or replace function private.stamp_submission_recorded_by()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.recorded_by := coalesce((select auth.uid()), new.recorded_by);
  return new;
end;
$$;

-- ----------------------------------------------------------- integrity triggers
create or replace function private.validate_mentor_assignment()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1 from public.profiles p
    where p.id = new.mentor_id and p.role = 'mentor' and p.institution_id = new.institution_id
  ) then
    raise exception 'mentor_id must reference a mentor of the same institution'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create or replace function private.validate_course_faculty()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1 from public.profiles p
    where p.id = new.faculty_id and p.role = 'faculty' and p.institution_id = new.institution_id
  ) then
    raise exception 'faculty_id must reference a faculty member of the same institution'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create or replace function private.validate_assignment_submission()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_max_score numeric;
  v_course_id uuid;
  v_academic_year text;
begin
  select a.max_score, a.course_id, a.academic_year
    into v_max_score, v_course_id, v_academic_year
  from public.assignments a
  where a.id = new.assignment_id;

  if not found then
    return new; -- the foreign key rejects the row
  end if;

  if new.score is not null and new.score > v_max_score then
    raise exception 'score exceeds the assignment max_score' using errcode = '23514';
  end if;

  if not exists (
    select 1 from public.student_courses sc
    where sc.student_id = new.student_id
      and sc.course_id = v_course_id
      and sc.academic_year = v_academic_year
  ) then
    raise exception 'student is not enrolled in the assignment course for that academic year'
      using errcode = '23514';
  end if;

  return new;
end;
$$;

create or replace function private.validate_intervention()
returns trigger
language plpgsql security definer
set search_path = ''
as $$
declare
  v_institution_id uuid;
begin
  if new.prediction_id is not null and not exists (
    select 1 from public.risk_predictions rp
    where rp.id = new.prediction_id and rp.student_id = new.student_id
  ) then
    raise exception 'prediction_id must belong to the same student' using errcode = '23514';
  end if;

  if new.assigned_to is not null then
    select s.institution_id into v_institution_id from public.students s where s.id = new.student_id;
    if not exists (
      select 1 from public.profiles p
      where p.id = new.assigned_to
        and p.role in ('mentor', 'faculty', 'admin')
        and p.institution_id = v_institution_id
    ) then
      raise exception 'assigned_to must be a staff member of the student''s institution'
        using errcode = '23514';
    end if;
  end if;

  return new;
end;
$$;

revoke all on function
  private.stamp_recorded_by(),
  private.stamp_created_by(),
  private.stamp_submission_recorded_by(),
  private.validate_mentor_assignment(),
  private.validate_course_faculty(),
  private.validate_assignment_submission(),
  private.validate_intervention()
from public, anon, authenticated;

-- --------------------------------------------------------------- trigger wiring
drop trigger if exists stamp_recorded_by on public.attendance_records;
create trigger stamp_recorded_by before insert or update on public.attendance_records
  for each row execute function private.stamp_recorded_by();

drop trigger if exists stamp_recorded_by on public.assignment_submissions;
create trigger stamp_recorded_by before insert or update on public.assignment_submissions
  for each row execute function private.stamp_submission_recorded_by();

drop trigger if exists stamp_created_by on public.assignments;
create trigger stamp_created_by before insert on public.assignments
  for each row execute function private.stamp_created_by();

drop trigger if exists stamp_created_by on public.interventions;
create trigger stamp_created_by before insert on public.interventions
  for each row execute function private.stamp_created_by();

drop trigger if exists validate_mentor_assignment on public.mentor_assignments;
create trigger validate_mentor_assignment before insert or update on public.mentor_assignments
  for each row execute function private.validate_mentor_assignment();

drop trigger if exists validate_course_faculty on public.course_faculty;
create trigger validate_course_faculty before insert or update on public.course_faculty
  for each row execute function private.validate_course_faculty();

drop trigger if exists validate_assignment_submission on public.assignment_submissions;
create trigger validate_assignment_submission before insert or update on public.assignment_submissions
  for each row execute function private.validate_assignment_submission();

drop trigger if exists validate_intervention on public.interventions;
create trigger validate_intervention before insert or update on public.interventions
  for each row execute function private.validate_intervention();
