#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ "$(cat /sys/class/dmi/id/board_vendor)" = ASRock ]
[ "$(cat /sys/class/dmi/id/board_name)" = "A620AI WiFi" ]
kernel=$(uname -r)
[ -f "/lib/modules/$kernel/build/Makefile" ] || {
    echo "Install matching headers: proxmox-headers-$kernel" >&2; exit 1
}
command -v dkms >/dev/null

existing=$(dkms status -m asrock-nct6686-fanctl)
if printf '%s\n' "$existing" | grep -v '^asrock-nct6686-fanctl/0\.1\.1[, :]' | grep -q '[^[:space:]]'; then
    echo "Other DKMS versions remain; stop and remove the old version before installing 0.1.1" >&2
    printf '%s\n' "$existing" >&2
    exit 1
fi

backup=$(mktemp -d /var/lib/asrock-nct6686-backup.XXXXXX)
chmod 700 "$backup"
tar -cf "$backup/module-settings.tar" -C /etc modprobe.d modules-load.d modules
if [ -d /etc/coolercontrol ]; then
    tar -cf "$backup/coolercontrol-config.tar" -C /etc coolercontrol
fi
package=asrock-nct6686-fanctl
version=0.1.1
destination="/usr/src/$package-$version"
if [ -d "$destination" ]; then
    for file in src/nct6686_hwmon.c src/fan_control.c src/fan_control.h Makefile dkms.conf; do
        cmp "$root/$file" "$destination/$file" >/dev/null || {
            echo "Existing DKMS source differs; refusing overwrite" >&2; exit 1
        }
    done
else
    install -d "$destination/src"
    install -m 644 "$root"/src/*.c "$root"/src/*.h "$destination/src/"
    install -m 644 "$root/Makefile" "$root/dkms.conf" "$destination/"
fi
if ! dkms status -m "$package" -v "$version" | grep -q .; then
    dkms add -m "$package" -v "$version"
fi
dkms build -m "$package" -v "$version" -k "$kernel"
dkms install -m "$package" -v "$version" -k "$kernel"
install -d /usr/local/libexec/asrock-nct6686
for file in load-readonly.sh restore-bios.sh stop-driver.sh; do
    install -m 755 "$root/tools/$file" /usr/local/libexec/asrock-nct6686/
done
install -m 644 "$root/packaging/asrock-nct6686.service" /etc/systemd/system/
systemctl daemon-reload
echo "Installed DKMS; backup: $backup"
echo "No module was loaded. Next: systemctl start asrock-nct6686"
