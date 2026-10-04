#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
[ "$(cat /sys/class/dmi/id/board_vendor)" = ASRock ]
[ "$(cat /sys/class/dmi/id/board_name)" = "A620AI WiFi" ]
if [ -d /sys/module/asrock_nct6686 ]; then
    [ "$(cat /sys/module/asrock_nct6686/parameters/enable_control)" = N ] || {
        echo "Existing controller opted in; refusing to reload automatically" >&2
        exit 1
    }
    [ -r /sys/module/asrock_nct6686/parameters/identify_once ] &&
    [ "$(cat /sys/module/asrock_nct6686/parameters/identify_once)" = N ] || {
        echo "Existing module is an identification/unknown build; restore BIOS and unload first" >&2
        exit 1
    }
    for h in /sys/class/hwmon/hwmon*; do
        [ -f "$h/control_status" ] || continue
        grep -q 'handoff_pending=0' "$h/control_status" || {
            echo "BIOS/baseline recovery pending; refusing readonly startup" >&2
            exit 1
        }
        grep -q 'writable=0' "$h/control_status" && exit 0
    done
    echo "Module has no bound controller" >&2
    exit 1
fi
had_stock=0
if [ -d /sys/module/nct6683 ]; then
    had_stock=1
    modprobe -r nct6683
fi
if ! modprobe asrock_nct6686 identify_once=0 enable_control=0 cha_fan_channel=0 channel_verified=0 polarity_verified=0 invert_pwm=0; then
    if [ "$had_stock" = 1 ]; then
        # The observed 0x1633 board requires force=1 with the stock driver.
        modprobe nct6683 force=1
    fi
    exit 1
fi
for h in /sys/class/hwmon/hwmon*; do
    [ -f "$h/control_status" ] || continue
    cat "$h/control_status"
    exit 0
done
echo "Controller did not bind" >&2
exit 1
