#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/artifacts/validation"
out=$(mktemp -d "$root/artifacts/validation/install-package.XXXXXXXX")
sh "$root/tools/build-deb.sh" "$out"
set -- "$out"/*.deb
[ "$#" -eq 1 ] && [ -f "$1" ]
apt-get install -y "$1"
echo "Package installed; no module loaded. Start asrock-nct6686.service for readonly operation."
