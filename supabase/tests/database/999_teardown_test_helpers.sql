-- Removes the helpers installed by 000_setup_test_helpers.sql.
begin;
select plan(1);
drop schema if exists tests cascade;
select hasnt_schema('tests', 'test helpers removed');
select * from finish();
commit;
