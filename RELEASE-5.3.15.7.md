# ruTorrent 5.3.15.7 (0.16.24): PHP 8.5.13

Released 19 November 2026 for the PHP security release of that day (17
php-src advisories, fixed in PHP 8.5.13).

## What changed

The published 5.3.15.6 image (`repo.cylo.net/rutorrent@sha256:0fcfa6f3bca3f6276edf1ca255e8774db2d8582089583bbbca9b9a6bf5aaa6ce`)
with only its 16 installed php85 packages upgraded from 8.5.12-r0 to
8.5.13-r0. rTorrent, libtorrent, ruTorrent, the plugins, rootfs, nginx and
PHP configuration and the basic-auth behaviour of 5.3.15.6 are unchanged.

Alpine's v3.24 index did not have php85 8.5.13 yet (aports MR !111133 was
for master only), so the packages come from our own build of Alpine's 3.24
`community/php85` APKBUILD at 8.5.13:
`repo.cylo.net/php-artifacts:php85-8.5.13-r0-alpine3.24`
(`sha256:75886f598da9b2bed755db76dbb66804ce77ad392e3d19cd4b89cb3e3688cb95`),
described in `release/php85-artifact/README.php85-8.5.13-r0-alpine3.24.md`
(PHP test suite: 21013 tests, 0 failed).

## Build and gate

- Build: `docker build --builder default --pull --no-cache --platform linux/amd64 -f Dockerfile.php-security -t repo.cylo.net/rutorrent:5.3.15.7-0.16.24 .`
  on builder.grant.appboxes.co from the exact pushed commit
  `16fa57f784db8fd4910f5de5aef7a540d33500d7`.
- Gate: `release/verify-image.sh repo.cylo.net/rutorrent:5.3.15.7-0.16.24`
  passed in release mode before the push:
  - the 5.3.15.6 layers (30) plus one; entrypoint, healthcheck, environment unchanged;
  - only php85 packages changed, all 16 now 8.5.13-r0 and matching the
    artifact APKINDEX checksums; php85 and php-fpm85 report 8.5.13;
  - php85/php-fpm85 modules identical to 5.3.15.6; /etc/php85, /etc/nginx and
    /tpls unchanged; no .apk-new files;
  - multipart upload through the php85 CLI server; ruTorrent PHP regression
    tests (11 files, 1992 assertions);
  - fresh install with the catalogue's app 66 environment and install
    fields: nginx -t and php-fpm85 -t, FPM multipart, a torrent added through
    addtorrent.php, public share.php without login; basic auth refuses no
    login and a wrong password and accepts the right one on the UI, PHP,
    addtorrent, /RPC2, XML-RPC :8000 and WebDAV :9000;
  - upgrade from 5.3.15.6 with the same /torrents and /passwd: the torrent
    seeded on 5.3.15.6 is retained, a new one is added, and the same
    basic-auth checks pass;
  - the registry reported the tag absent before the push.
- The first two gate runs stopped before pushing at the fresh-install
  addtorrent check: the container is healthy about ten seconds before
  ruTorrent's `initplugins.php` (scheduled 10 s after rTorrent starts by
  `.rtlocal.rc`) has run, and addtorrent.php returns "Failed" until then.
  The published 5.3.15.6 image does the same. The gate now waits for the
  plugin initialisation (`16fa57f`); the checks are unchanged.

## Published

- `repo.cylo.net/rutorrent:5.3.15.7-0.16.24`
- Digest: `sha256:db1a64429462205a3bc41833e4886fc4205945b5115a907ae6bf303e087b9df6`

Catalogue: cylo-api `migrations/20261119_rutorrent_5_3_15_7.sql` (admin-only,
not default) and `..._publish.sql`. Not applied; no instance updated.
