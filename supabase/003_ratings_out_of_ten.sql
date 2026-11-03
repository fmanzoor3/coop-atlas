-- Run once after 001_shared_library.sql. Safe to rerun.
-- Converts existing 1–5 ratings to 1–10, preserving notes and each persona.
begin;
create table if not exists coop_private.schema_migrations (
  version text primary key,
  applied_at timestamptz not null default now()
);
alter table coop_private.schema_migrations enable row level security;
revoke all on coop_private.schema_migrations from public, anon, authenticated;
lock table public.coop_ratings in access exclusive mode;
do $$
begin
  if not exists(select 1 from coop_private.schema_migrations where version='003_ratings_out_of_ten') then
    alter table public.coop_ratings drop constraint coop_ratings_stars_check;
    update public.coop_ratings set stars=stars*2 where stars is not null;
    alter table public.coop_ratings add constraint coop_ratings_stars_check check (stars between 1 and 10);
    insert into coop_private.schema_migrations(version) values ('003_ratings_out_of_ten');
  end if;
end; $$;

create or replace function public.coop_rating_scale() returns integer
language sql stable set search_path = '' as $$ select 10; $$;
revoke all on function public.coop_rating_scale() from public, anon, authenticated;
grant execute on function public.coop_rating_scale() to authenticated;

-- Require the new versioned endpoint, so stale 1–5 clients cannot mislabel scores.
revoke insert, update, delete on public.coop_ratings from public, anon, authenticated;
revoke insert(game_id, profile_name, stars, positives, negatives, note),
  update(stars, positives, negatives, note) on public.coop_ratings from authenticated;

create or replace function public.coop_save_rating_v10(
  p_game_id text,
  p_profile_name text,
  p_score smallint,
  p_note text,
  p_positives text[],
  p_negatives text[],
  p_expected_updated_at timestamptz
) returns public.coop_ratings
language plpgsql security definer set search_path = '' as $$
declare selected_profile text; saved public.coop_ratings;
begin
  if not coop_private.is_member() then raise exception 'Pair this device before rating' using errcode='42501'; end if;
  selected_profile := coop_private.current_profile();
  if p_profile_name is distinct from selected_profile then raise exception 'Profile changed. Review the selected profile before rating.' using errcode='40001'; end if;
  if p_score is not null and (p_score < 1 or p_score > 10) then
    raise exception 'Choose a rating from 1 to 10' using errcode='22023';
  end if;
  if not exists(select 1 from public.coop_game_state where game_id=p_game_id and play_state='Played' and not archived) then
    raise exception 'Mark this game Played before rating' using errcode='22023';
  end if;
  if p_expected_updated_at is null then
    begin
      insert into public.coop_ratings(game_id,profile_name,stars,note,positives,negatives)
      values (p_game_id,selected_profile,p_score,coalesce(p_note,''),coalesce(p_positives,'{}'),coalesce(p_negatives,'{}'))
      returning * into saved;
    exception when unique_violation then
      raise exception 'This rating changed on another device. Refresh before saving.' using errcode='40001';
    end;
  else
    update public.coop_ratings set stars=p_score,note=coalesce(p_note,''),
      positives=coalesce(p_positives,'{}'),negatives=coalesce(p_negatives,'{}')
    where game_id=p_game_id and profile_name=selected_profile and updated_at=p_expected_updated_at
    returning * into saved;
    if not found then
      raise exception 'This rating changed on another device. Refresh before saving.' using errcode='40001';
    end if;
  end if;
  return saved;
end; $$;
revoke all on function public.coop_save_rating_v10(text,text,smallint,text,text[],text[],timestamptz) from public, anon, authenticated;
grant execute on function public.coop_save_rating_v10(text,text,smallint,text,text[],text[],timestamptz) to authenticated;
commit;
