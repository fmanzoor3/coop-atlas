# Shared library foundation

Status: shared mode is implemented and opt-in. No browser save is automatically
uploaded or replaced. The original `coopAtlasGames` save remains separate.

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
4. Open the app, choose Fred or Manu, and pair with one code per browser/app.
   No user emails are needed. No further SQL is required for the client.

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


## Client behaviour and verification

`sync.js` uses the locally bundled Supabase JS client 2.118.0. The auth session has
its own `coopDbAuth` storage key. Paired devices remember their profile and can
switch in profile settings. Shared data is cached separately from local saves.
The Together inbox shows suggestions, Yes/Maybe/Pass responses and Ready to play.
Unread badges are based on persisted timestamps. This is in-app notification,
not phone push. Rating and response updates use timestamp conditions; game edits
use revision and field conflict checks. Edits are paused while offline/saving.
Failed game edits remain available under Export unsaved changes in profile settings.

Refresh occurs every 20 seconds while visible, on app focus, and after writes.
This avoids needing additional Realtime publication setup. First transfer is
explicit, downloads a backup, and inserts only missing records. It never replaces
existing shared records; reconciling conflicting old saves remains a manual edit.
Shared exports include ratings/proposals/responses in an additional `shared` field;
current import restores missing games only, not ratings or proposal history.
Personal ratings are recorded; fit scores still use the existing editorial model.

Tests: `python tests/shared-ui.py` from the repository root, with Playwright and
Chromium available. Tests use two isolated browser sessions and a deterministic
API fixture, never production pairing codes. They cover pairing persistence,
no automatic upload, shared state, individual ratings, responses, switching,
failed-save recovery, explicit transfer, and mobile/desktop widths. The SQL tests
separately execute RLS and pairing rules in PostgreSQL. Live auth configuration
and unauthenticated REST denial were verified; first physical-device pairing and
cross-device syncing still require Fred and Manu's own browsers.
