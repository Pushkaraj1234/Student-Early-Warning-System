-- SEWS 0006 — table privileges and Row Level Security policies.
--
-- Two layers, both required:
--   1. Privileges (GRANT) decide which operations/columns the API role may touch at
--      all. `anon` gets nothing. `authenticated` gets only the operations some app
--      role needs, and UPDATE/INSERT only on the columns that may legitimately change.
--      Identity/scope columns (student_id, course_id, institution_id, user_id, role,
--      recorded_by, created_by) are never client-writable.
--   2. RLS policies decide which rows. One explicit policy per permitted operation.
--      Any operation without a policy is denied (Postgres default with RLS enabled).
--
-- Service operations (scoring job, imports, account provisioning) use the service
-- role, which bypasses RLS and exists only server-side.
-- Idempotent: safe to re-run.

-- =============================================================== institutions
alter table public.institutions enable row level security;
revoke all on table public.institutions from anon, authenticated;
grant select on table public.institutions to authenticated;
grant update (name) on table public.institutions to authenticated;
grant all on table public.institutions to service_role;

drop policy if exists institutions_select on public.institutions;
create policy institutions_select on public.institutions
  for select to authenticated
  using (id = (select private.current_institution_id()));

drop policy if exists institutions_update on public.institutions;
create policy institutions_update on public.institutions
  for update to authenticated
  using (private.is_admin_of(id))
  with check (private.is_admin_of(id));
-- INSERT / DELETE: no policy (service role only).

-- ================================================================ departments
alter table public.departments enable row level security;
revoke all on table public.departments from anon, authenticated;
grant select, delete on table public.departments to authenticated;
grant insert (institution_id, code, name) on table public.departments to authenticated;
grant update (code, name) on table public.departments to authenticated;
grant all on table public.departments to service_role;

drop policy if exists departments_select on public.departments;
create policy departments_select on public.departments
  for select to authenticated
  using (institution_id = (select private.current_institution_id()));

drop policy if exists departments_insert on public.departments;
create policy departments_insert on public.departments
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists departments_update on public.departments;
create policy departments_update on public.departments
  for update to authenticated
  using (private.is_admin_of(institution_id))
  with check (private.is_admin_of(institution_id));

drop policy if exists departments_delete on public.departments;
create policy departments_delete on public.departments
  for delete to authenticated
  using (private.is_admin_of(institution_id));

-- ================================================================= programmes
alter table public.programmes enable row level security;
revoke all on table public.programmes from anon, authenticated;
grant select, delete on table public.programmes to authenticated;
grant insert (institution_id, department_id, code, name, degree_level, duration_semesters)
  on table public.programmes to authenticated;
grant update (code, name, degree_level, duration_semesters) on table public.programmes to authenticated;
grant all on table public.programmes to service_role;

drop policy if exists programmes_select on public.programmes;
create policy programmes_select on public.programmes
  for select to authenticated
  using (institution_id = (select private.current_institution_id()));

drop policy if exists programmes_insert on public.programmes;
create policy programmes_insert on public.programmes
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists programmes_update on public.programmes;
create policy programmes_update on public.programmes
  for update to authenticated
  using (private.is_admin_of(institution_id))
  with check (private.is_admin_of(institution_id));

drop policy if exists programmes_delete on public.programmes;
create policy programmes_delete on public.programmes
  for delete to authenticated
  using (private.is_admin_of(institution_id));

-- =================================================================== profiles
alter table public.profiles enable row level security;
revoke all on table public.profiles from anon, authenticated;
grant select on table public.profiles to authenticated;
-- Only the display name is self-editable. role / institution_id / onboarding
-- fields change only through SECURITY DEFINER functions (0008) or the service role.
grant update (full_name) on table public.profiles to authenticated;
grant all on table public.profiles to service_role;

drop policy if exists profiles_select on public.profiles;
create policy profiles_select on public.profiles
  for select to authenticated
  using (id = (select auth.uid()) or private.is_admin_of(institution_id));

drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));
-- INSERT: auth trigger only. DELETE: cascades from auth.users only.

-- =================================================================== students
alter table public.students enable row level security;
revoke all on table public.students from anon, authenticated;
grant select on table public.students to authenticated;
grant insert (institution_id, programme_id, roll_number, full_name, institutional_email,
              admission_year, current_semester, status)
  on table public.students to authenticated;
grant update (programme_id, roll_number, full_name, institutional_email, current_semester, status)
  on table public.students to authenticated;
grant all on table public.students to service_role;

drop policy if exists students_select on public.students;
create policy students_select on public.students
  for select to authenticated
  using (private.can_view_student(id));

drop policy if exists students_insert on public.students;
create policy students_insert on public.students
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists students_update on public.students;
create policy students_update on public.students
  for update to authenticated
  using (private.is_admin_of(institution_id))
  with check (private.is_admin_of(institution_id));
-- DELETE: no policy (erasure is a service-role operation; it cascades).

-- ================================================================== courses
alter table public.courses enable row level security;
revoke all on table public.courses from anon, authenticated;
grant select, delete on table public.courses to authenticated;
grant insert (institution_id, department_id, programme_id, code, title, credits, semester_number)
  on table public.courses to authenticated;
grant update (programme_id, code, title, credits, semester_number) on table public.courses to authenticated;
grant all on table public.courses to service_role;

drop policy if exists courses_select on public.courses;
create policy courses_select on public.courses
  for select to authenticated
  using (institution_id = (select private.current_institution_id()));

drop policy if exists courses_insert on public.courses;
create policy courses_insert on public.courses
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists courses_update on public.courses;
create policy courses_update on public.courses
  for update to authenticated
  using (private.is_admin_of(institution_id))
  with check (private.is_admin_of(institution_id));

drop policy if exists courses_delete on public.courses;
create policy courses_delete on public.courses
  for delete to authenticated
  using (private.is_admin_of(institution_id));

-- ========================================================= mentor_assignments
alter table public.mentor_assignments enable row level security;
revoke all on table public.mentor_assignments from anon, authenticated;
grant select, delete on table public.mentor_assignments to authenticated;
grant insert (institution_id, mentor_id, student_id, starts_on, ends_on)
  on table public.mentor_assignments to authenticated;
grant update (starts_on, ends_on) on table public.mentor_assignments to authenticated;
grant all on table public.mentor_assignments to service_role;

drop policy if exists mentor_assignments_select on public.mentor_assignments;
create policy mentor_assignments_select on public.mentor_assignments
  for select to authenticated
  using (
    mentor_id = (select auth.uid())
    or student_id = (select private.current_student_id())
    or private.is_admin_of(institution_id)
  );

drop policy if exists mentor_assignments_insert on public.mentor_assignments;
create policy mentor_assignments_insert on public.mentor_assignments
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists mentor_assignments_update on public.mentor_assignments;
create policy mentor_assignments_update on public.mentor_assignments
  for update to authenticated
  using (private.is_admin_of(institution_id))
  with check (private.is_admin_of(institution_id));

drop policy if exists mentor_assignments_delete on public.mentor_assignments;
create policy mentor_assignments_delete on public.mentor_assignments
  for delete to authenticated
  using (private.is_admin_of(institution_id));

-- ============================================================= course_faculty
alter table public.course_faculty enable row level security;
revoke all on table public.course_faculty from anon, authenticated;
grant select, delete on table public.course_faculty to authenticated;
grant insert (institution_id, course_id, faculty_id) on table public.course_faculty to authenticated;
grant all on table public.course_faculty to service_role;

drop policy if exists course_faculty_select on public.course_faculty;
create policy course_faculty_select on public.course_faculty
  for select to authenticated
  using (faculty_id = (select auth.uid()) or private.is_admin_of(institution_id));

drop policy if exists course_faculty_insert on public.course_faculty;
create policy course_faculty_insert on public.course_faculty
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

drop policy if exists course_faculty_delete on public.course_faculty;
create policy course_faculty_delete on public.course_faculty
  for delete to authenticated
  using (private.is_admin_of(institution_id));
-- UPDATE: no policy (delete and re-insert instead).

-- ============================================================ student_courses
alter table public.student_courses enable row level security;
revoke all on table public.student_courses from anon, authenticated;
grant select, delete on table public.student_courses to authenticated;
grant insert (institution_id, student_id, course_id, academic_year, semester, status,
              marks, grade, result_published_at)
  on table public.student_courses to authenticated;
grant update (status, marks, grade, result_published_at) on table public.student_courses to authenticated;
grant all on table public.student_courses to service_role;

drop policy if exists student_courses_select on public.student_courses;
create policy student_courses_select on public.student_courses
  for select to authenticated
  using (
    student_id = (select private.current_student_id())
    or private.is_mentor_of(student_id)
    or private.teaches_course(course_id)
    or private.is_admin_of(institution_id)
  );

drop policy if exists student_courses_insert on public.student_courses;
create policy student_courses_insert on public.student_courses
  for insert to authenticated
  with check (private.is_admin_of(institution_id));

-- Faculty record marks/grades for courses they teach; admins for their institution.
drop policy if exists student_courses_update on public.student_courses;
create policy student_courses_update on public.student_courses
  for update to authenticated
  using (private.teaches_course(course_id) or private.is_admin_of(institution_id))
  with check (private.teaches_course(course_id) or private.is_admin_of(institution_id));

drop policy if exists student_courses_delete on public.student_courses;
create policy student_courses_delete on public.student_courses
  for delete to authenticated
  using (private.is_admin_of(institution_id));

-- =========================================================== academic_records
alter table public.academic_records enable row level security;
revoke all on table public.academic_records from anon, authenticated;
grant select, delete on table public.academic_records to authenticated;
grant insert (student_id, academic_year, semester, sgpa, cgpa, credits_registered,
              credits_earned, result_status, published_at)
  on table public.academic_records to authenticated;
grant update (sgpa, cgpa, credits_registered, credits_earned, result_status, published_at)
  on table public.academic_records to authenticated;
grant all on table public.academic_records to service_role;

drop policy if exists academic_records_select on public.academic_records;
create policy academic_records_select on public.academic_records
  for select to authenticated
  using (private.can_view_student_personal(student_id));

drop policy if exists academic_records_insert on public.academic_records;
create policy academic_records_insert on public.academic_records
  for insert to authenticated
  with check (private.is_admin_of(private.student_institution_id(student_id)));

drop policy if exists academic_records_update on public.academic_records;
create policy academic_records_update on public.academic_records
  for update to authenticated
  using (private.is_admin_of(private.student_institution_id(student_id)))
  with check (private.is_admin_of(private.student_institution_id(student_id)));

drop policy if exists academic_records_delete on public.academic_records;
create policy academic_records_delete on public.academic_records
  for delete to authenticated
  using (private.is_admin_of(private.student_institution_id(student_id)));

-- ========================================================= attendance_records
alter table public.attendance_records enable row level security;
revoke all on table public.attendance_records from anon, authenticated;
grant select, delete on table public.attendance_records to authenticated;
grant insert (student_course_id, student_id, course_id, attendance_date, session_number, status)
  on table public.attendance_records to authenticated;
grant update (status) on table public.attendance_records to authenticated;
grant all on table public.attendance_records to service_role;

drop policy if exists attendance_records_select on public.attendance_records;
create policy attendance_records_select on public.attendance_records
  for select to authenticated
  using (private.can_view_student_personal(student_id) or private.teaches_course(course_id));

drop policy if exists attendance_records_insert on public.attendance_records;
create policy attendance_records_insert on public.attendance_records
  for insert to authenticated
  with check (
    private.teaches_course(course_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists attendance_records_update on public.attendance_records;
create policy attendance_records_update on public.attendance_records
  for update to authenticated
  using (
    private.teaches_course(course_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  )
  with check (
    private.teaches_course(course_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists attendance_records_delete on public.attendance_records;
create policy attendance_records_delete on public.attendance_records
  for delete to authenticated
  using (private.is_admin_of(private.student_institution_id(student_id)));

-- ================================================================ assignments
alter table public.assignments enable row level security;
revoke all on table public.assignments from anon, authenticated;
grant select, delete on table public.assignments to authenticated;
grant insert (institution_id, course_id, academic_year, title, max_score, due_at)
  on table public.assignments to authenticated;
grant update (title, max_score, due_at) on table public.assignments to authenticated;
grant all on table public.assignments to service_role;

drop policy if exists assignments_select on public.assignments;
create policy assignments_select on public.assignments
  for select to authenticated
  using (
    private.is_admin_of(institution_id)
    or private.teaches_course(course_id)
    or private.is_enrolled_self(course_id, academic_year)
    or private.mentors_student_in_course(course_id, academic_year)
  );

drop policy if exists assignments_insert on public.assignments;
create policy assignments_insert on public.assignments
  for insert to authenticated
  with check (private.teaches_course(course_id) or private.is_admin_of(institution_id));

drop policy if exists assignments_update on public.assignments;
create policy assignments_update on public.assignments
  for update to authenticated
  using (private.teaches_course(course_id) or private.is_admin_of(institution_id))
  with check (private.teaches_course(course_id) or private.is_admin_of(institution_id));

drop policy if exists assignments_delete on public.assignments;
create policy assignments_delete on public.assignments
  for delete to authenticated
  using (private.teaches_course(course_id) or private.is_admin_of(institution_id));

-- ===================================================== assignment_submissions
alter table public.assignment_submissions enable row level security;
revoke all on table public.assignment_submissions from anon, authenticated;
grant select, delete on table public.assignment_submissions to authenticated;
grant insert (assignment_id, student_id, status, submitted_at, score, graded_at)
  on table public.assignment_submissions to authenticated;
grant update (status, submitted_at, score, graded_at) on table public.assignment_submissions to authenticated;
grant all on table public.assignment_submissions to service_role;

drop policy if exists assignment_submissions_select on public.assignment_submissions;
create policy assignment_submissions_select on public.assignment_submissions
  for select to authenticated
  using (
    private.can_view_student_personal(student_id)
    or private.teaches_course(private.assignment_course_id(assignment_id))
  );

drop policy if exists assignment_submissions_insert on public.assignment_submissions;
create policy assignment_submissions_insert on public.assignment_submissions
  for insert to authenticated
  with check (
    private.teaches_course(private.assignment_course_id(assignment_id))
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists assignment_submissions_update on public.assignment_submissions;
create policy assignment_submissions_update on public.assignment_submissions
  for update to authenticated
  using (
    private.teaches_course(private.assignment_course_id(assignment_id))
    or private.is_admin_of(private.student_institution_id(student_id))
  )
  with check (
    private.teaches_course(private.assignment_course_id(assignment_id))
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists assignment_submissions_delete on public.assignment_submissions;
create policy assignment_submissions_delete on public.assignment_submissions
  for delete to authenticated
  using (private.is_admin_of(private.student_institution_id(student_id)));

-- ========================================================== engagement_events
alter table public.engagement_events enable row level security;
revoke all on table public.engagement_events from anon, authenticated;
grant select on table public.engagement_events to authenticated;
grant all on table public.engagement_events to service_role;

drop policy if exists engagement_events_select on public.engagement_events;
create policy engagement_events_select on public.engagement_events
  for select to authenticated
  using (private.can_view_student_personal(student_id));
-- INSERT / UPDATE / DELETE: no policy (server-side ingestion only).

-- =========================================================== risk_predictions
alter table public.risk_predictions enable row level security;
revoke all on table public.risk_predictions from anon, authenticated;
grant select on table public.risk_predictions to authenticated;
grant all on table public.risk_predictions to service_role;

drop policy if exists risk_predictions_select on public.risk_predictions;
create policy risk_predictions_select on public.risk_predictions
  for select to authenticated
  using (private.can_view_student_personal(student_id));
-- INSERT / UPDATE / DELETE: no policy. Predictions are written by the server-side
-- scoring job only and are immutable to API users.

-- =============================================================== risk_factors
alter table public.risk_factors enable row level security;
revoke all on table public.risk_factors from anon, authenticated;
grant select on table public.risk_factors to authenticated;
grant all on table public.risk_factors to service_role;

-- Visible exactly when the parent prediction is visible (the subquery is itself
-- filtered by the risk_predictions policy).
drop policy if exists risk_factors_select on public.risk_factors;
create policy risk_factors_select on public.risk_factors
  for select to authenticated
  using (exists (
    select 1 from public.risk_predictions rp where rp.id = risk_factors.prediction_id
  ));
-- INSERT / UPDATE / DELETE: no policy (server-side only).

-- ============================================================== interventions
alter table public.interventions enable row level security;
revoke all on table public.interventions from anon, authenticated;
grant select, delete on table public.interventions to authenticated;
grant insert (student_id, prediction_id, intervention_type, status, source, assigned_to, due_on, notes)
  on table public.interventions to authenticated;
grant update (status, assigned_to, due_on, notes, outcome, completed_at)
  on table public.interventions to authenticated;
grant all on table public.interventions to service_role;

-- Students have no direct access (notes are staff-only); they use
-- public.get_my_recommended_actions().
drop policy if exists interventions_select on public.interventions;
create policy interventions_select on public.interventions
  for select to authenticated
  using (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists interventions_insert on public.interventions;
create policy interventions_insert on public.interventions
  for insert to authenticated
  with check (
    (source = 'mentor' and private.is_mentor_of(student_id))
    or (source = 'admin' and private.is_admin_of(private.student_institution_id(student_id)))
  );

drop policy if exists interventions_update on public.interventions;
create policy interventions_update on public.interventions
  for update to authenticated
  using (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  )
  with check (
    private.is_mentor_of(student_id)
    or private.is_admin_of(private.student_institution_id(student_id))
  );

drop policy if exists interventions_delete on public.interventions;
create policy interventions_delete on public.interventions
  for delete to authenticated
  using (private.is_admin_of(private.student_institution_id(student_id)));

-- ============================================================== notifications
alter table public.notifications enable row level security;
revoke all on table public.notifications from anon, authenticated;
grant select on table public.notifications to authenticated;
grant update (read_at) on table public.notifications to authenticated;
grant all on table public.notifications to service_role;

drop policy if exists notifications_select on public.notifications;
create policy notifications_select on public.notifications
  for select to authenticated
  using (recipient_id = (select auth.uid()));

drop policy if exists notifications_update on public.notifications;
create policy notifications_update on public.notifications
  for update to authenticated
  using (recipient_id = (select auth.uid()))
  with check (recipient_id = (select auth.uid()));
-- INSERT / DELETE: no policy (server-side only).

-- ================================================================= audit_logs
alter table public.audit_logs enable row level security;
revoke all on table public.audit_logs from anon, authenticated;
grant select on table public.audit_logs to authenticated;
grant all on table public.audit_logs to service_role;

drop policy if exists audit_logs_select on public.audit_logs;
create policy audit_logs_select on public.audit_logs
  for select to authenticated
  using (private.is_admin_of(institution_id));
-- INSERT / UPDATE / DELETE: no policy (written by trigger only; append-only).
