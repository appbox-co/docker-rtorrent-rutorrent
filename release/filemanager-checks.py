"""File Manager checks run inside a started, healthy ruTorrent container.

The release gate pipes this file to `docker exec -i <container> python3 - MODE`.

  menus EXPECT   scan ruTorrent's JavaScript for context-menu entries whose
                 command is a string, which ruTorrent 5 greys out
                 (Novik/ruTorrent#3316). EXPECT is "none", or "filemanager-1.5.1"
                 for the control: File Manager 1.5.1's seven string commands
                 in plugins/filemanager/js/ui-fs.js and nothing else.
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
FLM_151_COMMANDS = [
    "flm.ui.getDialogs().showDialog('mkdir')",
    "flm.ui.getDialogs().showDialog('copy')",
    "flm.ui.getDialogs().showDialog('move')",
    "flm.ui.getDialogs().showDialog('delete')",
    "flm.ui.getDialogs().showDialog('rename')",
    "flm.ui.getDialogs().showDialog('mkdir')",
    "flm.goToPath(flm.currentPath)",
]


def fail(message):
    print("FAIL: " + message, file=sys.stderr)
    sys.exit(1)


def scan():
    hits = []
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
    return hits


def menus(expect):
    with open(os.path.join(ROOT, "js/objects.js"), encoding="utf-8") as handle:
        if CORE_RULE not in handle.read():
            fail("ruTorrent's js/objects.js no longer greys out string menu commands; the check is out of date")
    with open(os.path.join(ROOT, "plugins/filemanager/plugin.info"), encoding="utf-8") as handle:
        version = re.search(r"^plugin\.version:\s*(\S+)", handle.read(), re.M).group(1)
    hits = scan()
    for path, number, line in hits:
        print("string menu command: %s:%d %s" % (path, number, line[:160]))
    if expect == "none":
        if version != "1.6.0":
            fail("File Manager is %s, not 1.6.0" % version)
        if hits:
            fail("%d context-menu entries still have string commands" % len(hits))
    elif expect == "filemanager-1.5.1":
        if version != "1.5.1":
            fail("control: File Manager is %s, not 1.5.1" % version)
        files = {path for path, _, _ in hits}
        found = [cmd for _, _, line in hits for cmd in dict.fromkeys(FLM_151_COMMANDS) if '"%s"' % cmd in line]
        if files != {"plugins/filemanager/js/ui-fs.js"} or found != FLM_151_COMMANDS:
            fail("control: expected File Manager 1.5.1's seven string commands only, found %d in %s"
                 % (len(hits), sorted(files)))
    else:
        fail("unknown expectation: " + expect)
    print(json.dumps({"filemanager": version, "string_menu_commands": len(hits)}))


def call(payload):
    login = base64.b64encode((os.environ["USERNAME"] + ":" + os.environ["PASSWORD"]).encode()).decode()
    body = urllib.parse.urlencode({"action": json.dumps(payload)}).encode()
    request = urllib.request.Request(
        "http://127.0.0.1/plugins/filemanager/action.php", data=body, method="POST",
        headers={"Authorization": "Basic " + login,
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
elif len(sys.argv) == 2 and sys.argv[1] == "api":
    api()
else:
    fail("usage: filemanager-checks.py menus none|filemanager-1.5.1 | api")
