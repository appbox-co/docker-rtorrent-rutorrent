# aports community/php85 for 3.24-stable, upgraded to 8.5.13

Base: aports 3.24-stable `68d9c653a611ff60d298074c9e7bfff033aebfe6` ("community/php85: fix secfixes format",
pkgver 8.5.12, pkgrel 0). Every file here is that commit's `community/php85`
except:

- `APKBUILD`: pkgver 8.5.13, pkgrel 0, the 8.5.13 secfixes block, the
  php-8.5.13.tar.xz sha512 and `fix-ini_info.patch` added to source and
  sha512sums. These are the same changes as the upstream security upgrade for
  master, aports MR !111133 (commit a39c3fa5b5ed62270eb914eb1dd1692bde42efb6),
  minus its master-only removal of the loongarch64/s390x test lists.
- `fix-ini_info.patch`: copied from MR !111133 (php-src PR 24753, a test fix).

php-8.5.13.tar.xz: sha256 607602acaf0c3061818e9916ec44a058e8b3d43959a83862b9cd3ec7bf5b785f
(php.net releases JSON), sha512 as in APKBUILD (matches MR !111133), and
php-8.5.13.tar.xz.asc is a good signature from
49D9 AF6B C72A 80D6 6917 19C8 AA23 F5BE 9C70 97D4 (Volker Dusch, PHP 8.5
release manager, listed on https://www.php.net/gpg-keys.php).
