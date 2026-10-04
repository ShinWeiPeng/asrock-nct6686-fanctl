#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sh "$script_dir/restore-bios.sh"
if [ -d /sys/module/asrock_nct6686 ]; then
    modprobe -r asrock_nct6686
fi
if [ ! -d /sys/module/nct6683 ] &&
   [ "$(cat /sys/class/dmi/id/board_vendor)" = ASRock ] &&
   [ "$(cat /sys/class/dmi/id/board_name)" = "A620AI WiFi" ]; then
    modprobe nct6683 force=1
fi
