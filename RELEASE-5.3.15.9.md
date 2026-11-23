# ruTorrent 5.3.15.9 (0.16.24): Filters layout for autodl's own themes

Follow-up to 5.3.15.8 (support ticket #816797).

## Cause

5.3.15.8 gave club-QuickBox, DarkBetter, MaterialDesign and OblivionBlue a
Filters layout. The six themes autodl-rutorrent ships its own stylesheets
for (Standard, Acid, Blue, Dark, Excel, Oblivion) kept autodl's
`#autodl-filters{width:600px;height:350px}`. On ruTorrent 5 the filter list
scrolls inside that window, but the filter settings do not fit: Delay, Max,
"downloads per" and "Download duplicate releases" spill out below the
window, and the size fields overlap OK and Cancel.

Blue had a second fault, present in 5.3.15.8 as well. Its stylesheet sets
`#autodl-filters,#autodl-trackers,#autodl-servers,#autodl-prefs` and
`#autodl-multiselect` to `position:relative;left:0`. The rule also matches
the dialog windows with those ids and beats ruTorrent's
`.dlg-window{position:absolute}`, so autodl's dialogs sat below the page and
the browser scrolled the whole page to reach them.

## What changed

The published 5.3.15.8 image
(`repo.cylo.net/rutorrent@sha256:f2d00903ffce4c84bd500d9efc0b968c351695e3ea469be671af170e19c5ec88`)
with an updated `/usr/local/bin/patch-autodl-rutorrent-html5.py`, run once at
build time. The script appends a block to autodl's six stylesheets between
two marker comments, and replaces the block on every run. The block holds
the 5.3.15.8 Filters layout plus one rule that puts autodl's dialog windows
back to `position:absolute`. Each file keeps autodl's own rules ahead of the
block, with its mode and owner unchanged. The four generated stylesheets
copy the bundled colours without the block, so they are byte-identical to
5.3.15.8's. `03-config.sh` already runs the script on every start, so a
custom autodl-rutorrent plugin gets the block too.

Nothing else changed: rTorrent, libtorrent, ruTorrent, the plugins, PHP
8.5.13, nginx and the basic-auth behaviour are those of 5.3.15.8.

## Browsers keep the old stylesheet for a while

These stylesheets are served without Cache-Control or Expires, and
ruTorrent requests them as `css/<theme>.min.css?v=5315` in every image
version. A browser that loaded the old file can keep using its cached copy
for days. In testing, Oblivion looked unchanged until the cached copy was
refreshed. Customers should reload ruTorrent with Ctrl+Shift+R (Cmd+Shift+R
on a Mac) after updating, as the app's update text already says. 5.3.15.8 did
not hit this for the four new stylesheets, because those URLs had returned
404 before.

## Testing

- Browser test of the trial image with 80 autodl filters, at 1945x1263 and
  in a 1366x700 frame, for Standard, Acid, Blue, Dark, Excel and Oblivion:
  - the window is absolutely positioned, the page does not scroll, and the
    whole window is on screen;
  - the filter list stops at 420px and scrolls;
  - every settings field is inside the window, none overlaps OK;
  - New, Remove, Copy, OK and Cancel are inside the window;
  - selecting the last filter loads it (Standard at 1366x700).
  Blue's Trackers dialog is also absolutely positioned and on screen.
  5.3.15.8 with Oblivion: five fields below a 350px window, two overlapping
  OK.

## Build and gate

Trial runs on builder.grant (`local/rutorrent-trial:5.3.15.9-t1`, then `-t2`
with the Blue rule): `release/verify-autodl-image.sh` passed. It checks:

- the 5.3.15.8 layers plus two, with the image config and labels unchanged
  apart from the base-image label;
- that of 33,246 filesystem entries only the patch script and the six
  bundled stylesheets differ, and that the four generated stylesheets are
  unchanged;
- that the script changes nothing on a second run, keeps a foreign
  stylesheet, restores a deleted one and repairs an edited or truncated
  block;
- the runtime and basic-auth checks on a fresh install and after a restart,
  with all ten autodl stylesheets served;
- that a custom autodl plugin without the block gets it on start;
- an upgrade from 5.3.15.8 with Oblivion selected: 5.3.15.8 serves the
  fixed-height oblivion.min.css (the control), and after the upgrade
  torrents, theme and autodl.cfg are kept;
- that the registry reports the tag absent.

Release build and push: not done yet.
