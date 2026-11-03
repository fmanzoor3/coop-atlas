-- Coop Database: initial shared-data schema. Run once in Supabase SQL Editor.
-- This creates empty tables only. It does not import or overwrite browser saves.
-- Access stays closed until the project owner pairs each trusted device (separate step).
begin;

create schema if not exists coop_private;
revoke all on schema coop_private from public, anon, authenticated;
grant usage on schema coop_private to authenticated;

create table public.coop_devices (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null check (display_name in ('Fred', 'Manu')),
  last_seen_at timestamptz not null default now()
);
alter table public.coop_devices enable row level security;
revoke all on public.coop_devices from public, anon, authenticated;
grant select on public.coop_devices to authenticated;
grant update(last_seen_at, display_name) on public.coop_devices to authenticated;

-- Security definer avoids recursive membership policies. No user-supplied arguments.
create function coop_private.is_member() returns boolean
language sql stable security definer set search_path = ''
as $$ select exists(select 1 from public.coop_devices where user_id = (select auth.uid())); $$;
revoke all on function coop_private.is_member() from public, anon, authenticated;
grant execute on function coop_private.is_member() to authenticated;
-- A trusted device can switch persona; this is not a separate login identity.
create function coop_private.current_profile() returns text
language sql stable security definer set search_path = ''
as $$ select display_name from public.coop_devices where user_id = (select auth.uid()); $$;
revoke all on function coop_private.current_profile() from public, anon, authenticated;
grant execute on function coop_private.current_profile() to authenticated;
create policy members_read on public.coop_devices for select to authenticated
  using (user_id = (select auth.uid()));
create policy own_read_marker on public.coop_devices for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- Stable keys: seed:1 for built-in games, custom:<UUID> for additions.
-- game_data holds custom game details / edited fields, not an entire database blob.
create table public.coop_game_state (
  game_id text primary key check (game_id ~ '^(seed:[0-9]+|custom:[0-9a-f-]{36})$'),
  play_state text not null default 'Not played'
    check (play_state in ('Not played', 'Currently playing', 'Played')),
  shared_verdict text not null default 'Unrated'
    check (shared_verdict in ('Unrated', 'Good suggestion', 'Not sure', 'Probably won''t play', 'Loved', 'Okay', 'Disliked')),
  game_data jsonb not null default '{}' check (jsonb_typeof(game_data) = 'object'),
  archived boolean not null default false,
  revision bigint not null default 1,
  updated_by uuid not null default auth.uid() references public.coop_devices(user_id),
  updated_at timestamptz not null default now()
);
alter table public.coop_game_state enable row level security;
revoke all on public.coop_game_state from public, anon, authenticated;
grant select on public.coop_game_state to authenticated;
grant insert(game_id, play_state, shared_verdict, game_data, archived) on public.coop_game_state to authenticated;
grant update(play_state, shared_verdict, game_data, archived) on public.coop_game_state to authenticated;
create policy shared_games_read on public.coop_game_state for select to authenticated
  using ((select coop_private.is_member()));
create policy shared_games_insert on public.coop_game_state for insert to authenticated
  with check ((select coop_private.is_member()));
create policy shared_games_update on public.coop_game_state for update to authenticated
  using ((select coop_private.is_member())) with check ((select coop_private.is_member()));

create function coop_private.stamp_game() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_by := auth.uid();
  new.updated_at := clock_timestamp();
  if tg_op = 'UPDATE' then new.revision := old.revision + 1; else new.revision := 1; end if;
  return new;
end; $$;
revoke all on function coop_private.stamp_game() from public, anon, authenticated;
create trigger stamp_game before insert or update on public.coop_game_state
  for each row execute function coop_private.stamp_game();

create table public.coop_ratings (
  game_id text not null references public.coop_game_state(game_id),
  profile_name text not null default coop_private.current_profile() check (profile_name in ('Fred', 'Manu')),
  stars smallint check (stars between 1 and 5),
  positives text[] not null default '{}' check (positives <@ array['teamwork','combat','strategy','story','progression','replayability','skill']),
  negatives text[] not null default '{}' check (negatives <@ array['repetitive','button-mashy','limited-role','too-hard','too-slow','too-chaotic']),
  note text not null default '' check (length(note) <= 4000),
  updated_at timestamptz not null default now(),
  primary key(game_id, profile_name)
);
alter table public.coop_ratings enable row level security;
revoke all on public.coop_ratings from public, anon, authenticated;
grant select, delete on public.coop_ratings to authenticated;
grant insert(game_id, profile_name, stars, positives, negatives, note) on public.coop_ratings to authenticated;
grant update(stars, positives, negatives, note) on public.coop_ratings to authenticated;
create policy ratings_read on public.coop_ratings for select to authenticated
  using ((select coop_private.is_member()));
create policy ratings_insert on public.coop_ratings for insert to authenticated
  with check ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()));
create policy ratings_update on public.coop_ratings for update to authenticated
  using ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()))
  with check ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()));
create policy ratings_delete on public.coop_ratings for delete to authenticated
  using ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()));

create table public.coop_suggestions (
  id uuid primary key default gen_random_uuid(),
  game_id text not null references public.coop_game_state(game_id),
  proposed_by text not null default coop_private.current_profile() check (proposed_by in ('Fred', 'Manu')),
  message text not null default '' check (length(message) <= 4000),
  withdrawn boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(game_id, proposed_by)
);
alter table public.coop_suggestions enable row level security;
revoke all on public.coop_suggestions from public, anon, authenticated;
grant select on public.coop_suggestions to authenticated;
grant insert(game_id, message) on public.coop_suggestions to authenticated;
grant update(message, withdrawn) on public.coop_suggestions to authenticated;
create policy suggestions_read on public.coop_suggestions for select to authenticated
  using ((select coop_private.is_member()));
create policy suggestions_insert on public.coop_suggestions for insert to authenticated
  with check ((select coop_private.is_member()) and proposed_by = (select coop_private.current_profile()));
create policy suggestions_update on public.coop_suggestions for update to authenticated
  using ((select coop_private.is_member()) and proposed_by = (select coop_private.current_profile()))
  with check ((select coop_private.is_member()) and proposed_by = (select coop_private.current_profile()));

create table public.coop_responses (
  suggestion_id uuid not null references public.coop_suggestions(id) on delete cascade,
  profile_name text not null default coop_private.current_profile() check (profile_name in ('Fred', 'Manu')),
  response text not null check (response in ('yes', 'maybe', 'pass')),
  updated_at timestamptz not null default now(),
  primary key(suggestion_id, profile_name)
);
alter table public.coop_responses enable row level security;
revoke all on public.coop_responses from public, anon, authenticated;
grant select, delete on public.coop_responses to authenticated;
grant insert(suggestion_id, profile_name, response) on public.coop_responses to authenticated;
grant update(response) on public.coop_responses to authenticated;
create policy responses_read on public.coop_responses for select to authenticated
  using ((select coop_private.is_member()));
create policy responses_insert on public.coop_responses for insert to authenticated
  with check ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()) and exists (
    select 1 from public.coop_suggestions s where s.id = suggestion_id and s.proposed_by <> (select coop_private.current_profile()) and not s.withdrawn
  ));
create policy responses_update on public.coop_responses for update to authenticated
  using ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()))
  with check ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()) and exists (
    select 1 from public.coop_suggestions s where s.id = suggestion_id and s.proposed_by <> (select coop_private.current_profile()) and not s.withdrawn
  ));
create policy responses_delete on public.coop_responses for delete to authenticated
  using ((select coop_private.is_member()) and profile_name = (select coop_private.current_profile()));

create function coop_private.stamp_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at := clock_timestamp(); return new; end; $$;
revoke all on function coop_private.stamp_updated_at() from public, anon, authenticated;
create trigger stamp_rating before insert or update on public.coop_ratings
  for each row execute function coop_private.stamp_updated_at();
create trigger stamp_suggestion before insert or update on public.coop_suggestions
  for each row execute function coop_private.stamp_updated_at();
create trigger stamp_response before insert or update on public.coop_responses
  for each row execute function coop_private.stamp_updated_at();

create index coop_suggestions_updated on public.coop_suggestions(updated_at);
create index coop_responses_updated on public.coop_responses(updated_at);

-- Private one-use pairing tokens. Only their hashes are stored.
create table coop_private.pairing_codes (
  token_hash bytea primary key,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  consumed_by uuid references auth.users(id) on delete set null
);
revoke all on coop_private.pairing_codes from public, anon, authenticated;
alter table coop_private.pairing_codes enable row level security;

create function public.coop_pair_device(pairing_code text, profile_name text)
returns text language plpgsql security definer set search_path = '' as $$
declare device_id uuid := auth.uid(); redeemed bytea;
begin
  if device_id is null then raise exception 'Sign in anonymously before pairing'; end if;
  if profile_name not in ('Fred', 'Manu') or profile_name is null then raise exception 'Choose Fred or Manu'; end if;
  if exists(select 1 from public.coop_devices where user_id = device_id) then
    return (select display_name from public.coop_devices where user_id = device_id);
  end if;
  if pairing_code is null or length(trim(pairing_code)) <> 32 then raise exception 'Invalid or expired pairing code'; end if;
  update coop_private.pairing_codes set consumed_at = clock_timestamp(), consumed_by = device_id
    where token_hash = sha256(convert_to(lower(trim(pairing_code)), 'UTF8'))
      and consumed_at is null and expires_at > clock_timestamp()
    returning token_hash into redeemed;
  if redeemed is null then raise exception 'Invalid or expired pairing code'; end if;
  insert into public.coop_devices(user_id, display_name) values (device_id, profile_name);
  return profile_name;
end; $$;
revoke all on function public.coop_pair_device(text, text) from public, anon, authenticated;
grant execute on function public.coop_pair_device(text, text) to authenticated;

-- Realtime subscriptions are optional; persisted rows remain available after closing the app.
-- Do not publish these tables to Realtime until membership has been configured and tested.
commit;
