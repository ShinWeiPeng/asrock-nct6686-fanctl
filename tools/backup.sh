#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
backup=$(mktemp -d /var/lib/asrock-nct6686-backup.XXXXXXXX)
chmod 700 "$backup"
set --
for file in /etc/modprobe.d /etc/modules-load.d /etc/modules /etc/coolercontrol \
    /etc/systemd/system/asrock-nct6686.service \
    /etc/systemd/system/asrock-nct6686.service.d \
    /etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf \
    /usr/local/libexec/asrock-nct6686 /var/lib/asrock-nct6686 \
    /usr/src/asrock-nct6686-fanctl-*; do
    [ -e "$file" ] || [ -L "$file" ] || continue
    set -- "$@" "${file#/}"
done
tar -cf "$backup/state.tar" -C / "$@"
dkms status -m asrock-nct6686-fanctl > "$backup/dkms-status.txt"
uname -r > "$backup/kernel.txt"
echo "$backup"
