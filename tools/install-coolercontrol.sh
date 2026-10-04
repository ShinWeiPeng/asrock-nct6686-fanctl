#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Repository and environment variables from official CoolerControl documentation.
set -eu
[ "$(id -u)" -eq 0 ]
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
[ -x /usr/local/libexec/asrock-nct6686/load-readonly.sh ]
if [ ! -f /etc/apt/sources.list.d/coolercontrol.sources ]; then
    curl -fsSL --max-time 60 https://apt.coolercontrol.org/coolercontrol-archive-keyring.gpg -o /usr/share/keyrings/coolercontrol-archive-keyring.gpg
    chmod 644 /usr/share/keyrings/coolercontrol-archive-keyring.gpg
    cat > /etc/apt/sources.list.d/coolercontrol.sources <<'EOF'
Types: deb
URIs: https://apt.coolercontrol.org/debian
Suites: stable
Components: main
Signed-By: /usr/share/keyrings/coolercontrol-archive-keyring.gpg
EOF
fi
# Only update this repository; leave unrelated repository configuration alone.
apt-get update -o Dir::Etc::sourcelist="sources.list.d/coolercontrol.sources" -o Dir::Etc::sourceparts="-" -o APT::Get::List-Cleanup=0
install -d /etc/systemd/system/coolercontrold.service.d
install -m 644 "$root/packaging/coolercontrold.conf" /etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf
# The dependency and loopback overrides are in place before any package autostart.
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends coolercontrold
systemctl daemon-reload
systemctl enable --now asrock-nct6686.service
systemctl enable --now coolercontrold.service
echo "CoolerControl is available over an SSH tunnel to localhost:11987"
