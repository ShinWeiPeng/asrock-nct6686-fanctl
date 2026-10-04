#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(sed -n 's/^PACKAGE_VERSION="\([0-9.]*\)"$/\1/p' "$root/dkms.conf")
[ -n "$version" ] || { echo "Invalid package version" >&2; exit 1; }
out=${1:-"$root/artifacts/validation/package-$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
stage=$(mktemp -d "$out/stage.XXXXXXXX")
chmod 755 "$stage"
source="$stage/usr/src/asrock-nct6686-fanctl-$version"
install -d "$source" "$stage/DEBIAN" "$stage/usr/local/libexec/asrock-nct6686"
cd "$root"
for relative in src/*.c src/*.h Makefile dkms.conf LICENSE README.md tools/*.sh tools/*.py \
    packaging/* docs/*.md; do
    [ -f "$relative" ] || continue
    install -d "$source/$(dirname -- "$relative")"
    install -m 644 "$relative" "$source/$relative"
done
for file in driver-service.py backup.sh load-readonly.sh restore-bios.sh stop-driver.sh; do
    install -m 755 "tools/$file" "$stage/usr/local/libexec/asrock-nct6686/$file"
done
install -d "$stage/etc/systemd/system/coolercontrold.service.d" \
    "$stage/usr/share/doc/asrock-nct6686-fanctl-dkms"
install -m 644 packaging/asrock-nct6686.service "$stage/etc/systemd/system/"
install -m 644 packaging/coolercontrold.conf \
    "$stage/etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf"
install -m 644 LICENSE "$stage/usr/share/doc/asrock-nct6686-fanctl-dkms/copyright"
install -m 644 docs/recovery.md "$stage/usr/share/doc/asrock-nct6686-fanctl-dkms/recovery.md"
cat > "$stage/DEBIAN/control" <<EOF
Package: asrock-nct6686-fanctl-dkms
Version: $version
Architecture: all
Depends: dkms, gcc, make, python3, systemd
Section: kernel
Priority: optional
Maintainer: Local Administrator <root@localhost>
Description: Guarded ASRock A620AI WiFi NCT6686D fan control
 Complete DKMS source, service, opt-in control and BIOS recovery tools.
 Defaults to readonly; matching running-kernel headers are required.
EOF
for name in preinst postinst prerm; do
    sed "s/@VERSION@/$version/g" "packaging/$name" > "$stage/DEBIAN/$name"
done
# preinst must back up old files before dpkg replaces them; reuse the same source.
cat tools/backup.sh >> "$stage/DEBIAN/preinst"
chmod 755 "$stage/DEBIAN/preinst" "$stage/DEBIAN/postinst" "$stage/DEBIAN/prerm"
printf '%s\n' /etc/systemd/system/asrock-nct6686.service \
    /etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf > "$stage/DEBIAN/conffiles"
dpkg-deb --root-owner-group --build "$stage" "$out/asrock-nct6686-fanctl-dkms_${version}_all.deb"
