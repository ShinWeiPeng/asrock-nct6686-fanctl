#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Guarded service lifecycle; physical verification remains an administrator claim."""
import argparse
import json
import os
import pathlib
import re
import selectors
import subprocess
import time
import tempfile

VERSION = "0.2.0"
CONFIG = "/var/lib/asrock-nct6686/control.json"


class LocalHost:
    """Filesystem and process boundary, replaced by an isolated host in contract tests."""
    def __init__(self, root=pathlib.Path("/")):
        self.root = root
        self.used = 0

    def begin_recovery(self):
        """Give rollback a separate bounded capture allowance."""
        self.used = 0

    def path(self, name):
        return self.root / name.lstrip("/")

    def read(self, name):
        return self.path(name).read_text().strip()

    def write(self, name, value):
        self.path(name).write_text(value + "\n")

    def exists(self, name):
        return self.path(name).exists()

    def controller(self):
        found = [p for p in self.path("/sys/class/hwmon").glob("hwmon*")
                 if (p / "control_status").exists()]
        if len(found) != 1:
            raise RuntimeError("Expected exactly one guarded controller")
        return "/" + str(found[0].relative_to(self.root))

    def save_configuration(self, value):
        path = self.path(CONFIG)
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if path.parent.stat().st_uid != os.geteuid() or path.parent.stat().st_mode & 0o022:
            raise RuntimeError("Unsafe control configuration directory")
        if value is None:
            if path.exists():
                path.unlink()
            return
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as file:
            temporary = pathlib.Path(file.name)
            json.dump(value, file, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def run(self, argv, check=True):
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = bytearray()
        deadline = time.monotonic() + 20
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        error = None
        try:
            while selector.get_map():
                if time.monotonic() >= deadline:
                    error = "Command timed out"
                    break
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    self.used += len(chunk)
                    if self.used > 65536:
                        error = "Command capture exceeded 64 KiB"
                        break
                    output.extend(chunk)
                if error:
                    break
        finally:
            selector.close()
            if error:
                process.kill()
            process.wait(timeout=5)
            process.stdout.close()
        if error or (check and process.returncode):
            raise RuntimeError(str(argv) + ": " + (error or output.decode(errors="replace")[-2000:]))
        return None if process.returncode else output.decode(errors="replace").strip()


class DriverService:
    def __init__(self, host):
        self.host = host

    def status(self):
        h = self.host.controller()
        fields = dict(item.split("=", 1) for item in self.host.read(h + "/control_status").split())
        for key in ("writable", "inverted"):
            if fields.get(key) not in ("0", "1"):
                raise RuntimeError("Unknown controller status")
        return h, fields

    def configuration(self):
        host = self.host
        if not host.exists(CONFIG):
            return None
        path = host.path(CONFIG)
        stat = path.stat()
        if path.is_symlink() or stat.st_uid != os.geteuid() or stat.st_mode & 0o777 != 0o600:
            raise RuntimeError("Control configuration must be owned by the operator and mode 0600")
        if stat.st_size > 4096:
            raise RuntimeError("Control configuration exceeds 4 KiB")
        value = json.loads(host.read(CONFIG))
        if set(value) != {"enabled", "channel", "invert", "verification_run", "verified_kernel"}:
            raise RuntimeError("Invalid control configuration fields")
        if type(value["enabled"]) is not bool or type(value["invert"]) is not bool:
            raise RuntimeError("Invalid control configuration flags")
        if type(value["channel"]) is not int or not 1 <= value["channel"] <= 8:
            raise RuntimeError("Invalid verified channel")
        if not isinstance(value["verification_run"], str) or not re.fullmatch(
                "[0-9a-f]{32}", value["verification_run"]):
            raise RuntimeError("A fixed physical verification run is required")
        if not isinstance(value["verified_kernel"], str) or not value["verified_kernel"]:
            raise RuntimeError("Verified kernel identity is required")
        return value

    def start(self):
        host = self.host
        if host.read("/sys/class/dmi/id/board_vendor") != "ASRock" or host.read(
                "/sys/class/dmi/id/board_name") != "A620AI WiFi":
            raise RuntimeError("Unsupported board")
        if host.run(["modinfo", "-F", "version", "asrock_nct6686"]) != VERSION:
            raise RuntimeError("Unreviewed module version")
        config = self.configuration()
        enabled = bool(config and config["enabled"])
        if enabled and config["verified_kernel"] != host.run(["uname", "-r"]):
            print("Unverified kernel; retaining readonly BIOS operation")
            enabled = False
        channel = config["channel"] if enabled else 0
        inverted = int(config["invert"]) if enabled else 0
        params = ["identify_once=0", "enable_control=" + str(int(enabled)),
                  "cha_fan_channel=" + str(channel), "channel_verified=" + str(int(enabled)),
                  "polarity_verified=" + str(int(enabled)), "invert_pwm=" + str(inverted)]
        if host.exists("/sys/module/asrock_nct6686"):
            h, state = self.status()
            if state["writable"] != str(int(enabled)) or state.get("handoff_pending") != "0":
                raise RuntimeError("Existing controller requires explicit recovery/stop")
            if host.read("/sys/module/asrock_nct6686/parameters/identify_once") != "N":
                raise RuntimeError("Existing identification module is not a service instance")
            if host.read("/sys/module/asrock_nct6686/version") != VERSION:
                raise RuntimeError("Existing module version differs")
            if int(state.get("channel", "-1")) != channel or int(state["inverted"]) != inverted:
                raise RuntimeError("Existing channel/direction differs; stop explicitly")
            return
        had_stock = host.exists("/sys/module/nct6683")
        if had_stock:
            host.run(["modprobe", "-r", "nct6683"])
        try:
            host.run(["modprobe", "asrock_nct6686", *params])
            h, state = self.status()
            if state["writable"] != str(int(enabled)) or state.get("handoff_pending") != "0":
                raise RuntimeError("Startup permissions/recovery state not verified")
            if int(state.get("channel", "-1")) != channel or int(state["inverted"]) != inverted:
                raise RuntimeError("Startup channel/direction not verified")
        except Exception:
            if had_stock and not host.exists("/sys/module/asrock_nct6686"):
                host.run(["modprobe", "nct6683", "force=1"])
            raise

    def restore(self):
        host = self.host
        if not host.exists("/sys/module/asrock_nct6686"):
            return
        h, state = self.status()
        if state.get("handoff_pending") not in ("0", "1"):
            raise RuntimeError("Unknown recovery state; leave module bound")
        if state["handoff_pending"] == "1":
            host.write(h + "/restore_bios", "2")
            h, state = self.status()
            if state.get("handoff_pending") != "0":
                raise RuntimeError("Recovery incomplete; leave module bound")
        if state["writable"] == "1":
            channel = int(state.get("channel", "0"))
            if not 1 <= channel <= 8:
                raise RuntimeError("Invalid verified channel")
            enable = h + "/pwm" + str(channel) + "_enable"
            if host.read(enable) != "2":
                host.write(enable, "2")
            if host.read(enable) != "2":
                raise RuntimeError("BIOS handoff not verified; leave module bound")

    def stop(self):
        host = self.host
        self.restore()
        if host.exists("/sys/module/asrock_nct6686"):
            host.run(["modprobe", "-r", "asrock_nct6686"])
        if not host.exists("/sys/module/nct6683"):
            if host.read("/sys/class/dmi/id/board_vendor") == "ASRock" and host.read(
                    "/sys/class/dmi/id/board_name") == "A620AI WiFi":
                host.run(["modprobe", "nct6683", "force=1"])

    def switch(self, configuration):
        host = self.host
        previous = self.configuration()
        host.run(["/usr/local/libexec/asrock-nct6686/backup.sh"])
        cooler_was_active = host.run(["systemctl", "is-active", "coolercontrold"], check=False) == "active"
        changed = False
        try:
            if cooler_was_active:
                host.run(["systemctl", "stop", "coolercontrold"])
            host.run(["systemctl", "stop", "asrock-nct6686"])
            if host.exists("/sys/module/asrock_nct6686"):
                raise RuntimeError("Old driver remains bound; no configuration change")
            host.save_configuration(configuration)
            changed = True
            host.run(["systemctl", "start", "asrock-nct6686"])
            if cooler_was_active:
                host.run(["systemctl", "start", "coolercontrold"])
        except Exception as error:
            host.begin_recovery()
            try:
                if changed:
                    if cooler_was_active:
                        host.run(["systemctl", "stop", "coolercontrold"])
                    host.run(["systemctl", "stop", "asrock-nct6686"])
                    self.stop()
                    if host.exists("/sys/module/asrock_nct6686"):
                        raise RuntimeError("Driver remains bound; preserve current configuration")
                    host.save_configuration(previous)
                host.run(["systemctl", "start", "asrock-nct6686"])
                self.start()
                if cooler_was_active:
                    host.run(["systemctl", "start", "coolercontrold"])
            except Exception as recovery:
                raise RuntimeError(str(error) + "; rollback incomplete: " + str(recovery)) from error
            raise RuntimeError("Control transition failed and previous state restored: " + str(error)) from error

    def enable(self, channel, inverted, verification_run):
        if type(channel) is not int or not 1 <= channel <= 8 or type(inverted) is not bool:
            raise RuntimeError("A physically verified channel/direction is required")
        if not isinstance(verification_run, str) or not re.fullmatch("[0-9a-f]{32}", verification_run):
            raise RuntimeError("A fixed physical verification run is required")
        self.switch({"enabled": True, "channel": channel, "invert": inverted,
                     "verification_run": verification_run,
                     "verified_kernel": self.host.run(["uname", "-r"])})

    def disable(self):
        config = self.configuration()
        if config:
            config = dict(config, enabled=False)
        self.switch(config)

    def reset(self):
        config = self.configuration()
        if config:
            self.host.save_configuration(dict(config, enabled=False))


def main():
    if os.geteuid() != 0:
        raise SystemExit("Root is required")
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("start", "restore", "stop", "status", "enable", "disable", "reset"))
    parser.add_argument("--channel", type=int)
    parser.add_argument("--invert", action="store_true")
    parser.add_argument("--verification-run")
    args = parser.parse_args()
    manager = DriverService(LocalHost())
    try:
        if args.action == "enable":
            manager.enable(args.channel, args.invert, args.verification_run)
        elif args.action == "status":
            print(json.dumps(manager.status()[1], sort_keys=True))
        else:
            getattr(manager, args.action)()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
