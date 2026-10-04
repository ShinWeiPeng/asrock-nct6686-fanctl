# SPDX-License-Identifier: GPL-2.0-or-later
"""Public service lifecycle contracts against an isolated Linux filesystem."""
import json
import importlib.util
import pathlib
import subprocess
import tempfile
import shutil
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("driver_service", ROOT / "tools/driver-service.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class FakeHost(service.LocalHost):
    def __init__(self, root):
        super().__init__(root)
        self.calls = []
        self.recovery_fails = False
        self.cooler_active = True
        self.fail_control_load = False
        self.fail_backup = False
        self.driver_active = False
        self.fail_cooler_start_once = False
        for name, text in {
            "/sys/class/dmi/id/board_vendor": "ASRock",
            "/sys/class/dmi/id/board_name": "A620AI WiFi",
        }.items():
            self.path(name).parent.mkdir(parents=True, exist_ok=True)
            self.path(name).write_text(text)

    def write(self, name, value):
        if name.endswith("/restore_bios"):
            if self.recovery_fails:
                raise RuntimeError("Injected BIOS recovery failure")
            h = self.controller()
            self.path(h + "/control_status").write_text(
                "channel=4 writable=1 inverted=1 tach=unavailable handoff_pending=0")
            self.path(h + "/pwm4_enable").write_text("2")
        else:
            super().write(name, value)

    def run(self, argv, check=True):
        self.calls.append(argv)
        if argv == ["/usr/local/libexec/asrock-nct6686/backup.sh"]:
            if self.fail_backup:
                raise RuntimeError("Injected backup failure")
            directory = self.path("/var/lib/asrock-nct6686-backup.contract")
            directory.mkdir(parents=True, mode=0o700, exist_ok=True)
            (directory / "previous.json").write_text(self.read(service.CONFIG) if self.exists(service.CONFIG) else "null")
            return str(directory)
        if argv == ["uname", "-r"]:
            return "7.0.14-11-pve"
        if argv == ["modinfo", "-F", "version", "asrock_nct6686"]:
            return "0.2.0"
        if argv[0] == "systemctl":
            action, unit = argv[1:]
            if unit == "coolercontrold":
                if action == "is-active":
                    return "active" if self.cooler_active else None
                if action == "start" and self.fail_cooler_start_once:
                    self.fail_cooler_start_once = False
                    self.used = 65536
                    raise RuntimeError("Injected CoolerControl capture failure")
                if action == "start" and self.used >= 65536:
                    raise RuntimeError("Recovery capture budget was not reset")
                self.cooler_active = action == "start"
            elif unit == "asrock-nct6686":
                manager = service.DriverService(self)
                if action == "stop":
                    if self.driver_active or self.exists("/sys/module/asrock_nct6686"):
                        manager.stop()
                    self.driver_active = False
                elif not self.driver_active:
                    manager.start()
                    self.driver_active = True
            return ""
        if argv[:2] == ["modprobe", "-r"]:
            shutil.rmtree(self.path("/sys/module/" + argv[2]), ignore_errors=True)
            if argv[2] == "asrock_nct6686":
                shutil.rmtree(self.path("/sys/class/hwmon/hwmon5"))
            return ""
        if argv[:2] == ["modprobe", "nct6683"]:
            self.path("/sys/module/nct6683").mkdir(parents=True, exist_ok=True)
            return ""
        if argv[0] == "modprobe":
            if "enable_control=1" in argv and self.fail_control_load:
                raise RuntimeError("Injected control module load failure")
            self.path("/sys/module/asrock_nct6686").mkdir(parents=True)
            self.path("/sys/module/asrock_nct6686/version").write_text("0.2.0")
            self.path("/sys/module/asrock_nct6686/parameters").mkdir(exist_ok=True)
            self.path("/sys/module/asrock_nct6686/parameters/identify_once").write_text("N")
            h = self.path("/sys/class/hwmon/hwmon5")
            h.mkdir(parents=True)
            for name, text in {
                "control_status": "channel=0 writable=0 inverted=0 tach=unavailable handoff_pending=0",
                "pwm4": "165", "pwm4_enable": "2", "restore_bios": "",
            }.items():
                (h / name).write_text(text)
            if "enable_control=1" in argv:
                (h / "control_status").write_text(
                    "channel=4 writable=1 inverted=1 tach=unavailable handoff_pending=0")
            return ""
        raise AssertionError("Unexpected external operation: " + repr(argv))


class ServiceContract(unittest.TestCase):
    def test_default_start_preserves_bios_and_does_not_enable_control(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            self.assertEqual(host.read("/sys/class/hwmon/hwmon5/pwm4"), "165")
            self.assertEqual(host.read("/sys/class/hwmon/hwmon5/pwm4_enable"), "2")
            self.assertEqual(host.calls[-1], [
                "modprobe", "asrock_nct6686", "identify_once=0", "enable_control=0",
                "cha_fan_channel=0", "channel_verified=0", "polarity_verified=0", "invert_pwm=0",
            ])

    def test_failed_bios_recovery_prevents_module_unload(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            h = host.controller()
            host.path(h + "/control_status").write_text(
                "channel=4 writable=1 inverted=1 tach=unavailable handoff_pending=1")
            host.path(h + "/pwm4_enable").write_text("1")
            host.recovery_fails = True
            with self.assertRaises(RuntimeError):
                manager.stop()
            self.assertNotIn(["modprobe", "-r", "asrock_nct6686"], host.calls)
            self.assertEqual(host.read(h + "/pwm4_enable"), "1")

    def test_explicit_verified_configuration_enables_only_channel_four_with_inverse_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            config = host.path(service.CONFIG)
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "enabled": True, "channel": 4, "invert": True,
                "verification_run": "0123456789abcdef0123456789abcdef",
                "verified_kernel": "7.0.14-11-pve",
            }))
            config.chmod(0o600)
            service.DriverService(host).start()
            self.assertEqual(host.calls[-1], [
                "modprobe", "asrock_nct6686", "identify_once=0", "enable_control=1",
                "cha_fan_channel=4", "channel_verified=1", "polarity_verified=1", "invert_pwm=1",
            ])

    def test_enable_stops_consumers_before_switch_and_never_requests_identification(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            manager.enable(4, True, "0123456789abcdef0123456789abcdef")
            stop_cc = host.calls.index(["systemctl", "stop", "coolercontrold"])
            stop_driver = host.calls.index(["systemctl", "stop", "asrock-nct6686"])
            start_driver = host.calls.index(["systemctl", "start", "asrock-nct6686"])
            start_cc = host.calls.index(["systemctl", "start", "coolercontrold"])
            self.assertLess(stop_cc, stop_driver)
            self.assertLess(stop_driver, start_driver)
            self.assertLess(start_driver, start_cc)
            self.assertTrue(host.cooler_active)
            self.assertNotIn("identify_once=1", [a for call in host.calls for a in call])
            self.assertEqual(manager.status()[1]["channel"], "4")

    def test_existing_bound_wrong_channel_is_rejected_without_reloading(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            config = host.path(service.CONFIG)
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "enabled": True, "channel": 4, "invert": True,
                "verification_run": "0123456789abcdef0123456789abcdef",
                "verified_kernel": "7.0.14-11-pve",
            }))
            config.chmod(0o600)
            host.path(host.controller() + "/control_status").write_text(
                "channel=2 writable=1 inverted=1 tach=unavailable handoff_pending=0")
            before = len([a for a in host.calls if a[0] == "modprobe"])
            with self.assertRaises(RuntimeError):
                manager.start()
            self.assertEqual(before, len([a for a in host.calls if a[0] == "modprobe"]))

    def test_failed_control_load_restores_previous_readonly_service_and_consumer(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            host.fail_control_load = True
            with self.assertRaises(RuntimeError):
                manager.enable(4, True, "0123456789abcdef0123456789abcdef")
            self.assertEqual(manager.status()[1]["writable"], "0")
            self.assertTrue(host.cooler_active)
            self.assertFalse(host.exists(service.CONFIG))

    def test_control_stop_recovers_bios_before_returning_stock_driver(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            h = host.controller()
            host.path(h + "/control_status").write_text(
                "channel=4 writable=1 inverted=1 tach=unavailable handoff_pending=1")
            host.path(h + "/pwm4_enable").write_text("1")
            manager.stop()
            self.assertFalse(host.exists("/sys/module/asrock_nct6686"))
            self.assertTrue(host.exists("/sys/module/nct6683"))

    def test_unknown_kernel_configuration_falls_back_to_readonly(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            config = host.path(service.CONFIG)
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "enabled": True, "channel": 4, "invert": True,
                "verification_run": "0123456789abcdef0123456789abcdef",
                "verified_kernel": "untested-kernel",
            }))
            config.chmod(0o600)
            manager = service.DriverService(host)
            manager.start()
            self.assertEqual(manager.status()[1]["writable"], "0")
            self.assertIn("enable_control=0", host.calls[-1])

    def test_insecure_configuration_is_rejected_before_module_load(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            config = host.path(service.CONFIG)
            config.parent.mkdir(parents=True)
            config.write_text("{}")
            config.chmod(0o644)
            with self.assertRaises(RuntimeError):
                service.DriverService(host).start()
            self.assertFalse(any(call[0] == "modprobe" for call in host.calls))

    def test_readonly_start_is_idempotent_and_invalid_verification_has_no_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            count = len(host.calls)
            manager.start()
            self.assertEqual(host.calls[count:], [["modinfo", "-F", "version", "asrock_nct6686"]])
            with self.assertRaises(RuntimeError):
                manager.enable(4, True, "unverified")
            self.assertFalse(host.exists(service.CONFIG))

    def test_transition_creates_restore_point_before_stopping_consumers(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            manager.start()
            manager.enable(4, True, "0123456789abcdef0123456789abcdef")
            self.assertTrue(host.exists("/var/lib/asrock-nct6686-backup.contract/previous.json"))
            backup = host.calls.index(["/usr/local/libexec/asrock-nct6686/backup.sh"])
            stop = host.calls.index(["systemctl", "stop", "coolercontrold"])
            self.assertLess(backup, stop)
            host.fail_backup = True
            previous = manager.configuration()
            count = len(host.calls)
            with self.assertRaises(RuntimeError):
                manager.disable()
            self.assertTrue(host.cooler_active)
            self.assertEqual(manager.configuration(), previous)
            self.assertFalse(any(a[:2] == ["systemctl", "stop"] for a in host.calls[count:]))

    def test_failed_consumer_start_restarts_previous_driver_with_fresh_recovery_budget(self):
        with tempfile.TemporaryDirectory() as temp:
            host = FakeHost(pathlib.Path(temp))
            manager = service.DriverService(host)
            host.run(["systemctl", "start", "asrock-nct6686"])
            host.fail_cooler_start_once = True
            with self.assertRaisesRegex(RuntimeError, "previous state restored"):
                manager.enable(4, True, "0123456789abcdef0123456789abcdef")
            self.assertTrue(host.driver_active)
            self.assertTrue(host.cooler_active)
            self.assertEqual(manager.status()[1]["writable"], "0")
            self.assertFalse(host.exists(service.CONFIG))


if __name__ == "__main__":
    unittest.main()
