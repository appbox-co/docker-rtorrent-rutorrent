# ruTorrent 5.3.15.12 (0.16.24): File Manager 1.6.0

## Cause

Support ticket #785930: on ruTorrent 5.3.15.11 the File Manager tab's
right-click menu had New Directory, Copy, Move, Delete and Rename greyed out.
Open and Create > New Archive still worked.

ruTorrent 5 changed `theContextMenu.setCommand` (Novik/ruTorrent#3316, in the
pinned ruTorrent `fe46836` that every 5.3.15.x image uses). A menu entry whose
command is a string is now shown disabled, and the browser console logs
"Context menu command must be a function, not a string". File Manager 1.5.1
(`js/ui-fs.js`) gives seven commands as strings: New Directory (twice), Copy,
Move, Delete, Rename and Refresh. Open and New Archive are functions, which is
why they kept working. The fault has been in every 5.3.15.x release since
5.3.15.1. No other plugin in the image has a string menu command; ruTorrent's
own `tests/` contain some on purpose.

"Share..." is greyed out for folders on every version: filemanager-share only
shares files.

## What changed

The published 5.3.15.11 image
(`repo.cylo.net/rutorrent@sha256:3fc67478bd5f9a476adfc2ccc8f976618852e061682d16c0bb042eb564259137`)
with `/var/www/rutorrent/plugins/filemanager` replaced by upstream File Manager
v1.6.0 (`501aa6378350699f36ec5c6b9f373475e6420c7d`, 2026-10-20), cloned with
`.git*` removed as the full `Dockerfile` clones it, owned by nobody:nogroup.
The full `Dockerfile` now clones `v1.6.0` too.

v1.6.0 has the same file list as v1.5.1. Its changes:

- `js/ui-fs.js`: the seven menu commands are arrow functions (upstream #88).
- `js/api.js`: requests are encoded with `JSON.stringify` instead of the
  plugin's own `json_encode`, which `js/utils.js` no longer has.
  filemanager-share 1.5.0 and filemanager-media 1.4.0 do not call it.
- `plugin.info` (1.6.0) and upstream's own `Dockerfile`.

The PHP side is unchanged. rTorrent, libtorrent, ruTorrent, the other plugins,
themes, PHP 8.5.13, nginx, autodl and the basic-auth behaviour are those of
5.3.15.11. Files and settings are not touched.

Browsers may keep the 1.5.1 scripts after the update. File Manager loads
`js/app.js` (and through it `ui-fs.js`, `api.js` and `utils.js`) with a
dynamic `import()` that has no version query, and nginx sends no
Cache-Control, so a browser that used File Manager in the last few days can
serve them from its cache on a normal reload: the entries stay greyed out,
and a mix of the old `api.js` with the new `utils.js` would break every File
Manager request. A hard reload (Ctrl+Shift+R, Cmd+Shift+R on a Mac) fetches
the new files. The release notes and the ticket reply say so, and the canary
updates a 5.3.15.11 instance that has used File Manager.

## Testing

`release/verify-filemanager-image.sh` with `release/filemanager-checks.py`:

- the filesystem: the plugin directory must match `git ls-tree` of v1.6.0
  (types, modes, nobody:nogroup, SHA-256 of every file), 5.3.15.11's must
  match v1.5.1 the same way, and every path outside it must be unchanged;
- `menus none`: no context-menu entry in ruTorrent's JavaScript (outside
  `tests/`) has a string command containing a call, ruTorrent's rule that
  greys them out is still present, and no plugin still calls
  `flm.utils.json_encode`. The pattern is a regression tripwire; the browser
  test checks the menu itself. The control, `menus filemanager-1.5.1`, must
  find 1.5.1's seven, all in `js/ui-fs.js`, on 5.3.15.11;
- `api`: create, rename (to a name with a space and quotes) and list a folder
  in `/torrents/completed` through `plugins/filemanager/action.php`, encoded
  as v1.6.0's JavaScript sends it. File Manager runs its commands through
  rTorrent, as rtorrent; a fresh gate volume leaves `/torrents` itself owned
  by root, so the first trial's attempt there failed the same way on
  5.3.15.11;
- the 5.3.15.11 runtime, login and autodl send checks, on a fresh install,
  after a restart and after an upgrade from 5.3.15.11 on the same volumes.

## Build and gate

Trial runs on builder.grant, each from a `git archive` of a pushed commit:
`docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.filemanager-1.6.0`,
then `release/verify-filemanager-image.sh` in trial mode.

- `b5583b9` failed at the API step: `/torrents` in a fresh gate volume is
  root:root 755, so rTorrent (as rtorrent) could not create a folder there.
  The same call failed the same way on a 5.3.15.11 container, so the check
  moved to `/torrents/completed` (`a6111bb`).
- `a6111bb` (`local/rutorrent-trial:5.3.15.12-2df764`) passed:
  - 5.3.15.11's 39 layers plus one, with labels, entrypoint, healthcheck and
    environment unchanged;
  - of 33,578 filesystem entries, everything outside the plugin directory is
    identical to 5.3.15.11; 5.3.15.11's File Manager is exactly v1.5.1 and the
    image's exactly v1.6.0 (180 lines), with `js/ui-fs.js`, `js/api.js`,
    `js/utils.js`, `plugin.info` and `Dockerfile` changed;
  - fresh install and restart: runtime, login and autodl send checks, no
    string menu commands, and the File Manager API created, renamed and
    listed a folder as rtorrent (1000:1000);
  - upgrade from 5.3.15.11 on the same volumes: the control found 1.5.1's
    seven string commands; afterwards `.rtorrent.rc`, the session torrents,
    completed data, theme.dat and autodl.cfg were unchanged, and all checks
    passed;
  - the registry reported `repo.cylo.net/rutorrent:5.3.15.12-0.16.24` absent
    (MANIFEST_UNKNOWN) before and after.

## Browser test

The `a6111bb` trial image behind an nginx that adds a test login, opened over
an SSH tunnel, File Manager tab, `/completed` with two folders and two files:

- the right-click menu's Open, Copy, Move, Delete, Rename and Refresh were all
  enabled (`menu-cmd`, none `dis`), and Create offered New Directory, New
  Archive and, for a file, Share;
- Rename to `Show "S01" it's`, New Directory, Copy of a file into another
  folder, Move of a file, Delete of a folder (each task console "Done") and
  Refresh all worked, and the results were on disk, owned by rtorrent;
- no "Context menu command must be a function" warning in the console. The
  only console errors were 404s for optional theme files and core images
  (`plugins/theme/themes/appbox/*.css`, `css/images/*.png`), none from File
  Manager.

## Review

Two reviewers who did not write the change, Claude Opus 5.5 and Claude
Sonnet 5.5, both found it ready to roll out as admin-only with a canary.

- Opus: browsers can keep the 1.5.1 scripts after the update (see "What
  changed"). Fixed in the notes, the catalogue release notes and the canary
  plan; nginx is not changed in this release.
- Both: `flm_expected` ended in `} | sort`, so its error paths could never
  fire. It now writes `git ls-tree` to a file, fails on an unexpected entry,
  and the tag checks use `$TAB` instead of a literal tab. Its output is the
  same 180 lines.
- Opus: the control's command list did not prove "seven only"; it is now the
  file set and a count of seven. Sonnet: the scan only finds string commands
  that contain a call; the wording now says it is a tripwire.
- Sonnet: nothing checked that no other plugin calls the removed
  `flm.utils.json_encode`; `menus none` now fails if one does.
- Sonnet: the autodl send check is redundant for this change. Left in: it
  costs about 45 seconds and keeps 5.3.15.11's fix checked end to end on the
  image that ships it.

Opus checked the fixes again (`bbaa2fb`) and found nothing; it ran the old and
new `flm_expected` under dash on a test repository and got the same output.

## Release

Release build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.filemanager-1.6.0 -t repo.cylo.net/rutorrent:5.3.15.12-0.16.24 .`
on builder.grant from the exact pushed commit
`bbaa2fb234e1b330fee9189623d510d00a01221f`.
`release/verify-filemanager-image.sh` passed in release mode with the same
results as the trial: 5.3.15.11's 39 layers plus one, only the plugin
directory changed and equal to v1.6.0, no string menu commands (the control
found 1.5.1's seven on 5.3.15.11), and the File Manager API, logins, uploads
and autodl working on a fresh install, after a restart and after an upgrade.
The registry reported the tag absent before and after the checks, and the
first push succeeded.

## Published

- `repo.cylo.net/rutorrent:5.3.15.12-0.16.24`
- Digest: `sha256:8fd8aa1036a6115205e74e28349a6fa2df08126ae9f1de8fb72b2b9f647fd47f`
  (OCI index: linux/amd64 `sha256:fabc93ac557829f9eccb93d48c172608e8147a4862d849b394a59a34fe3f1292` plus attestation)

Catalogue: cylo-api `migrations/20261126_rutorrent_5_3_15_12.sql` (admin-only,
not default) and `..._publish.sql`.


## Canary

2026-11-26 on grant, instance 267021 (`rutorrent.grant.appboxes.co`), in a
Chrome that had used ruTorrent on that domain before:

- Installed 5.3.15.11. File Manager's Copy, Move, Delete, Rename and
  Refresh were greyed out (`dis`): the ticket's fault, reproduced.
- Through the Appbox proxy, `plugins/filemanager/js/*.js` are served with no
  Cache-Control or Expires header, only Last-Modified (13 Oct for 1.5.1) and
  an ETag.
- Switched the instance to 5.3.15.12 from its page (about 4 minutes, the
  dialog already advises a hard refresh). After a normal reload the menu was
  still greyed out: File Manager's modules all came from the browser cache
  (transfer size 0) and the 1.5.1 encoder was still loaded.
- **A hard reload (Cmd+Shift+R) did not help.** It re-downloaded ruTorrent's
  own scripts, but File Manager's modules are loaded later by `import()`,
  which a hard reload does not bypass, so they came from the cache again.
  Chrome keeps them for 10% of their age at the time they were cached, so a
  few days for files dated 13 Oct.
- After refreshing those cache entries with `fetch(..., {cache: 'reload'})`
  and a normal reload, 1.6.0 was running: every entry was enabled, Rename
  and Delete worked through the menu in `/completed`, and New Directory
  worked there through the API.
- New Directory at File Manager's top level (`/`, which is `/torrents`)
  failed with "Error Processing Request" on 5.3.15.12, and the UI showed no
  error. `/torrents` is not writable by rtorrent on Appbox either. This was
  already so on 5.3.15.11 (the entry was greyed out there) and is not caused
  by this release.

5.3.15.12 stays admin-only and is not published. 5.3.15.13 (RELEASE-5.3.15.13.md)
versions File Manager's module URLs so browsers load 1.6.0 after the update.

