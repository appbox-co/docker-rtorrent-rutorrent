#!/usr/bin/env python3
"""Give File Manager's JavaScript modules versioned URLs.

Usage: patch-filemanager-module-urls.py <plugin dir>
       (/var/www/rutorrent/plugins/filemanager in the image)

File Manager loads js/app.js with import() from init.js, and app.js, ui.js and
file-archive.js import the rest by relative URL. Neither the image's nginx nor
the Appbox proxy sends Cache-Control for them, so after an image update a
browser keeps running the cached modules for days: Chrome keeps them for 10%
of their age, and a hard reload does not bypass the cache for modules loaded
later by import(). After 5.3.15.12 replaced File Manager 1.5.1 with 1.6.0, the
grant canary kept running 1.5.1 after both a normal and a hard reload.

This appends ?v=<token> to every one of those module URLs. The token is
derived from the content of the plugin's js/*.js files before patching, so it
changes whenever any module changes and a browser fetches the new modules on
the next normal reload. Every module gets exactly one URL, so none is loaded
twice. init.js reaches the browser through ruTorrent's php/getplugins.php,
which has an ETag but no Last-Modified, so browsers revalidate it every time.

The script expects File Manager 1.6.0's ten imports exactly and fails on
anything else, including a tree it has already patched.
"""
import hashlib
import pathlib
import re
import sys

# The module imports of File Manager 1.6.0, per file.
EXPECTED = {
    "init.js": 1,
    "js/app.js": 6,
    "js/ui.js": 2,
    "js/file-archive.js": 1,
}
# from "./x.js" / import("./x.js") inside js/, and import('./' + plugin.path
# + 'js/app.js') in init.js. twig.min.js is a third-party library that does
# not change between File Manager versions and is left alone.
RELATIVE = re.compile(r"""((?:\bfrom\s+|\bimport\s*\(\s*)(["']))\./([A-Za-z0-9_.-]+\.js)\2""")
INIT_APP = "'js/app.js'"


def fail(message):
    sys.exit("patch-filemanager-module-urls: " + message)


if len(sys.argv) != 2:
    fail("usage: patch-filemanager-module-urls.py <plugin dir>")
root = pathlib.Path(sys.argv[1])
modules = sorted((root / "js").glob("*.js"))
if not modules:
    fail("no js/*.js under %s" % root)
for path in [root / "init.js"] + modules:
    if ".js?v=" in path.read_text(encoding="utf-8"):
        fail("%s already has versioned module URLs" % path)

digest = hashlib.sha256()
for path in modules:
    digest.update(path.relative_to(root).as_posix().encode() + b"\0")
    digest.update(path.read_bytes() + b"\0")
token = digest.hexdigest()[:12]

counts = {}
init = root / "init.js"
text = init.read_text(encoding="utf-8")
counts["init.js"] = text.count(INIT_APP)
init_patched = text.replace(INIT_APP, "'js/app.js?v=%s'" % token)

patched = {}
for path in modules:
    text = path.read_text(encoding="utf-8")
    new, n = RELATIVE.subn(lambda m: "%s./%s?v=%s%s" % (m.group(1), m.group(3), token, m.group(2)), text)
    if n:
        counts[path.relative_to(root).as_posix()] = n
        patched[path] = new

if counts != EXPECTED:
    fail("unexpected module imports %s; expected %s" % (counts, EXPECTED))

init.write_text(init_patched, encoding="utf-8")
for path, new in patched.items():
    path.write_text(new, encoding="utf-8")
print("File Manager module URLs versioned with ?v=%s (%d imports)" % (token, sum(counts.values())))
