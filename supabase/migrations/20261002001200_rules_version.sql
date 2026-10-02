-- SEWS schema 4.1.0: record which rule-set version produced each rule suggestion.
--
-- Closes the "Known gap" in docs/architecture/versioning.md: interventions stored the rule that fired
-- (rule_id) but not the version of the rule set, so a later threshold change could not be told apart
-- in stored data. The recommendation job writes RULES_VERSION from
-- services/sews_services/recommendations/engine.py.
--
-- Additive and backwards compatible: rows created before this migration keep rule_version null
-- (unknown — nothing is back-filled, because their rule set cannot be proven). The mobile contract is
-- unchanged, so minimum_mobile_app stays 2.0.0. Idempotent (safe to re-run).

alter table public.interventions add column if not exists rule_version text;

alter table public.interventions drop constraint if exists interventions_rule_version_format;
alter table public.interventions add constraint interventions_rule_version_format
  check (rule_version is null or rule_version ~ '^rules-[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}$');

comment on column public.interventions.rule_version is
  'Rule-set version (e.g. rules-1.0.0) that produced this suggestion; null for staff-created rows and for rows created before schema 4.1.0.';

-- Provenance rules, checked for every writer including the service role:
--   * a new row carries rule_id and rule_version together, or neither;
--   * only rule-engine output (source 'model_rule') may carry them;
--   * once stored, neither can change.
-- Rows that existed before this migration are not re-checked (only new inserts are), so existing
-- suggestions with a rule_id and no version keep working through the intervention workflow.
create or replace function private.enforce_rule_provenance()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    if (new.rule_id is null) <> (new.rule_version is null) then
      raise exception 'sews:rule_id_and_version_required_together' using errcode = '23514';
    end if;
    if new.rule_id is not null and new.source <> 'model_rule' then
      raise exception 'sews:rule_provenance_only_for_rule_output' using errcode = '23514';
    end if;
    return new;
  end if;

  if new.rule_id is distinct from old.rule_id or new.rule_version is distinct from old.rule_version then
    raise exception 'sews:rule_provenance_is_immutable' using errcode = '23514';
  end if;
  return new;
end
$$;

revoke all on function private.enforce_rule_provenance() from public, anon, authenticated;

drop trigger if exists enforce_rule_provenance on public.interventions;
create trigger enforce_rule_provenance before insert or update on public.interventions
  for each row execute function private.enforce_rule_provenance();

-- Contract version (MINOR: additive column).
create or replace function public.get_platform_versions()
returns table (component text, version text)
language sql
immutable
set search_path = ''
as $$
  values ('database_schema', '4.1.0'), ('minimum_mobile_app', '2.0.0'), ('inference_api', '1.0.0');
$$;

revoke all on function public.get_platform_versions() from public, anon;
grant execute on function public.get_platform_versions() to authenticated, service_role;
