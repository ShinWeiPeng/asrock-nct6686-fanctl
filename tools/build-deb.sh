#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out=${1:-"$root/artifacts/validation/package-$(date -u +%Y%m%dT%H%M%SZ)"}
mkdir -p "$out"
out=$(CDPATH= cd -- "$out" && pwd)
stage=$(mktemp -d "$out/stage.XXXXXX")
source="$stage/usr/src/asrock-nct6686-fanctl-0.1.1"
install -d "$source/src" "$stage/DEBIAN"
install -m 644 "$root"/src/*.c "$root"/src/*.h "$source/src/"
install -m 644 "$root/Makefile" "$root/dkms.conf" "$root/LICENSE" "$source/"
install -d "$stage/usr/share/doc/asrock-nct6686-fanctl-dkms"
install -m 644 "$root/LICENSE" "$stage/usr/share/doc/asrock-nct6686-fanctl-dkms/copyright"
cat > "$stage/DEBIAN/control" <<'EOF'
Package: asrock-nct6686-fanctl-dkms
Version: 0.1.1
Architecture: all
Depends: dkms, gcc, make
Section: kernel
Priority: optional
Maintainer: Local Administrator <root@localhost>
Description: Guarded ASRock A620AI WiFi NCT6686D hwmon driver source
 DKMS source package. Default module operation is readonly.
 Matching running-kernel headers must be installed separately.
 Does not load a module or take over fans during package installation.
EOF
cat > "$stage/DEBIAN/preinst" <<'EOF'
#!/bin/sh
set -eu
command -v dkms >/dev/null || exit 0

existing=$(dkms status -m asrock-nct6686-fanctl)
if printf '%s\n' "$existing" | grep -v '^asrock-nct6686-fanctl/0\.1\.1[, :]' | grep -q '[^[:space:]]'; then
    echo "Other DKMS versions remain; stop and remove the old version before installing 0.1.1" >&2
    printf '%s\n' "$existing" >&2
    exit 1
fi
EOF
cat > "$stage/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -eu
if [ "$1" = configure ]; then
    if ! dkms status -m asrock-nct6686-fanctl -v 0.1.1 | grep -q .; then
        dkms add -m asrock-nct6686-fanctl -v 0.1.1
    fi
    dkms build -m asrock-nct6686-fanctl -v 0.1.1 -k "$(uname -r)"
    dkms install -m asrock-nct6686-fanctl -v 0.1.1 -k "$(uname -r)"
fi
EOF
cat > "$stage/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -eu
if [ "$1" = remove ]; then
    if [ -d /sys/module/asrock_nct6686 ]; then
        echo "Stop CoolerControl, return to BIOS and unload asrock_nct6686 before removing" >&2
        exit 1
    fi
    dkms remove -m asrock-nct6686-fanctl -v 0.1.1 --all
    if dkms status -m asrock-nct6686-fanctl | grep -q '[^[:space:]]'; then
        echo "Other project DKMS versions remain; removal incomplete" >&2
        exit 1
    fi
fi
EOF
chmod 755 "$stage/DEBIAN/preinst" "$stage/DEBIAN/postinst" "$stage/DEBIAN/prerm"
dpkg-deb --root-owner-group --build "$stage" "$out/asrock-nct6686-fanctl-dkms_0.1.1_all.deb"
