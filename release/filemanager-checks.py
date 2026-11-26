"""File Manager checks run inside a started, healthy ruTorrent container.

The release gate pipes this file to `docker exec -i <container> python3 - MODE`.

  menus EXPECT   scan ruTorrent's JavaScript for context-menu entries whose
                 command is a string of code such as "flm.goToPath(...)",
                 which ruTorrent 5 greys out (Novik/ruTorrent#3316). The
                 pattern needs a "(" in the string, so it is a regression
                 tripwire, not a proof; the browser test checks the menu.
                 EXPECT is "none" (which also fails if another plugin still
                 calls flm.utils.json_encode, removed in File Manager 1.6.0),
                 or "filemanager-1.5.1" for the control: File Manager 1.5.1's
                 seven string commands in plugins/filemanager/js/ui-fs.js.
  modules EXPECT File Manager's module imports (init.js and js/*.js). EXPECT is
                 the ?v= token scripts/patch-filemanager-module-urls.py gave
                 them: all ten imports must carry it, every versioned URL
                 must be served with the file's bytes, and ruTorrent's
                 php/getplugins.php must hand browsers the versioned import.
                 "unversioned" is the control: no import carries a token.
  api            create, rename and list a folder in /torrents/completed
                 through File Manager's own endpoint, with the request encoded
                 as File Manager 1.6.0's JavaScript encodes it
                 (JSON.stringify), then remove it. File Manager's root is
                 /torrents, which a fresh gate volume leaves owned by root;
                 rTorrent runs File Manager's commands as rtorrent, so the
                 check works in completed/, which the image creates for it.

ruTorrent's own JavaScript tests (tests/) contain string commands on purpose
and are not scanned. The container's USERNAME and PASSWORD environment set
the basic-auth login. The last line printed is a JSON summary.
"""
import base64
import json
import os
import re
import secrets
import shutil
import sys
import urllib.parse
import urllib.request

ROOT = "/var/www/rutorrent"
TOP = "/torrents"
WORK = "completed"
CORE_RULE = "must be a function, not a string"
# [label, "command("...] or [CMENU_SEL, label, "command("...], optionally
# with a (condition) ? null : "command(" ternary, as File Manager 1.5.1 has.
STRING_COMMAND = re.compile(
    r"""\[\s*(?:theUILang\.[A-Za-z_]+|CMENU_SEL\s*,\s*[^,\]]+|"[^"\n]*"|'[^'\n]*')\s*,\s*"""
    r"""(?:\([^)]*\)\s*\?\s*[^:]+:\s*)?(?:"[^"\n]*\(|'[^'\n]*\()"""
)


def fail(message):
    print("FAIL: " + message, file=sys.stderr)
    sys.exit(1)


def scan():
    hits = []
    encoder_calls = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        if dirpath == ROOT:
            dirnames[:] = [d for d in dirnames if d != "tests"]
        for name in filenames:
            if not name.endswith(".js") or name.endswith(".min.js"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as handle:
                for number, line in enumerate(handle, 1):
                    stripped = line.strip()
                    if stripped.startswith(("//", "/*", "*")):
                        continue
                    if STRING_COMMAND.search(line):
                        hits.append((os.path.relpath(path, ROOT), number, stripped))
                    if "flm.utils.json_encode" in line:
                        encoder_calls.append("%s:%d" % (os.path.relpath(path, ROOT), number))
    return hits, encoder_calls


def menus(expect):
    with open(os.path.join(ROOT, "js/objects.js"), encoding="utf-8") as handle:
        if CORE_RULE not in handle.read():
            fail("ruTorrent's js/objects.js no longer greys out string menu commands; the check is out of date")
    with open(os.path.join(ROOT, "plugins/filemanager/plugin.info"), encoding="utf-8") as handle:
        version = re.search(r"^plugin\.version:\s*(\S+)", handle.read(), re.M).group(1)
    hits, encoder_calls = scan()
    for path, number, line in hits:
        print("string menu command: %s:%d %s" % (path, number, line[:160]))
    if expect == "none":
        if version != "1.6.0":
            fail("File Manager is %s, not 1.6.0" % version)
        if hits:
            fail("%d context-menu entries still have string commands" % len(hits))
        if encoder_calls:
            fail("flm.utils.json_encode, removed in File Manager 1.6.0, is still called: %s" % encoder_calls)
    elif expect == "filemanager-1.5.1":
        if version != "1.5.1":
            fail("control: File Manager is %s, not 1.5.1" % version)
        files = {path for path, _, _ in hits}
        if files != {"plugins/filemanager/js/ui-fs.js"} or len(hits) != 7:
            fail("control: expected File Manager 1.5.1's seven string commands only, found %d in %s"
                 % (len(hits), sorted(files)))
    else:
        fail("unknown expectation: " + expect)
    print(json.dumps({"filemanager": version, "string_menu_commands": len(hits)}))


IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*)["']\./([A-Za-z0-9_.-]+\.js)(?:\?v=([0-9a-f]+))?["']""")


def login():
    return "Basic " + base64.b64encode((os.environ["USERNAME"] + ":" + os.environ["PASSWORD"]).encode()).decode()


def get(path):
    request = urllib.request.Request("http://127.0.0.1" + path, headers={"Authorization": login()})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, response.read()


def modules(expect):
    flm = os.path.join(ROOT, "plugins/filemanager")
    with open(os.path.join(flm, "init.js"), encoding="utf-8") as handle:
        init = handle.read()
    app_versions = re.findall(r"'js/app\.js(?:\?v=([0-9a-f]+))?'", init)
    imports = []
    for name in sorted(os.listdir(os.path.join(flm, "js"))):
        if name.endswith(".js"):
            with open(os.path.join(flm, "js", name), encoding="utf-8") as handle:
                imports += [(name, target, version) for target, version in IMPORT.findall(handle.read())]
    tokens = {version for _, _, version in imports} | set(app_versions)
    if len(app_versions) != 1 or len(imports) != 9:
        fail("expected one app.js import in init.js and nine in js/, found %d and %d" % (len(app_versions), len(imports)))
    if expect == "unversioned":
        if tokens != {""}:
            fail("control: module imports already carry tokens %s" % sorted(tokens))
        print(json.dumps({"module_imports": 10, "versioned": 0}))
        return
    if tokens != {expect}:
        fail("module imports carry %s, expected only ?v=%s" % (sorted(tokens), expect))
    for target in sorted({"app.js"} | {target for _, target, _ in imports}):
        status, body = get("/plugins/filemanager/js/%s?v=%s" % (target, expect))
        with open(os.path.join(flm, "js", target), "rb") as handle:
            if status != 200 or body != handle.read():
                fail("js/%s?v=%s was not served with the file's content (HTTP %s)" % (target, expect, status))
    status, body = get("/php/getplugins.php")
    if status != 200 or ("js/app.js?v=%s'" % expect).encode() not in body:
        fail("php/getplugins.php does not hand browsers the versioned app.js import (HTTP %s)" % status)
    print(json.dumps({"module_imports": 10, "versioned": 10, "token": expect, "served": "ok"}))


def call(payload):
    body = urllib.parse.urlencode({"action": json.dumps(payload)}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1/plugins/filemanager/action.php", data=body, method="POST",
        headers={"Authorization": login(),
                 "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "X-Requested-With": "XMLHttpRequest"})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read())
    if result.get("errcode") is not None or result.get("error"):
        fail("File Manager %s failed: %s" % (payload["method"], json.dumps(result)[:300]))
    return result


def api():
    name = "appbox-gate-flm-" + secrets.token_hex(4)
    renamed = name + " renamed 'quoted'"
    created = os.path.join(TOP, WORK, name)
    moved = os.path.join(TOP, WORK, renamed)
    try:
        call({"method": "newDirectory", "target": "/%s/%s" % (WORK, name)})
        if not os.path.isdir(created):
            fail("newDirectory reported success but %s does not exist" % created)
        owner = os.stat(created)
        call({"method": "fileRename", "target": "/%s/%s" % (WORK, name), "to": "/%s/%s" % (WORK, renamed)})
        if os.path.exists(created) or not os.path.isdir(moved):
            fail("fileRename did not move %s to %s" % (created, moved))
        listing = call({"method": "listDirectory", "dir": "/" + WORK}).get("listing")
        names = {entry.get("name", "").rstrip("/") for entry in listing or []}
        if renamed not in names:
            fail("listDirectory does not show the renamed folder: %s" % sorted(names)[:20])
    finally:
        for path in (created, moved):
            if os.path.isdir(path):
                shutil.rmtree(path)
    print(json.dumps({"newDirectory": True, "fileRename": True, "listDirectory": len(names),
                      "owner": "%d:%d" % (owner.st_uid, owner.st_gid)}))


if len(sys.argv) == 3 and sys.argv[1] == "menus":
    menus(sys.argv[2])
elif len(sys.argv) == 3 and sys.argv[1] == "modules":
    modules(sys.argv[2])
elif len(sys.argv) == 2 and sys.argv[1] == "api":
    api()
else:
    fail("usage: filemanager-checks.py menus none|filemanager-1.5.1 | modules TOKEN|unversioned | api")
