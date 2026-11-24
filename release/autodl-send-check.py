#!/usr/bin/env python3
"""Send a test torrent through autodl-irssi's own rTorrent upload path.

Runs inside a running ruTorrent container as root:
    docker exec -i <container> python3 - <expect> < release/autodl-send-check.py

<expect> is "sent" (the torrent must reach rTorrent and autodl must report
"Sent torrent to rtorrent") or "no-address" (the control: autodl must report
that rt-address is not initialised and rTorrent must not get the torrent).

The check builds a one-file torrent, writes a small Perl driver, and has the
live irssi process run it with /script exec, pushed through irssi's dtach
socket. The driver calls AutodlIrssi::MatchedRelease::_sendRtorrent, the code
autodl runs for a matched release with "upload-type = rtorrent", so the SCGI
address lookup, the socket permissions and the XML-RPC load are autodl's own.
autodl's messages are read back through its GUI server (getlines), as the
ruTorrent plugin does. Prints one JSON summary line; exits non-zero on
failure.
"""
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import xmlrpc.client

AUTODL_CFG = "/torrents/config/autodl/autodl.cfg"
DTACH_SOCKET = "/detach_sess/.irssi"
SCGI_SOCKET = "/var/run/rtorrent/scgi.socket"
WORK = "/tmp/appbox-gate-autodl"
RT_DIR = "/torrents/downloading"
SENT = "Sent torrent to rtorrent"
NO_ADDRESS = "You have not initialized rt-address"


def fail(msg):
    print("FAIL: " + msg, file=sys.stderr)
    sys.exit(1)


def bencode(value):
    if isinstance(value, int):
        return b"i%de" % value
    if isinstance(value, str):
        value = value.encode()
    if isinstance(value, bytes):
        return b"%d:%s" % (len(value), value)
    if isinstance(value, dict):
        return b"d" + b"".join(bencode(k) + bencode(value[k]) for k in sorted(value)) + b"e"
    raise TypeError(type(value))


def gui_settings():
    port = password = None
    with open(AUTODL_CFG, encoding="utf-8", errors="replace") as cfg:
        for line in cfg:
            match = re.match(r"\s*gui-server-(port|password)\s*=\s*(.*?)\s*$", line)
            if match and match.group(1) == "port":
                port = int(match.group(2))
            elif match:
                password = match.group(2)
    if not port or not password:
        fail("autodl.cfg has no gui-server-port/password")
    return port, password


def gui(command, timeout=20):
    port, password = gui_settings()
    command = dict(command, password=password)
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as conn:
        conn.sendall(json.dumps(command).encode())
        conn.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
    reply = json.loads(data.decode("utf-8", "replace"))
    if reply.get("error"):
        fail("autodl GUI server error: %s" % reply["error"])
    return reply


def plain(line):
    text = line.get("line", "") if isinstance(line, dict) else str(line)
    return re.sub(r"\x03\d{0,2}(,\d{1,2})?|[\x00-\x1f]", "", text)


def rtorrent(method, *params):
    body = xmlrpc.client.dumps(params, method).encode()
    header = b"CONTENT_LENGTH\x00%d\x00SCGI\x001\x00" % len(body)
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(20)
        conn.connect(SCGI_SOCKET)
        conn.sendall(b"%d:%s,%s" % (len(header), header, body))
        data = b""
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            data += chunk
    return xmlrpc.client.loads(data.split(b"\r\n\r\n", 1)[1])[0][0]


def loaded_hashes():
    return {h.upper() for h in rtorrent("download_list", "", "main")}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("sent", "no-address"):
        fail("usage: autodl-send-check.py sent|no-address")
    expect = sys.argv[1]

    # irssi loads autodl a few seconds after the container reports healthy.
    deadline = time.time() + 120
    while True:
        try:
            cid = gui({"command": "getlines"})["cid"]
            break
        except (OSError, ValueError) as exc:
            if time.time() > deadline:
                fail("autodl GUI server not reachable: %s" % exc)
            time.sleep(3)

    name = "appbox-gate-autodl-" + secrets.token_hex(4)
    piece = b"\0" * 16384
    info = {"length": len(piece), "name": name, "piece length": len(piece),
            "pieces": hashlib.sha1(piece).digest(), "private": 1}
    info_hash = hashlib.sha1(bencode(info)).hexdigest().upper()
    if info_hash in loaded_hashes():
        fail("test torrent already loaded before the check")

    os.makedirs(WORK, exist_ok=True)
    os.chmod(WORK, 0o755)
    torrent_path = WORK + "/gate.torrent"
    status_path = WORK + "/status"
    driver_path = WORK + "/driver.pl"
    with open(torrent_path, "wb") as out:
        out.write(bencode({"announce": "http://127.0.0.1:1/announce", "info": info}))
    if os.path.exists(status_path):
        os.unlink(status_path)
    os.chmod(WORK, 0o777)
    driver = """use strict; use warnings;
my $ok = eval {
    require AutodlIrssi::MatchedRelease;
    open(my $in, '<:raw', '%(torrent)s') or die "open: $!";
    my $data = do { local $/; <$in> };
    close($in);
    my $m = AutodlIrssi::MatchedRelease->new(undef);
    $m->{ti} = { torrentName => '%(name)s' };
    $m->{torrentFileData} = $data;
    $m->{info_hash} = pack('H*', '%(hash)s');
    $m->{info_name} = '%(name)s';
    $m->{startTime} = time();
    $m->{uploadMethod} = { rtDir => '%(rtdir)s', rtCommands => '', rtLabel => '', rtRatioGroup => '',
        rtChannel => '', rtPriority => '', rtIgnoreScheduler => 0, rtDontAddName => 0 };
    $m->_sendRtorrent();
    1;
};
open(my $out, '>', '%(status)s') or die;
print $out ($ok ? "called\\n" : "died: $@");
close($out);
""" % {"torrent": torrent_path, "name": name, "hash": info_hash, "rtdir": RT_DIR, "status": status_path}
    with open(driver_path, "w") as out:
        out.write(driver)
    os.chmod(driver_path, 0o644)
    os.chmod(torrent_path, 0o644)

    command = "/script exec do '%s';\r" % driver_path
    subprocess.run(["dtach", "-p", DTACH_SOCKET], input=command.encode(), check=True, timeout=30)

    deadline = time.time() + 30
    while not os.path.exists(status_path):
        if time.time() > deadline:
            fail("irssi did not run the driver (no status file)")
        time.sleep(1)
    with open(status_path) as status_file:
        status = status_file.read().strip()
    if status != "called":
        fail("driver failed inside irssi: " + status[:300])

    lines = []
    loaded = False
    deadline = time.time() + (60 if expect == "sent" else 20)
    while time.time() < deadline:
        lines += [plain(l) for l in gui({"command": "getlines", "cid": cid}).get("lines") or []]
        loaded = info_hash in loaded_hashes()
        if expect == "sent" and loaded and any(SENT in l for l in lines):
            break
        time.sleep(2)

    gate_lines = [l for l in lines if name in l or NO_ADDRESS in l]
    summary = {"expect": expect, "loaded": loaded, "autodl": [l[:200] for l in gate_lines]}
    if expect == "sent":
        if not loaded:
            fail("rTorrent did not load the torrent autodl sent; autodl said: %s" % gate_lines)
        if not any(SENT in l and name in l for l in lines):
            fail("autodl did not report '%s'; it said: %s" % (SENT, gate_lines))
        # A single-file torrent's directory is the rt-dir itself.
        directory = rtorrent("d.directory", info_hash)
        summary["directory"] = directory
        rtorrent("d.erase", info_hash)
        if directory.rstrip("/") != RT_DIR:
            fail("torrent loaded with directory %r, expected the filter's rt-dir %s" % (directory, RT_DIR))
    else:
        if loaded:
            fail("control: rTorrent loaded the torrent although autodl has no SCGI address")
        if not any(NO_ADDRESS in l for l in lines):
            fail("control: autodl did not report '%s'; it said: %s" % (NO_ADDRESS, gate_lines))
    print(json.dumps(summary))


main()
