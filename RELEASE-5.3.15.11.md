# ruTorrent 5.3.15.11 (0.16.24): autodl-irssi can send torrents to rTorrent

## Cause

Support ticket #075612: since the customer moved to ruTorrent 5, autodl-irssi
had matched and downloaded 25 releases, but none of them reached rTorrent.

autodl sends a matched torrent to rTorrent over SCGI. It takes the address
from `rt-address` under `[options]` in autodl.cfg, or, when that is unset,
from the first `scgi_local`, `scgi_port` or `network.scgi.open_*` line in
`~/.rtorrent.rc` (`AutodlIrssi::MatchedRelease::_getRtAddress`). On the 5.x
image:

- irssi runs with `HOME=/home/rtorrent`, and there was no
  `/home/rtorrent/.rtorrent.rc`. rTorrent's own config is
  `/torrents/config/rtorrent/.rtorrent.rc` plus `.rtlocal.rc`.
- The autodl.cfg that Appbox writes holds only the GUI server port and
  password. The autodl-rutorrent settings have no field for `rt-address`.

So the address was empty, and every filter with `upload-type = rtorrent`
logged `Can't send torrent file to rtorrent. You have not initialized
rt-address (SCGI address).` The torrent had already been downloaded and
recorded in autodl's history, so autodl did not try it again. The 3.10 image
worked because its irssi user's `~/.rtorrent.rc` was rTorrent's config.
Filters with `upload-type = watchdir` were not affected.

No Appbox 5.x build has created that file or set `rt-address`, so every 5.x
release has this fault; it was confirmed on 5.3.15.7 (the customer's) and
5.3.15.10. The autodl release gate, `release/verify-autodl-image.sh`, checked
only stylesheets.

## What changed

The published 5.3.15.10 image
(`repo.cylo.net/rutorrent@sha256:8ab0ef99acd54013efe2ea0b5c277d94020f8e7842eb38814b746122683981b7`)
plus `/home/rtorrent/.rtorrent.rc` (rtorrent:rtorrent 644), from
`rootfs/home/rtorrent/.rtorrent.rc`, with one setting:

```text
network.scgi.open_local = /var/run/rtorrent/scgi.socket
```

That is the socket rTorrent opens (`cfg.rundir` in `.rtlocal.rc`) and the one
ruTorrent and nginx use. rTorrent never reads this file. An `rt-address` set
in autodl.cfg still takes precedence. The socket is `rtorrent:rtorrent 770`,
and irssi runs as rtorrent, so autodl can connect.

Nothing else changed: rTorrent, libtorrent, ruTorrent, the plugins, themes,
PHP 8.5.13, nginx and the basic-auth behaviour are those of 5.3.15.10.
Customers need no action after updating: autodl reads the file again for each
torrent it sends. Torrents that autodl matched before the update were not
added and won't be retried; customers have to add them by hand.

## Testing

`release/autodl-send-check.py` tests the code path that failed. It builds a
one-file torrent, then has the container's running irssi execute a short Perl
driver (`/script exec`, typed into irssi's dtach session). The driver calls
`AutodlIrssi::MatchedRelease::_sendRtorrent`, the method autodl runs for a
matched release with `upload-type = rtorrent`. It uses an `rt-dir` of
`/torrents/downloading` and no `rt-address`, as Appbox's autodl.cfg has none.
The check then reads autodl's messages from its GUI server (`getlines`, as the
ruTorrent plugin does) and asks rTorrent over SCGI whether the torrent loaded.

- `sent` passes when rTorrent has the torrent with the filter's directory and
  autodl logged "Sent torrent to rtorrent". The test torrent is then erased.
- `no-address` (the control) passes when autodl logged the rt-address error
  and rTorrent did not get the torrent.

A probe on builder.grant first ran the check against a published 5.3.15.10
container. `no-address` passed, then with the new file copied into the same
container `sent` passed. The driver path is the one a real announce takes
after the torrent has been downloaded.

## Build and gate

Trial runs on builder.grant, each from a `git archive` of a local commit:
`docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.autodl-rt-address`,
then `release/verify-autodl-rt-address-image.sh` in trial mode. The first ran on
`729abdd` (`local/rutorrent-trial:5.3.15.11-Zmk8U6`). The last ran on `cf88877`
(`local/rutorrent-trial:5.3.15.11-vnpIVk`), after the review fixes below. Both
passed:

- the 5.3.15.10 layers (38) plus one, with labels, entrypoint, healthcheck
  and environment unchanged;
- of 33,578 filesystem entries, only `/home/rtorrent/.rtorrent.rc` was
  added, identical to the repository file, rtorrent:rtorrent 644;
- fresh install: runtime and basic-auth checks, and `sent` (autodl:
  "Sent torrent to rtorrent", directory `/torrents/downloading`);
- after a restart: the same checks, the earlier upload retained, and `sent`;
- upgrade from 5.3.15.10 on the same volumes. Before the upgrade, `no-address`
  passed on 5.3.15.10 (autodl: "Can't send torrent file to rtorrent. You have
  not initialized rt-address (SCGI address)."). After it, `.rtorrent.rc`, the
  session torrents, completed data, theme.dat and autodl.cfg (with five added
  rtorrent-upload filters) were unchanged, the runtime and login checks passed,
  and `sent` passed;
- the registry reported `repo.cylo.net/rutorrent:5.3.15.11-0.16.24` absent
  (MANIFEST_UNKNOWN) before and after.

autodl reported a total time of about 15 seconds for each send in the gate.

## Review

Two reviewers who did not write the change, Claude Opus 5.5 and Claude
Sonnet 5.5, both found it ready to roll out. Both noted that
`COPY rootfs /` in the full `Dockerfile` ran after the chown of
`/home/rtorrent`, so a full build would have left that directory
`root:root 755` and the new file root-owned. Opus reproduced this with a
BuildKit build. The chown, now with `chmod 775`, runs after the COPY
(`cf88877`); a local build of that order gives `rtorrent:rtorrent 775` and
`rtorrent:rtorrent 644`, as in the overlay. The 5.3.15.11 overlay never ran
that part of the build, so it was unaffected. Sonnet also found a dead
`chmod` in `autodl-send-check.py`; the check now hands its work directory to
rtorrent instead.

## Release

Release build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.autodl-rt-address -t repo.cylo.net/rutorrent:5.3.15.11-0.16.24 .`
on builder.grant from the exact pushed commit
`0262a7157efda7ea682251799ec1c9028faacd82`.
`release/verify-autodl-rt-address-image.sh` passed in release mode: 5.3.15.10's
38 layers plus one, and only `/home/rtorrent/.rtorrent.rc` added (33,578
entries). autodl sent a torrent to rTorrent on a fresh install, after a
restart and after an upgrade from 5.3.15.10, where the control failed with
the rt-address error. The registry reported the tag absent before and after
the checks, and the first push succeeded.

## Published

- `repo.cylo.net/rutorrent:5.3.15.11-0.16.24`
- Digest: `sha256:3fc67478bd5f9a476adfc2ccc8f976618852e061682d16c0bb042eb564259137`
  (OCI index: linux/amd64 `sha256:8395d79cd2fcdf398142c535a1c5eed7af27d053ff42b8ed975f9c9a6257bdf4` plus attestation)

5.3.15.11 also carries club-QuickBox v2 from 5.3.15.10, which stays
admin-only and is not published; 5.3.15.11 replaces 5.3.15.9 directly.
Catalogue: cylo-api `migrations/20261124_rutorrent_5_3_15_11.sql`
(admin-only, not default) and `..._publish.sql` (appbox-co/cylo-api#308).
