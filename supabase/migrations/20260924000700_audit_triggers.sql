-- SEWS 0007 — audit trail for sensitive tables.
-- Records actor (auth.uid(), null for service/system writes), action, table, record id
-- and — for updates — the names of changed columns. Row contents are deliberately not
-- copied (data minimisation; an erasure request must not leave personal data behind
-- in the audit log). Updates that change nothing but updated_at are not logged.
-- Idempotent: safe to re-run.

create or replace function private.write_audit_log()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_row jsonb;
  v_old jsonb;
  v_changed text[] := '{}';
  v_institution_id uuid;
begin
  if tg_op = 'DELETE' then
    v_row := to_jsonb(old);
  else
    v_row := to_jsonb(new);
  end if;

  if tg_op = 'UPDATE' then
    v_old := to_jsonb(old);
    select coalesce(array_agg(n.key order by n.key), '{}')
      into v_changed
    from jsonb_each(v_row) as n (key, value)
    where n.value is distinct from (v_old -> n.key)
      and n.key <> 'updated_at';

    if cardinality(v_changed) = 0 then
      return null;
    end if;
  end if;

  if v_row ? 'institution_id' then
    v_institution_id := (v_row ->> 'institution_id')::uuid;
  end if;

  if v_institution_id is null and v_row ? 'student_id' then
    select s.institution_id into v_institution_id
    from public.students s
    where s.id = (v_row ->> 'student_id')::uuid;
  end if;

  insert into public.audit_logs (institution_id, actor_id, action, table_name, record_id, changed_columns)
  values (
    v_institution_id,
    (select auth.uid()),
    lower(tg_op),
    tg_table_name,
    (v_row ->> 'id')::uuid,
    v_changed
  );

  return null;
end;
$$;

revoke all on function private.write_audit_log() from public, anon, authenticated;

do $$
declare
  v_table text;
begin
  foreach v_table in array array[
    'profiles', 'students', 'mentor_assignments', 'course_faculty', 'student_courses',
    'academic_records', 'attendance_records', 'assignments', 'assignment_submissions',
    'interventions', 'risk_predictions'
  ]
  loop
    execute format('drop trigger if exists write_audit_log on public.%I', v_table);
    execute format(
      'create trigger write_audit_log after insert or update or delete on public.%I '
      'for each row execute function private.write_audit_log()',
      v_table
    );
  end loop;
end
$$;
