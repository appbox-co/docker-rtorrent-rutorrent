# ruTorrent 5.3.15.10 (0.16.24): club-QuickBox v2

Adds club-QuickBox v2 as a theme. The original club-QuickBox stays as it is.

## Why

A customer on support ticket #816797 asked about club-QuickBox v2, the
QuickBox project's current ruTorrent skin, and later chose to keep the
original. It is bundled anyway, so any customer can pick it from the theme
list instead of installing it as a custom theme.

## What changed

The published 5.3.15.9 image
(`repo.cylo.net/rutorrent@sha256:b4b93012e2a789d38e1da2a6a446d53f1220d2f676d44853bbce7864f67256df`)
plus:

- `/var/www/rutorrent/plugins/theme/themes/club-QuickBox-v2`: club-QuickBox
  v2.7.2 from https://github.com/QuickBox/club-QuickBox (branch `latest`,
  commit `e24bfbd38cf7710f3bd38e97d06e6099c07a1c1f`, public domain; Material
  Design Icons glyphs under Apache 2.0), without `bin/`, `docs/` and
  `.github/`. Owner nobody:nogroup, directories 755, files 644.
  - Upstream installs v2 as `club-QuickBox`, the directory the original
    already uses, so the bundled copy is `club-QuickBox-v2`. Customers who
    selected club-QuickBox keep the original.
  - `init.js` finds its own `style.css`, `stable.css` and `plugins.css` by
    path; the path now names `club-QuickBox-v2`. Without this edit,
    `plugins.css` would load twice and changed sheets would keep their
    cached URLs.
  - `js/about.js` no longer asks GitHub once a day for a newer release. The
    theme updates with the image, so an "Update available" note with `git`
    steps would not apply. The QuickBox dashboard update path needs
    QuickBox's `qb_theme` cookie and never runs on Appbox.
- `patch-autodl-rutorrent-html5.py` also generates autodl's
  `club-quickbox-v2.min.css`: the 5.3.15.8 Filters layout only, as for the
  original club-QuickBox, whose plugin stylesheet colours autodl itself.

Nothing else changed: rTorrent, libtorrent, ruTorrent, the plugins, PHP
8.5.13, nginx, the basic-auth behaviour and the other themes are those of
5.3.15.9.

A customer who installed v2 as a custom theme under
`/torrents/config/rutorrent/themes/club-QuickBox` keeps it: `03-config.sh`
copies custom themes over the image's on every start.

## Testing

Browser test of the trial image (`local/rutorrent-trial:5.3.15.10-t1`, built
from e45b273) with club-QuickBox-v2 selected and 80 autodl filters, at
1024x768 and 1366x700:

- The theme list offers club-QuickBox and club-QuickBox-v2, and v2 loads all
  its stylesheets with its own version key. `plugins.css` loads once, and
  there are no console errors.
- autodl loads `club-quickbox-v2.min.css`. The Filters window is absolutely
  positioned and on screen, and the page does not scroll. The filter list
  stops at 420px and scrolls. New, Remove, Copy, OK and Cancel are inside
  the window. At 700px high the filter settings scroll inside the window.
- Help shows club-QuickBox v2.7.2. What's new lists the bundled changelogs,
  read from the theme directory, with no "Update available" note. Nothing
  is requested from GitHub.

## Build and gate

Trial build on builder.grant from e45b273:
`release/verify-quickbox-v2-image.sh local/rutorrent-trial:5.3.15.10-t1`
passed. It checks:

- the 5.3.15.9 layers plus three, with the image config and labels unchanged
  apart from the base-image label;
- that of 33,576 filesystem entries only the patch script, the 167 entries
  of `club-QuickBox-v2` (identical to the repository, nobody:nogroup,
  755/644) and `club-quickbox-v2.min.css` (the script's output) differ, so
  the original club-QuickBox and autodl's other stylesheets are unchanged;
- the patch script's idempotency, foreign-file, deleted-file and
  repair checks;
- the runtime and basic-auth checks on a fresh install and after a restart,
  with every autodl stylesheet and the v2 theme files served with the login
  and refused without it;
- that a custom autodl plugin without the generated stylesheets gets all
  four, `club-quickbox-v2` included, on start;
- an upgrade from 5.3.15.9 with the original club-QuickBox selected.
  5.3.15.9 serves club-QuickBox but has no club-QuickBox-v2 (the control).
  After the upgrade, torrents, theme selection and autodl.cfg are kept, and
  v2 is served;
- that the registry reports the tag absent.

Release build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.quickbox-v2 -t repo.cylo.net/rutorrent:5.3.15.10-0.16.24 .`
on builder.grant from the exact pushed commit
`7961e0620d817d01f993399489790d3db8ce324a`. `release/verify-quickbox-v2-image.sh`
passed in release mode with the results above, the registry reported the tag
absent before and after the checks, and the first push succeeded.

## Published

- `repo.cylo.net/rutorrent:5.3.15.10-0.16.24`
- Digest: `sha256:8ab0ef99acd54013efe2ea0b5c277d94020f8e7842eb38814b746122683981b7`
  (OCI index: linux/amd64 `sha256:9186ddc8aebe5905b8f36459628cbae55322711f5a3f547296c5b724e4dee039` plus attestation)

Catalogue: cylo-api `migrations/20261124_rutorrent_5_3_15_10.sql` (admin-only,
not default) and `..._publish.sql`.
