# ruTorrent 5.3.15.13 (0.16.24): File Manager 1.6.0 that browsers actually load

## Cause

5.3.15.12 replaced File Manager 1.5.1 with 1.6.0, which fixes the greyed-out
right-click menu of ticket #785930 (see RELEASE-5.3.15.12.md). Its canary on
grant showed that browsers keep running 1.5.1 after the update:

- File Manager's init.js (delivered inside ruTorrent's `php/getplugins.php`)
  loads `js/app.js` with `import()`, and app.js, ui.js and file-archive.js
  import the other modules by relative URL. The URLs are the same in every
  version.
- Neither the image's nginx nor the Appbox proxy sends Cache-Control or
  Expires for them, only Last-Modified and an ETag, so Chrome caches them for
  10% of their age: several days for 1.5.1's files, dated 13 Oct.
- A normal reload used the cached modules. So did a hard reload
  (Cmd+Shift+R): it re-downloaded ruTorrent's own scripts, but not the
  modules File Manager loads later with `import()`.

A customer who had used File Manager recently would have seen no change after
updating to 5.3.15.12.

## What changed

The 5.3.15.12 image
(`repo.cylo.net/rutorrent@sha256:8fd8aa1036a6115205e74e28349a6fa2df08126ae9f1de8fb72b2b9f647fd47f`)
plus `scripts/patch-filemanager-module-urls.py`, run on the plugin directory.
It appends `?v=<token>` to all ten module imports: the `js/app.js` import in
`init.js`, six in `js/app.js`, two in `js/ui.js` and one in
`js/file-archive.js`. The token is the first 12 hex digits of a SHA-256 over
the plugin's `js/*.js` files before patching (`e25127a6c9e3` for 1.6.0), so it
changes whenever a module changes. Every module still has exactly one URL.
`twig.min.js`, a third-party library, keeps its URL.

`php/getplugins.php` answers with an ETag and no Last-Modified, so browsers
revalidate it on every load and get the new init.js at once; from there every
module URL is new, and the first normal reload after the update runs 1.6.0.

The script is in `/usr/local/bin` (root:root 644), and the full `Dockerfile`
runs it right after cloning File Manager. It accepts only File Manager 1.6.0's
ten imports and refuses a tree it has already patched, so a File Manager
update has to look at it again.

Nothing else changed: the four patched files keep their owner and mode, and
rTorrent, ruTorrent, the other plugins, PHP 8.5.13, nginx, autodl and the
basic-auth behaviour are those of 5.3.15.12.

## Testing

`release/verify-filemanager-module-urls-image.sh`, with
`release/filemanager-checks.py`:

- the filesystem: 5.3.15.12's File Manager must be exactly upstream v1.6.0,
  and the image must be 5.3.15.12 with the checksums of the four patched files
  changed to what the script makes of upstream v1.6.0 (computed by the gate
  from a fresh `git archive`), plus the script. Nothing else may differ;
- `modules TOKEN`: all ten imports carry the gate's token, every versioned
  URL is served through nginx with the file's bytes, and `php/getplugins.php`
  hands browsers the versioned `js/app.js` import. The control,
  `modules unversioned`, must find no token on 5.3.15.12;
- `menus none` and `api` as in 5.3.15.12, and the runtime, login and autodl
  checks, on a fresh install, after a restart and after an upgrade from
  5.3.15.12 on the same volumes.

## Build and gate

Trial runs on builder.grant from a `git archive` of a pushed commit:
`docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.filemanager-module-urls`,
then `release/verify-filemanager-module-urls-image.sh` in trial mode.

- `cdc2bd5` failed only on the script's mode: `git archive` writes files 664,
  so the plain COPY installed it 664. Both Dockerfiles now use
  `COPY --chmod=644` (`4f4a4ae`).
- `4f4a4ae` (`local/rutorrent-trial:5.3.15.13-524983`) passed:
  - 5.3.15.12's 40 layers plus two, with labels, entrypoint, healthcheck and
    environment unchanged;
  - 33,580 filesystem entries, identical to 5.3.15.12 except `init.js`,
    `js/app.js`, `js/ui.js` and `js/file-archive.js` (what the script makes of
    upstream v1.6.0, token `e25127a6c9e3`) and the script itself;
  - fresh install, restart and upgrade from 5.3.15.12: all ten imports carry
    the token, every versioned URL is served with the file's bytes, and
    `php/getplugins.php` hands out the versioned `app.js` import. The control
    found none versioned on 5.3.15.12. Menus, the File Manager API, logins,
    uploads and autodl all passed, and the upgrade kept the session, data,
    theme and autodl.cfg;
  - the registry reported the tag absent before and after.

## Browser test

The update path the 5.3.15.12 canary failed, on the builder, through an nginx
that adds a test login and an SSH tunnel:

1. A 5.3.15.11 container. File Manager 1.5.1's modules were downloaded, and
   a normal reload then served them from the cache (transfer size 0), as on
   grant.
2. The container replaced by the `4f4a4ae` trial image on the same volumes.
3. One normal reload: `app.js`, `ui.js`, `api.js`, `actions.js`, `utils.js`,
   `ui-fs.js`, `ui-dialogs.js`, `file-archive.js` and `file-checksum.js` were
   all downloaded at `?v=e25127a6c9e3`, each once; only `twig.min.js` kept
   its URL. The 1.5.1 encoder was gone.
4. The File Manager menu had every entry enabled. Copy (task console "Done")
   and Delete worked, and the results were on disk. No context-menu warning
   in the console.

## Review

Claude Opus 5.5 found nothing to change. It ran the script on upstream
v1.6.0, the gate's token and quoting under dash, and checked that no other
code loads File Manager's modules by the old URLs. Claude Sonnet 5.5 found it
ready, with four small points:

- The script counted only the import forms it rewrites, so a later File
  Manager with a bare `import "./x.js"` or a `../` path could keep an
  unversioned module. Fixed: it now also fails if any relative `.js`
  reference in `js/*.js` would be left without a token. Its output for
  v1.6.0 is unchanged (`e25127a6c9e3`, the same four files), and a test tree
  with an added bare import fails before anything is written.
- `get()` and `call()` in `filemanager-checks.py` built the login header
  twice. Fixed with a `login()` helper.
- The catalogue notes say new folders can't be made at File Manager's top
  level. Left in: it is true (canary of 5.3.15.12), and it answers what a
  customer trying New Directory there would see, now that the entry works.
- The full `Dockerfile` path isn't gated. Left as in 5.3.15.12: releases are
  built from the overlays.

## Release

Release build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.filemanager-module-urls -t repo.cylo.net/rutorrent:5.3.15.13-0.16.24 .`
on builder.grant from the exact pushed commit
`de79c5a4d2361ae4db28cde490de305df6db6d94`.
`release/verify-filemanager-module-urls-image.sh` passed in release mode with
the trial's results: 5.3.15.12's 40 layers plus two, the image identical to
5.3.15.12 except the four patched files (token `e25127a6c9e3`) and the
script, all ten imports versioned and served on a fresh install, after a
restart and after an upgrade (none on 5.3.15.12), and the menus, File Manager
API, logins, uploads and autodl working. The registry reported the tag absent
before and after the checks, and the first push succeeded.

## Published

- `repo.cylo.net/rutorrent:5.3.15.13-0.16.24`
- Digest: `sha256:7fac83a0da35de7a1380c385d9c862daaca3790e3ed4dfbd8609054cf8d67d92`
  (OCI index: linux/amd64 `sha256:0d644180032d39a0d33f793aa28e5881b232096866b94e7b7aa7bd9cff451101` plus attestation)

Catalogue: cylo-api `migrations/20261126_rutorrent_5_3_15_13.sql` (admin-only,
not default) and `..._publish.sql`, in place of 5.3.15.12's publish migration.


## Canary

2026-11-26 on grant, instance 267021 (`rutorrent.grant.appboxes.co`), Chrome
through the Appbox proxy, following a customer's path from 5.3.15.11:

1. Instance on 5.3.15.11 (via its page's Update button). File Manager 1.5.1's
   modules downloaded, and a normal reload then served all of them from
   the browser cache (transfer size 0), with the 1.5.1 encoder loaded.
2. Switched to 5.3.15.13 from the instance page (about 4 minutes).
3. One normal reload: `php/getplugins.php` came back new (393 KB), and every
   File Manager module was downloaded at `?v=e25127a6c9e3`. The 1.5.1 encoder
   was gone.
4. File Manager menu in `/completed`: New Directory and Refresh enabled.
   New Directory created "Canary 13", which was then shown with Copy, Move,
   Delete and Rename enabled. Delete removed it through the task console. No
   console errors.

On 5.3.15.12 the same steps left the menu greyed out until the cached
modules were forced fresh.
