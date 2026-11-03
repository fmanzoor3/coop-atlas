# Shared library foundation

Status: schema and setup instructions are ready. The game app is still local-only;
no browser save has been uploaded, modified, or automatically migrated.

Project: https://eoinghlgylynomxaqhji.supabase.co
`client-config.json` contains the public browser connection settings, not a secret.
Never add a service-role key, database password, or generated pairing code here.

## Owner setup

Use ../setup.html in the published site for copy buttons.

1. In the project's SQL Editor, run `001_shared_library.sql` once. It is atomic
   and creates empty tables. It deliberately fails if these tables already exist
   rather than dropping or replacing existing data. Do not rerun it after success.
2. Authentication > Sign In / Providers > Anonymous Sign-ins: enable and save.
3. Run `002_generate_pairing_codes.sql` in a new query. Keep the four resulting
   codes private. Each is one-use and expires after seven days. The query can be
   rerun to generate additional codes. It does not revoke earlier unused codes.
4. Return to the development chat after success. No user emails are needed.

The publishable key can read project auth settings, but cannot execute SQL or
change authentication configuration. These owner actions must be completed in
the Supabase dashboard. Do not send privileged credentials to work around this.

## Access and data model

Devices use Supabase anonymous Auth (the authenticated database role). Pairing
redeems a random UUID-derived token through `coop_pair_device`; only its
SHA-256 hash is stored in a non-exposed schema. Redemption and enrollment are one
transaction. Anonymous visitors without a paired device have no shared access.

Fred and Manu are personas, not separate verified identities. Any paired trusted
device may switch its persona in Settings. Ratings and responses are keyed by
persona so they are consistent across that person's devices. RLS checks writes
against the currently selected persona; changing persona is deliberately allowed.
The browser can only see/change its own device registration. Owner-only SQL can
revoke access by deleting a device after handling any referenced audit records.

- `coop_devices`: trusted device auth IDs, current persona, last-seen marker.
- `coop_game_state`: per-game shared progress, old shared verdict, custom/edited
  game data, archive marker and revision. Seed keys are `seed:<existing id>`;
  additions use `custom:<UUID>` to avoid colliding IDs on different devices.
- `coop_ratings`: optional 1–5 stars, positive/negative tags and notes per persona.
- `coop_suggestions`: each persona's proposal per game, message, withdrawal flag.
- `coop_responses`: the other persona's Yes/Maybe/Pass response per proposal.

Built-in catalogue and editorial data stay in the repository. Existing joint
verdicts must not be converted into either person's individual ratings. The first
import must be reviewed and backed up; do not bulk replace server state with a
browser's complete array. Use revision-conditional game updates to detect stale
writes and field-level merges for independent changes. Supabase REST column
grants intentionally prevent clients from changing author IDs or revision values.
The client must omit these fields during inserts/updates and read returned rows.

Unread suggestions/responses are durable database records, not ephemeral socket
events. Start with refresh-on-focus/polling; enable private Realtime subscriptions
only after live access tests. Push notifications are outside this first stage.

## Tests

`npm --prefix supabase/tests install` then `npm --prefix supabase/tests test`.
Tests run the actual migration in PGlite (PostgreSQL), with a stub of Supabase Auth,
and exercise anonymous/unpaired denial, pairing reuse/expiry, independent ratings,
profile switching, multi-device access, suggestions/responses and stale revisions.
A live two-device test is still required after owner setup and client integration.

## Sessions and backups

Keep `coopAtlasGames` and version-1 JSON export compatible during migration.
Anonymous sessions can be lost when browser storage is cleared. Re-pairing with
a fresh code recovers database access; it does not create a new Fred/Manu profile.
Safari and Home Screen sessions are separate and may each need a pairing code.
Keep exports available after syncing; do not silently overwrite local save files.
