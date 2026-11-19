# php-artifacts: php85 8.5.13-r0 for Alpine 3.24 (x86_64)

Image: `repo.cylo.net/php-artifacts:php85-8.5.13-r0-alpine3.24` (FROM scratch;
nothing runs from it). Pin it by digest and mount or copy from it.

Alpine's v3.24 community index still had php85 8.5.12-r0 when PHP 8.5.13 was
released on 19 November 2026 with fixes for 17 php-src advisories (among them
CVE-2026-129289 FPM request smuggling, CVE-2026-115560 and CVE-2026-126714
session handling, CVE-2026-129496 timezone cache, CVE-2026-129474 and
CVE-2026-129182 backtrace use-after-free, CVE-2026-129481 session shutdown
use-after-free). Alpine's own security upgrade (aports MR !111133) targeted
master only. These are Alpine's own php85 packages, built by us from Alpine's
3.24 APKBUILD and signed with our own key.

## Contents

- `/packages/community/x86_64/*.apk` and `APKINDEX.tar.gz`: an apk repository
  of all 63 php85 subpackages, version 8.5.13-r0. The index and every
  package are signed with the key below.
- `/keys/cylo-php85-20261119152730.rsa.pub`: the public signing key
  (RSA 4096; SHA-256 of the DER public key
  `d8bdb93790988365041af3104209710c871862ae97e3e2fff84dfa7a670c52a6`).
  The private key is not in this image. It is kept only on the builder
  (`/home/appbox/php-artifact-keys/`, mode 700).
- `/SHA256SUMS`: SHA-256 of every file under `/packages` and `/keys`.
- `/build-info.txt`, `/build-environment-packages.txt`: the build container's
  Alpine release, apk-tools, and every installed package (makedepends
  included) at build time.

## Provenance

- Source: `https://www.php.net/distributions/php-8.5.13.tar.xz`
  - SHA-256 `607602acaf0c3061818e9916ec44a058e8b3d43959a83862b9cd3ec7bf5b785f`
    (matches php.net's releases JSON)
  - SHA-512 `00b5d0fc0a60fb071d060c0964fb3a9b833e1703d6c11aa765596f271cae1a9d8838ddc410af340e9bb62d125ff912e48a06ef630fdd15333c99d61ff50b61d5`
    (matches the APKBUILD and aports MR !111133)
  - `php-8.5.13.tar.xz.asc`: good signature from
    `49D9 AF6B C72A 80D6 6917 19C8 AA23 F5BE 9C70 97D4` (Volker Dusch, a
    PHP 8.5 release manager listed on https://www.php.net/gpg-keys.php)
- Recipe: `release/php85-artifact/aport-3.24-8.5.13/` in this repository
  (see its SOURCE.md): aports 3.24-stable `community/php85` at
  `68d9c653a611ff60d298074c9e7bfff033aebfe6` ("community/php85: fix secfixes
  format", pkgver 8.5.12) with the pkgver, secfixes and sha512 changes and
  `fix-ini_info.patch` from aports MR !111133 (commit
  `a39c3fa5b5ed62270eb914eb1dd1692bde42efb6`). Patches, test lists and every
  other source file are unchanged from 3.24-stable.
- Build: `release/php85-artifact/build-in-alpine.sh` (abuild 3.17.0-r0, clang
  22.1.3, `abuild deps` then `abuild` as an unprivileged `abuild` group user)
  in `alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6`
  (alpine:3.24, 3.24.2), started by `release/php85-artifact/builder-build.sh`
  on builder.grant.appboxes.co in a throwaway container with
  `--cpu-shares 256`, from docker-rtorrent-rutorrent commit
  `25530e33385777ee8ee5d2aa21de11914c07b75d`. Built on 19 November 2026,
  15:27–15:58 UTC.
- PHP test suite (`check()`, 48 workers): 21013 tests, 20128 passed,
  0 failed, 876 skipped, 9 expected failures, 0 warned.
- Gate before push: `release/php85-artifact/verify-artifact.sh` (contents and
  SHA256SUMS, signature of every package, install of every runtime
  subpackage in alpine:3.24, all modules load, `php-fpm85 -t`, `httpd -t`,
  multipart upload through the CLI server, php-fpm and apache2 + mod_php85,
  registry tag absent).

## Use

Upgrade only the php85 packages an image already has, from this repository
alone (no network, its own key directory, nothing added to `/etc/apk/keys`):

```dockerfile
ARG PHP85_ARTIFACT=repo.cylo.net/php-artifacts@sha256:<digest>
FROM ${PHP85_ARTIFACT} AS php85-artifact
FROM <base image pinned by digest>
RUN --mount=type=bind,from=php85-artifact,source=/,target=/run/php85-artifact \
    apk --no-cache --no-network --repositories-file /dev/null \
        --repository /run/php85-artifact/packages/community \
        --keys-dir /run/php85-artifact/keys \
        upgrade $(apk info | grep -E '^php85(-|$)')
```

The packages link against Alpine 3.24 libraries by soname, as Alpine's own
build does. An install that needs a library the base image lacks fails
rather than fetching it.

## Packages (SHA-256)

```text
6d7c2d0769bc74c8b5d442c1cf3eedb86e74dc3272a0706dacf58af6646b0a32  APKINDEX.tar.gz
7f91dd1e3cea71803a7bfb7cbc711ba1030a2f5bb74df8545e73afa82cec5f4f  php85-8.5.13-r0.apk
88cd854e9bfc7030239b12d1797f4a095e6aebd340f7354c2c96410f9137812e  php85-apache2-8.5.13-r0.apk
e1d162bf060fb6e703199cf1d2717debda78b4acdb860be9bdcc3b5e18ec48e0  php85-bcmath-8.5.13-r0.apk
44c2a9b91109e53feba27e8310592461a173db3181cea2facb42547794ee6312  php85-bz2-8.5.13-r0.apk
050c934c07394dad28658f479fc01716820fb115b82219931cb4cc6285893320  php85-calendar-8.5.13-r0.apk
20060509300ee8e0e1005f85ff245ef78ba0bcb1e16b97834329311777d34f2a  php85-cgi-8.5.13-r0.apk
8a1c6b5b1e88fb494c48ad4f906fb935290d91c84ac9188925b0d4dc5d8ef390  php85-common-8.5.13-r0.apk
884e294e3ca7e5254549dd0f83ef4031042ad52b17b6259656270724d88faadd  php85-ctype-8.5.13-r0.apk
50f330403a6056b502bd682ad40e2b35f4a2cb30caa7da2edb6cbe32e094d067  php85-curl-8.5.13-r0.apk
228d1ad53472206962f75074223a56e86f991e9eb785223de8673389741bde6b  php85-dba-8.5.13-r0.apk
9a6e668ae9d5740cf4886057e787e455bfa023911da41ee0414f7e74d01a6193  php85-dbg-8.5.13-r0.apk
e1a06406ab654f151feae82cffc5f34b4788ca8789bb3b11467e204f552defe2  php85-dev-8.5.13-r0.apk
9479ce6859e8523e77b508bc25b435256ffbda554b5939e25b766e874f8d0af5  php85-doc-8.5.13-r0.apk
9c13c641378cffbfa0dad33acc1fc3512d112f208a83768cf92fd95702410f65  php85-dom-8.5.13-r0.apk
94cfeceab511070f8ff2c06f1ebe4a33fe19d80ad732317ce96beb0c214671b1  php85-embed-8.5.13-r0.apk
25234de5a0042d4095c0310311358eb3d68a6805fabd87a99307c19c5e2aed69  php85-enchant-8.5.13-r0.apk
f9a306fc49c3c3060b2924640e98f185ea103d38cd1dd9f83e5fe5cb9401fed9  php85-exif-8.5.13-r0.apk
1edc14c3e4c6b6f70a0b47b9de828bae27e4415561b82dbb73de825086c83279  php85-ffi-8.5.13-r0.apk
608ca80f213be2ca6bc95567c164a12b299fa30dfa34ed15554d2f0b0cbe6816  php85-fileinfo-8.5.13-r0.apk
122ee9d3d67be0be057df777c932b1d1c3528cee27cfde6b079a096619d2b09f  php85-fpm-8.5.13-r0.apk
e9c148d5e3b1c36a5c896b37338261887ca358b5ebc066962952c38319328ac4  php85-ftp-8.5.13-r0.apk
3c663adc47e24d38d5177cb78e69ad702df6b8d4ce8b63c01e574ba22bcbe0ce  php85-gd-8.5.13-r0.apk
ef195f370f147940bedb97bcaa68120b01eb9696003397f2843d9cc0344dac8a  php85-gettext-8.5.13-r0.apk
c8f806a519cb08ab5cb2321d77234e0536a296f80a825d56265b0b7bfa4e7693  php85-gmp-8.5.13-r0.apk
4bb57016ad01232f913ef7fa2cf473ef0a084c0e6fdcc338285386db95ae0f45  php85-iconv-8.5.13-r0.apk
4141e5cc2c3d49cf1f2210800b0aea676be7d8ddd80b5b7218a0a7db07689e35  php85-intl-8.5.13-r0.apk
a5eecde320b096a614739a8c51670139fbe08ac427ed192714aee9b7c2df1842  php85-ldap-8.5.13-r0.apk
251880e133858ee7a4d6255187bcd8bc2ca0920931b42809bd5f58ac0c11ee97  php85-litespeed-8.5.13-r0.apk
a11b7f5fa0f0fbafe264d090a3ca62c0b9ba07f0d2afc40b2095d8c8fd2fe69c  php85-mbstring-8.5.13-r0.apk
4bdd1375ac362a2e932e4a5c3f3f888215905e520b572aded43d92554c243bb3  php85-mysqli-8.5.13-r0.apk
b8a9052916efcb32b843e9330dc1697fd6f2b6c7b04083b06941a829a3365034  php85-mysqlnd-8.5.13-r0.apk
85857a2706ac485446aa4e14677b11729bccbc1f5e048cb9270daa9692380152  php85-odbc-8.5.13-r0.apk
246d7d44fb912594b3a1efdeacd8b5865cd23b962213eefa7268dcc801644906  php85-openssl-8.5.13-r0.apk
195b78d66ae1b8fb8a590004b5305710b4173f1536d4d9f0b8d078ddb6e7e63e  php85-pcntl-8.5.13-r0.apk
cfab5d1d5d4e6de0940bc86a637b4997c173d7af3e124a3e5bfeb1205cc4eb23  php85-pdo-8.5.13-r0.apk
4091b010806ec67e85bfba8a195c68f4edbafa719d904cd07a5a4dbe8deff8e4  php85-pdo_dblib-8.5.13-r0.apk
e60feda0c9aed31db1fd1161a0294a0f1748ecc15e954844816950a5ae2d8d03  php85-pdo_mysql-8.5.13-r0.apk
0c67e32bc435a74b34bad44d394029875f44f83f96bf0c78fb407f1d285b0b9f  php85-pdo_odbc-8.5.13-r0.apk
46b74b2d70f69604515e80a6ec9e22719e979cbd02748a5d0d8634ee7ceb7d15  php85-pdo_pgsql-8.5.13-r0.apk
95f2de22efcf31989c702b3a7b3349595e4e49a19fa806b44013abde09d4a695  php85-pdo_sqlite-8.5.13-r0.apk
f9bca80bea47a763335dc67f5edc83865c53ebdaa0932fae29b185ff7c8c3156  php85-pear-8.5.13-r0.apk
70b7511cabfef02c1405537fd3be6067e489aadccfa6accda63886e23046b038  php85-pgsql-8.5.13-r0.apk
f2936c2b084ac662f20b43b80787aeb1a29ba32721c3be2d408894f610373fe6  php85-phar-8.5.13-r0.apk
8fadfd80a0726222debc14d6b2a919ef3baf4b4ab88dcdc2f377d30cd88ace2b  php85-phpdbg-8.5.13-r0.apk
c3332447d72ab62d0cf9a4752e1ab0033910133777e1541fd9973a2426d9dc9c  php85-posix-8.5.13-r0.apk
424a4cf7d3aefa71a023b0cac1de2f3ee9d434f7482f588b0309013f5cb458b5  php85-session-8.5.13-r0.apk
cae41a5cdff4bb84300a52b5e9facdfe1b3ae9821c40ba1fdec182067b764c4e  php85-shmop-8.5.13-r0.apk
d7d95dda8b01dc4bd438f96036cc1e3845fa6616bda8bf5b336e6ee31051058c  php85-simplexml-8.5.13-r0.apk
c86d5fea322e9b2d36d75f3c9b9255141fa4f43be3937f5a36cd89ac0ccd4223  php85-snmp-8.5.13-r0.apk
2a715a85c48a88dd9bba9f13ea2f928c499c88495a7784e6321fcb8cc4f63864  php85-soap-8.5.13-r0.apk
47c6931a844230e4dac7ffb9419b03d5562ea72cb92b16e5ae2278a1d2a26a35  php85-sockets-8.5.13-r0.apk
bcbf51b8d220a999b25411e46569a0103ec8ea05995cd3d18362474feee21ea5  php85-sodium-8.5.13-r0.apk
129af26a03c648f6a48ff3ce6a430db76b9084070c0463af8b7347624efec03f  php85-sqlite3-8.5.13-r0.apk
839276cc23f0bed3b529076fdc34893667b6bd45cfb6d333e4b1f8d10ee5d0dc  php85-sysvmsg-8.5.13-r0.apk
a89a7db4afc49ba2c44430415dace4fa18d2279010f65f4d80522f1617cbbe2a  php85-sysvsem-8.5.13-r0.apk
1cb19a9fe137e3bbabe7978ff9e29c100dd687092654a98515ee67f6a400276d  php85-sysvshm-8.5.13-r0.apk
ad7693152ada26feea7b9f29880512dfd3277be886672ecc63d1b2714cb92200  php85-tidy-8.5.13-r0.apk
bd3049b7dfb41bd8978c66721cf4b06922e144190236bc2d645d9e2d27849af6  php85-tokenizer-8.5.13-r0.apk
59c53546301c80d644fbcaf4c75a363ddcc39cb338078b731a2ceac132abcfa6  php85-xml-8.5.13-r0.apk
bc0646b4425c81b299ce97c2ed7d1f034f0862499fde31b9760f0100fef80828  php85-xmlreader-8.5.13-r0.apk
8c8a96499cee556e5eeb4d6cea06e66e830b8163dd681cefa38b40e1e14055d6  php85-xmlwriter-8.5.13-r0.apk
0dfdcc33369b60797c4db1821f0685c045b698044c6bcfb31e14a21183d91455  php85-xsl-8.5.13-r0.apk
1676954558764b7cc59e50f114fab4555a62546a62c9712c03ed8e8226700c26  php85-zip-8.5.13-r0.apk
```
