# ruTorrent 5.3.15.8 (0.16.24): autodl stylesheets for the other themes

Released 22 November 2026 for a support ticket: after updating from 3.10, a
customer using the club-QuickBox theme could not scroll autodl-irssi's
Filters window, which ran off the bottom of the screen with a long filter
list.

## Cause

autodl-rutorrent loads `css/<theme>.min.css`, where `<theme>` is the active
ruTorrent theme's directory name in lower case, and ships stylesheets only for
Standard, Acid, Blue, Dark, Excel and Oblivion. The image also offers
club-QuickBox, DarkBetter, MaterialDesign and OblivionBlue. For those the
request returned 404, so the filter list had no height or scrollbar.
ruTorrent 5 positions dialogs absolutely on a page that does not scroll, so
the window grew as tall as the list. club-QuickBox's own `plugins.css` makes
it worse (`#autodl-filters{height:auto}`, `#autodl-filters-left{min-height:max-content}`).
club-QuickBox v2 (2.7.2, the QuickBox project's current skin) keeps the same
rules and has the same fault.

## What changed

The published 5.3.15.7 image (`repo.cylo.net/rutorrent@sha256:db1a64429462205a3bc41833e4886fc4205945b5115a907ae6bf303e087b9df6`)
with an updated `/usr/local/bin/patch-autodl-rutorrent-html5.py`, run once at
build time. The script now writes `club-quickbox.min.css`,
`darkbetter.min.css`, `materialdesign.min.css` and `oblivionblue.min.css` in
`plugins/autodl-rutorrent/css/`:

- DarkBetter and MaterialDesign get autodl's `dark` rules, OblivionBlue its
  `oblivion` rules, and club-QuickBox none (it styles autodl itself);
- all four get a layout that keeps the Filters window on screen: the filter
  list stops at 420px (less on short screens) and scrolls, the filter
  settings scroll inside the window, and OK and Cancel stay at the bottom.

`03-config.sh` already runs the script on every start, so a custom
autodl-rutorrent plugin under `/torrents/config/rutorrent/plugins` and a
custom club-QuickBox (v2 included) under `/torrents/config/rutorrent/themes`
are covered. Each generated file starts with a marker line, and the script
never replaces a stylesheet that lacks it. Nothing else changed: rTorrent,
libtorrent, ruTorrent, the plugins, PHP 8.5.13, nginx and the basic-auth
behaviour are those of 5.3.15.7.

Not changed: with autodl's own stylesheets (Standard, Acid, Blue, Dark,
Excel, Oblivion) the filter list already scrolls, but on ruTorrent 5 the
filter settings overflow the fixed 350px window. Customers on those themes
are unaffected by this release.

## Testing

- Browser test of the trial image with 80 autodl filters, at 1945x1152 and in
  a 1366x700 frame, for club-QuickBox, DarkBetter, MaterialDesign and
  OblivionBlue: the window stays on screen, the list scrolls, New, Remove,
  Copy, OK and Cancel are visible, and selecting the last filter loads it.
  5.3.15.7 with club-QuickBox: the list is about 1,900px tall and the buttons
  are off screen.
- The same layout tested with club-QuickBox v2.7.2 installed as a custom
  theme on 5.3.15.7.

## Build and gate

- Build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.autodl-themes -t repo.cylo.net/rutorrent:5.3.15.8-0.16.24 .`
  on builder.grant.appboxes.co from the exact pushed commit
  `41836ba51baeb0bdc3bd6852c9bf3217484d0d37`.
- Gate: `release/verify-autodl-image.sh repo.cylo.net/rutorrent:5.3.15.8-0.16.24`
  passed in release mode before the push:
  - the 5.3.15.7 layers (31) plus two; entrypoint, healthcheck, environment
    and labels unchanged apart from the base-image label;
  - of 33,246 filesystem entries only the patch script (identical to
    `scripts/`) and the four stylesheets (identical to the script's output on
    the 5.3.15.7 plugin, 0644 nobody:nogroup) differ;
  - the script changes nothing on a second run, keeps a stylesheet it did not
    write, restores one that was deleted and copes with no css directory;
  - fresh install with the catalogue's app 66 environment and install
    fields: nginx -t and php-fpm85 -t, FPM multipart, a torrent added through
    addtorrent.php, public share.php, basic auth on the UI, PHP, addtorrent,
    /RPC2, XML-RPC :8000 and WebDAV :9000; the four stylesheets served with the
    login (401 without) and the dark/oblivion rules present; the same after a
    restart;
  - a custom autodl-rutorrent plugin without the stylesheets gets three on
    start and keeps its own fourth; after removing it and re-creating the
    container the image's stylesheets are back;
  - upgrade from 5.3.15.7 with the same /torrents and /passwd, club-QuickBox
    selected and five extra autodl filters: 5.3.15.7 returns 404 for
    club-quickbox.min.css (control); after the upgrade .rtorrent.rc, the
    session torrents, completed data, theme.dat and autodl.cfg are unchanged,
    the seeded torrent is retained and the stylesheets are served;
  - the registry reported the tag absent before and after the checks.
- Trial runs on the same image inputs (`local/rutorrent-trial:5.3.15.8-t1`)
  fixed three gate faults before the release run, none in the image: the gate
  now waits for ruTorrent's plugin initialisation as `verify-image.sh` does,
  identifies themes by `style.css` (DarkBetter has no init.js), and re-creates
  the container after removing the custom plugin (a restart keeps the
  container's copy).
- The first two pushes stopped at one blob: the registry's B2 backend
  answered 503 on the upload, and the client's retry reached another replica
  that had no record of the upload. The tag stayed absent (MANIFEST_UNKNOWN);
  the third push of the same image succeeded.

## Published

- `repo.cylo.net/rutorrent:5.3.15.8-0.16.24`
- Digest: `sha256:f2d00903ffce4c84bd500d9efc0b968c351695e3ea469be671af170e19c5ec88`
  (OCI index: linux/amd64 `sha256:eee7e554e80bdc18a74dbd6e1b1f2db2901f5341bc7838c6b7c97ae78c5ba8fa` plus attestation)

Catalogue: cylo-api `migrations/20261122_rutorrent_5_3_15_8.sql` (admin-only,
row 1614) applied 2026-11-22 21:26 UTC; canary on the ticket customer's
instance at 21:30 UTC (torrents, theme and filters kept; customer confirmed
the Filters window scrolls); `..._publish.sql` applied 2026-11-23 15:27 UTC,
so 5.3.15.8 is the default (appbox-co/cylo-api#276). No fleet update run.
