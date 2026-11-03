-- Run in Supabase SQL Editor AFTER 001_shared_library.sql succeeds.
-- Generates four private, one-use device codes, valid for seven days.
-- Keep the query results private. This file contains no actual pairing codes.
with codes as materialized (
  select replace(gen_random_uuid()::text, '-', '') as code from generate_series(1, 4)
), stored as (
  insert into coop_private.pairing_codes(token_hash, expires_at)
  select sha256(convert_to(code, 'UTF8')), now() + interval '7 days' from codes
  returning token_hash
)
select code as pairing_code, 'One device; expires in 7 days' as usage
from codes join stored on stored.token_hash = sha256(convert_to(code, 'UTF8'));
