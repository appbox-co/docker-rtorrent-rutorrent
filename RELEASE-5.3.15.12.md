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
5.3.15.11. Customers need no action after updating; their files and settings
are not touched.

## Testing

`release/verify-filemanager-image.sh` with `release/filemanager-checks.py`:

- the filesystem: the plugin directory must match `git ls-tree` of v1.6.0
  (types, modes, nobody:nogroup, SHA-256 of every file), 5.3.15.11's must
  match v1.5.1 the same way, and every path outside it must be unchanged;
- `menus none`: no context-menu entry in ruTorrent's JavaScript (outside
  `tests/`) has a string command, and ruTorrent's rule that greys them out is
  still present. The control, `menus filemanager-1.5.1`, must find exactly
  1.5.1's seven on 5.3.15.11;
- `api`: create, rename (to a name with a space and quotes) and list a folder
  through `plugins/filemanager/action.php`, encoded as v1.6.0's JavaScript
  sends it;
- the 5.3.15.11 runtime, login and autodl send checks, on a fresh install,
  after a restart and after an upgrade from 5.3.15.11 on the same volumes.
