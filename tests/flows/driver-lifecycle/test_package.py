# SPDX-License-Identifier: GPL-2.0-or-later
"""Single-deb delivery contract, including its real maintainer entry points."""
import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]


class PackageContract(unittest.TestCase):
    def test_one_package_contains_runtime_services_tools_and_corresponding_source(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = pathlib.Path(temp)
            result = subprocess.run(["sh", str(ROOT / "tools/build-deb.sh"), str(temp / "build")],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            packages = list((temp / "build").glob("*.deb"))
            self.assertEqual(len(packages), 1)
            payload = temp / "payload"
            subprocess.run(["dpkg-deb", "-x", str(packages[0]), str(payload)], check=True)
            required = [
                "usr/local/libexec/asrock-nct6686/driver-service.py",
                "usr/local/libexec/asrock-nct6686/restore-bios.sh",
                "usr/local/libexec/asrock-nct6686/stop-driver.sh",
                "etc/systemd/system/asrock-nct6686.service",
                "etc/systemd/system/coolercontrold.service.d/asrock-nct6686.conf",
                "usr/src/asrock-nct6686-fanctl-0.2.0/src/fan_control.c",
                "usr/src/asrock-nct6686-fanctl-0.2.0/tools/driver-service.py",
                "usr/src/asrock-nct6686-fanctl-0.2.0/LICENSE",
            ]
            for relative in required:
                self.assertTrue((payload / relative).is_file(), relative)
            self.assertTrue(os.access(payload / required[0], os.X_OK))
            self.assertIn("driver-service.py start", (payload / required[3]).read_text())
            self.assertNotIn("identify_once=1", (payload / required[3]).read_text())

    def test_reinstall_rebuilds_same_version_and_failed_build_does_not_enable_services(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = pathlib.Path(directory)
            subprocess.run(["sh", str(ROOT / "tools/build-deb.sh"), str(temp / "build")],
                           cwd=ROOT, check=True, capture_output=True, timeout=60)
            package = next((temp / "build").glob("*.deb"))
            control = temp / "control"
            subprocess.run(["dpkg-deb", "-e", str(package), str(control)], check=True)
            commands = temp / "commands"
            commands.mkdir()
            log = temp / "calls"
            program = """#!/usr/bin/env python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ["CALL_LOG"], "a") as stream:
    stream.write(json.dumps([name] + sys.argv[1:]) + "\\n")
if name == "dkms" and sys.argv[1] == "status":
    print("asrock-nct6686-fanctl/0.2.0, test-kernel, x86_64: installed")
if name == "dkms" and sys.argv[1] == "build" and os.environ.get("FAIL_BUILD") == "1":
    sys.exit(43)
"""
            for name in ("dkms", "systemctl", "python3"):
                path = commands / name
                # Absolute interpreter avoids the fake python3 recursively launching itself.
                path.write_text(program.replace("#!/usr/bin/env python3", "#!" + os.sys.executable))
                path.chmod(0o755)
            env = dict(os.environ, PATH=str(commands) + ":" + os.environ["PATH"], CALL_LOG=str(log))
            result = subprocess.run(["sh", str(control / "postinst"), "configure"],
                                    env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [__import__("json").loads(line) for line in log.read_text().splitlines()]
            self.assertTrue(any(call[:2] == ["dkms", "build"] and "--force" in call for call in calls))
            self.assertTrue(any(call[:2] == ["dkms", "install"] and "--force" in call for call in calls))
            self.assertFalse(any(call[:2] in (["systemctl", "start"], ["systemctl", "enable"]) and "--now" in call for call in calls))
            log.unlink()
            result = subprocess.run(["sh", str(control / "postinst"), "configure"],
                                    env=dict(env, FAIL_BUILD="1"), capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 43)
            calls = [__import__("json").loads(line) for line in log.read_text().splitlines()]
            self.assertFalse(any(call[0] in ("systemctl", "python3") or call[:2] == ["dkms", "install"] for call in calls))


if __name__ == "__main__":
    unittest.main()
