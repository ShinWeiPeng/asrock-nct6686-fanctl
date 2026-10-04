#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(id -u)" -eq 0 ] || { echo "Root is required" >&2; exit 1; }
controller=
for h in /sys/class/hwmon/hwmon*; do
    [ -f "$h/control_status" ] || continue
    [ -z "$controller" ] || { echo "Ambiguous controller count; no handoff attempted" >&2; exit 1; }
    controller=$h
done
if [ -n "$controller" ]; then
    status=$(cat "$controller/control_status")
    case "$status" in
        *"handoff_pending=1"*)
            [ -w "$controller/restore_bios" ] || { echo "Recovery interface missing" >&2; exit 1; }
            printf '2\n' > "$controller/restore_bios"
            status=$(cat "$controller/control_status")
            case "$status" in
                *"handoff_pending=0"*) ;;
                *) echo "Recovery incomplete; leaving driver loaded" >&2; exit 1 ;;
            esac
            ;;
    esac
    case "$status" in
        *"writable=0"*) echo "Controller remained readonly"; exit 0 ;;
        *"writable=1"*) ;;
        *) echo "Unknown controller status" >&2; exit 1 ;;
    esac
    channel=$(printf '%s\n' "$status" | sed -n 's/^channel=\([1-8]\) .*/\1/p')
    [ -n "$channel" ] || { echo "Invalid verified channel" >&2; exit 1; }
    printf '2\n' > "$controller/pwm${channel}_enable"
    [ "$(cat "$controller/pwm${channel}_enable")" = 2 ] || {
        echo "BIOS handoff not verified; leaving driver loaded" >&2
        exit 1
    }
fi
echo "BIOS handoff completed, or controller remained readonly"
