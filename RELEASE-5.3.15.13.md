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
