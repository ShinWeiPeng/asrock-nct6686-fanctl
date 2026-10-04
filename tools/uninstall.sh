#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
# The package prerm performs bounded BIOS recovery before DKMS removal.
apt-get remove asrock-nct6686-fanctl-dkms
echo "Removal requested through dpkg; private backups remain under /var/lib."
