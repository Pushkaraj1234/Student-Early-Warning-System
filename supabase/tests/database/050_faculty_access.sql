-- Faculty scope: course-bound academic records of courses they teach only. No access
-- to semester results, predictions, interventions or engagement.
begin;
select plan(31);

select tests.create_fixture();
select tests.authenticate_as(tests.uid('user_f1'));

-- ---------------------------------------------------------- reads: own courses
select set_eq($$ select id from public.student_courses $$, array[tests.uid('sc_s1_a1')],
              'faculty sees enrolments only for courses they teach');
select set_eq($$ select id from public.attendance_records $$, array[tests.uid('att_s1_a1')],
              'faculty sees attendance only for courses they teach');
select set_eq($$ select id from public.students $$, array[tests.uid('student_s1')],
              'faculty sees only students enrolled in their courses');
select is_empty($$ select id from public.academic_records $$, 'faculty cannot read semester results (SGPA/CGPA)');
select is_empty($$ select id from public.risk_predictions $$, 'faculty cannot read risk predictions');
select is_empty($$ select id from public.risk_factors $$, 'faculty cannot read risk factors');
select is_empty($$ select id from public.interventions $$, 'faculty cannot read interventions');
select is_empty($$ select id from public.engagement_events $$, 'faculty cannot read engagement events');
select set_eq($$ select id from public.assignment_submissions $$, array[tests.uid('sub_s1_a1')],
              'faculty sees submissions only for their course assignments');
select set_eq($$ select id from public.assignments $$, array[tests.uid('asg_a1')],
              'faculty sees assignments only for courses they teach');
select set_eq($$ select course_id from public.course_faculty $$, array[tests.uid('course_a1')],
              'faculty sees only their own teaching assignments');
select is_empty(format('select * from public.students where id = %L', tests.uid('student_s2')),
                'faculty cannot access students outside their courses');
select is_empty(format('select * from public.student_courses where id = %L', tests.uid('sc_s1_a2')),
                'faculty cannot access the same student''s other courses');

-- ------------------------------------------------------------ marks & grades
select is(tests.affected_rows(format(
            'update public.student_courses set status = %L, marks = 85, grade = %L where id = %L',
            'completed', 'A+', tests.uid('sc_s1_a1'))),
          1, 'faculty can record marks and grade for their course');
select is((select grade_points from public.student_courses where id = tests.uid('sc_s1_a1')),
          9::smallint, 'grade points are derived from the UGC grade (A+ = 9)');
select is(tests.affected_rows(format('update public.student_courses set marks = 50 where id = %L', tests.uid('sc_s1_a2'))),
          0, 'faculty cannot record marks for a course they do not teach');
select throws_ok(
  format('update public.student_courses set student_id = %L where id = %L', tests.uid('student_s2'), tests.uid('sc_s1_a1')),
  '42501', null, 'faculty cannot move an enrolment to another student');

-- ---------------------------------------------------------------- attendance
select lives_ok(
  format($$ insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date, status)
            values (%L, %L, %L, date '2026-09-02', 'late') $$,
         tests.uid('sc_s1_a1'), tests.uid('student_s1'), tests.uid('course_a1')),
  'faculty can record attendance for their course');
select is(
  (select recorded_by from public.attendance_records
   where student_course_id = tests.uid('sc_s1_a1') and attendance_date = date '2026-09-02'),
  tests.uid('user_f1'),
  'recorded_by is stamped from the JWT');
select throws_ok(
  format($$ insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date, status)
            values (%L, %L, %L, date '2026-09-02', 'present') $$,
         tests.uid('sc_s1_a2'), tests.uid('student_s1'), tests.uid('course_a2')),
  '42501', null, 'faculty cannot record attendance for a course they do not teach');
select throws_ok(
  format($$ insert into public.attendance_records (student_course_id, student_id, course_id, attendance_date,
            status, recorded_by) values (%L, %L, %L, date '2026-09-03', 'present', %L) $$,
         tests.uid('sc_s1_a1'), tests.uid('student_s1'), tests.uid('course_a1'), tests.uid('user_a1')),
  '42501', null, 'faculty cannot forge recorded_by');
select is(tests.affected_rows(format('update public.attendance_records set status = %L where id = %L',
                                     'absent', tests.uid('att_s1_a1'))),
          1, 'faculty can correct attendance for their course');
select is(tests.affected_rows(format('delete from public.attendance_records where id = %L', tests.uid('att_s1_a1'))),
          0, 'faculty cannot delete attendance (admin only)');

-- ------------------------------------------------ assignments & submissions
select lives_ok(
  format($$ insert into public.assignments (institution_id, course_id, academic_year, title, max_score, due_at)
            values (%L, %L, '2026-27', 'Faculty created', 10, now() + interval '7 days') $$,
         tests.uid('inst_a'), tests.uid('course_a1')),
  'faculty can create assignments for their course');
select throws_ok(
  format($$ insert into public.assignments (institution_id, course_id, academic_year, title, max_score, due_at)
            values (%L, %L, '2026-27', 'Not my course', 10, now() + interval '7 days') $$,
         tests.uid('inst_a'), tests.uid('course_a2')),
  '42501', null, 'faculty cannot create assignments for other courses');
select is(tests.affected_rows(format('update public.assignment_submissions set score = 18 where id = %L',
                                     tests.uid('sub_s1_a1'))),
          1, 'faculty can grade submissions in their course');
select throws_ok(
  format('update public.assignment_submissions set score = 25 where id = %L', tests.uid('sub_s1_a1')),
  '23514', null, 'score above max_score is rejected');
select is(tests.affected_rows(format(
            'update public.assignment_submissions set score = 10, graded_at = now() where id = %L',
            tests.uid('sub_s2_a2'))),
          0, 'faculty cannot grade submissions in other courses');
select throws_ok(
  format($$ insert into public.academic_records (student_id, academic_year, semester, credits_registered,
            credits_earned, result_status) values (%L, '2026-27', 1, 0, 0, 'pending') $$, tests.uid('student_s1')),
  '42501', null, 'faculty cannot create semester results');

-- ------------------------------------------------ other institution's faculty
select tests.authenticate_as(tests.uid('user_f2'));
select set_eq($$ select id from public.student_courses $$, array[tests.uid('sc_s3_b1')],
              'institution B faculty sees only their own course enrolments');
select is_empty(format('select * from public.attendance_records where course_id = %L', tests.uid('course_a1')),
                'institution B faculty cannot access institution A attendance');

select * from finish();
rollback;
