#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
# Retained Requires= integration must not reactivate the removed driver on boot.
if systemctl cat coolercontrold.service >/dev/null 2>&1; then
    systemctl disable --now coolercontrold.service
fi
sh /usr/local/libexec/asrock-nct6686/stop-driver.sh
systemctl disable --now asrock-nct6686.service
dkms remove -m asrock-nct6686-fanctl -v 0.1.1 --all
if dkms status -m asrock-nct6686-fanctl | grep -q '[^[:space:]]'; then
    echo "Other project DKMS versions remain; removal is incomplete" >&2
    dkms status -m asrock-nct6686-fanctl >&2
    exit 1
fi
# Keep backups, source and disabled service definitions for audit/recovery.
echo "DKMS removed; stock driver restored. Backups retained in /var/lib."
