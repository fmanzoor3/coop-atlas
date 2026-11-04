# Coop Database

Personal co-op discovery library for Farid and Manu. Static GitHub Pages site:
https://fmanzoor3.github.io/coop-atlas/

## Architecture

`index.html` defines the interface, `styles.css` contains responsive styling,
and `app.js` contains behaviour, metadata and the unchanged 167-game seed catalogue.
There is no application build step or service worker. Optional shared mode uses
Supabase with anonymously authenticated, privately paired devices. The UI includes
Discover / Library / Saved navigation, category tabs, editing, status/verdict controls, search, filters, JSON
import/export, detail dialogs and a screenshot lightbox. There are 152 Steam ID
mappings, 30 detailed assessments and 24 editorial entries (coverage can overlap).
Images load directly from Steam CDNs and several third-party sites. Details use
Steam's appdetails API through proxy.cors.dev, with memory/sessionStorage caching
and fallback messaging. Mapping accuracy has not been independently audited.

## Saved data

Keep `coopAtlasGames` unchanged: it stores the complete games array, including
user changes and additions. Existing legacy statuses are mapped to playState and
verdict in memory on load. Export is `{version:1, exported, games}`; the filename
is now `coop-database-backup.json`. Existing backup files remain compatible.
In local mode, import replaces the array after confirmation. In shared mode,
transfer adds missing records only and preserves existing shared records.

Safari and an installed iPhone Home Screen app have separate localStorage.
Export from BOTH contexts before removing an app or clearing any website data.
Pair each browser/app separately to access the same shared database, or use JSON
backups for the local-only library. See WebKit's Safari 17.2 release article:
https://webkit.org/blog/14787/webkit-features-in-safari-17-2/

## Icons and iPhone verification

`icon.svg` is the checked-in artwork source. `scripts/render-icons.py` renders it
using Playwright/Chromium and Pillow, flattening to RGB PNG with a purple
background. It produces 180px Apple icons and 192/512px manifest icons. iOS
applies its own icon mask. Keep the versioned touch-icon filename in sync with
the HTML when changing artwork; it avoids reusing the previous icon URL.

The November 2026 audit found the previous PNG valid: 180x180 RGBA, all alpha
values 255, valid chunk CRCs, served HTTP 200 as image/png. Live HTML, manifest
and PNG matched main byte for byte. HTML/manifest paths resolved correctly;
GitHub Pages used Cache-Control: max-age=600. The original SVG-only touch icon
was unsuitable for Apple's documented PNG configuration. Continued failure
with the valid PNG could not be reproduced without the affected iPhone; stale
installation/page state is a hypothesis, not a proven diagnosis.

Apple configuration reference:
https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html

After deployment:
1. Export existing saved data from Safari AND any installed app. Do not clear data.
2. Open https://fmanzoor3.github.io/coop-atlas/apple-touch-icon-v4.png in Safari;
   confirm the purple/mint controllers appear.
3. Open https://fmanzoor3.github.io/coop-atlas/?icon-check=4 in Safari, then
   Share > Add to Home Screen. Check the preview icon and Coop Database label.
   Keep the old installation until the new one and its backup import are verified.
4. Launch the new icon, verify artwork and import the chosen JSON backup if
   necessary. Compare statuses and added games with the source backup.
5. If the preview still fails, record the iOS version and whether the direct PNG
   displays. An installed shortcut may retain its original icon. Do not erase
   Safari data as a troubleshooting shortcut.

## Next priorities

- Validate imported records before replacing storage; offer a pre-import backup.
  Currently only `data.games` being an array is checked. Malformed records can
  break rendering. Storage write failures also need a visible, recoverable error.
- Verify Steam mappings/platform-specific online support. `Online-like` is now excluded from native-online recommendations;
  exact platform support still needs auditing.
- Reduce screenshot dependency on an unaffiliated public CORS proxy, preferably
  with checked-in verified metadata and screenshot URLs. Preserve fallback links.
- Continue improving the optional shared library without a major frontend rewrite.
  HTML, CSS and JavaScript are separate files.

Validation for this icon change: JavaScript syntax, mobile Chromium smoke test,
167-card rendering, detail dialog, existing storage preservation on load, status
persistence, export/import roundtrip, PNG dimensions/mode and deployed assets.
Actual iOS Home Screen installation still requires the device check above.


## Mobile interface refresh

Browsing now uses Discover, Library and Saved views with compact artwork cards.
A bookmark uses the existing `Good suggestion` verdict; no storage migration is
needed. Played-game verdicts stay intact: those cards offer editing rather than
a bookmark. Play status, verdict, notes, screenshots and assessments are in the
game details. Backup/import, adding games and storage guidance are in the app
menu. Platform/genre/sort controls open in a mobile sheet. Search and categories
stay accessible while scrolling. The default discovery category is online games
not yet played, ordered by fit. All games remain accessible under Discover.

UI validation: mobile Chromium interactions, 320/375/390/430/768/1440px overflow
checks, existing storage left unchanged on load, bookmark/status persistence,
custom-game creation, filtering/sorting, JSON roundtrip, keyboard Escape and
lightbox restoration. Artwork was previewed using downloaded copies of the
actual CDN images; failure fallbacks were checked separately. Physical iPhone
Safari testing remains a device check.


## Shared library

Database setup and access-policy tests are in [supabase/README.md](supabase/README.md).
[setup.html](setup.html) provides copy buttons for the owner-run SQL. The app supports opt-in paired-device syncing, Fred/Manu profiles,
shared progress, a suggestion inbox and individual ratings. Original local saves
remain separate, with an explicit, non-overwriting transfer option.

Personal ratings use 1–10 after applying the owner-run ratings migration in
[setup.html#ratings](setup.html#ratings). Marking a game Played offers an optional
personal rating; shared status is saved independently.

Library opens on All games and orders by recorded personal ratings, using the
average when both profiles have rated. A single rating is labelled with its
profile name. Unrated games follow, with legacy Loved verdicts first. Library
cards show actual ratings rather than predicted fit; Discover retains fit scores.


## Interface polish

`polish.css` supplies the current charcoal/apricot visual theme with lilac/mint profile accents above the base
layout rules. Cards use meaningful score colours and avoid repeating unrated
labels. Ratings sit next to play status in game details. Generic genre-derived
assessments are omitted; individual assessments and all catalogue data remain.
The editor keeps legacy status internally but exposes one play-status/verdict
pair; metadata and device-transfer actions use progressive disclosure. Proposal
actions reflect the other person's response and avoid duplicate suggestions.

`python tests/local-ui.py` and `python tests/shared-ui.py` exercise local editing,
backup roundtrips, filters, shared ratings and suggestion flows, visible feedback,
and widths from 320 to 1440 pixels. Optional images cached in /tmp support visual
QA without making tests depend on external image services. Physical-device
safe-area behaviour should also be checked on an iPhone Home Screen launch.


## Display modes

Discover and Saved default to the artwork grid. Library defaults to compact rows
(two columns on wider desktop screens), retaining the existing all-games and
shared-rating order. The Grid/List controls remember a separate choice per view
on this device under `coopDbViewModesV1`; these presentation preferences never
change game data or cloud settings. The active profile avatar uses lilac for
Fred and mint for Manu. Small-list targets remain 44px wide for touch use.
