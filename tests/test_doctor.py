import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import doctor

def probe(text="", code=0):
    return {"ok": code == 0, "code": code, "stdout": text, "output": text, "command": "fake"}

def rows_ok():
    return [doctor.finding(k, "ok", n + " fine") for k, n in doctor.CHECKS]

class Checks(unittest.TestCase):
    def test_failed_service_is_named_in_plain_words(self):
        run = lambda args, **kw: probe("backup.service loaded failed failed Backup" if "--user" not in args else "")
        row = doctor.Probes(run).services()
        self.assertEqual(row["state"], "bad")
        self.assertIn("backup", row["title"])
        self.assertTrue(row["advice"])

    def test_services_unreadable_is_not_a_problem(self):
        row = doctor.Probes(lambda *a, **kw: probe("Failed to connect to bus", 1)).services()
        self.assertEqual(row["state"], "unknown")
        self.assertTrue(row["title"].startswith("Couldn't check"))

    def test_temperature_uses_each_sensors_own_limits(self):
        tree = {"k10temp-pci-00c3": {"Tctl": {"temp1_input": 88}},
                "nvme-pci-0500": {"Composite": {"temp1_input": 82, "temp1_crit": 84.85}}}
        row = doctor.Probes(lambda *a, **kw: probe(json.dumps(tree))).temperature()
        self.assertEqual(row["state"], "warn")   # the NVMe is near its limit; the Ryzen at 88 is normal boost
        tree["nvme-pci-0500"]["Composite"]["temp1_input"] = 50
        self.assertEqual(doctor.Probes(lambda *a, **kw: probe(json.dumps(tree))).temperature()["state"], "ok")

    def test_no_route_means_offline(self):
        run = lambda args, **kw: probe("[]")
        row = doctor.Probes(run).network()
        self.assertEqual((row["state"], row["signature"]), ("bad", "offline"))

    def test_dns_failure_is_a_warning(self):
        run = lambda args, **kw: probe('[{"dst":"default"}]') if args[0] == "ip" else probe("", 2)
        self.assertEqual(doctor.Probes(run).network()["state"], "warn")

    def test_wifi_off_only_matters_without_a_cable(self):
        def run(args, **kw):
            if args[0] == "nmcli":
                return probe("enabled:disabled")
            return probe('[{"dst":"default"}]')
        self.assertEqual(doctor.Probes(run).wifi()["state"], "ok")
        run2 = lambda args, **kw: probe("enabled:disabled") if args[0] == "nmcli" else probe("[]")
        self.assertEqual(doctor.Probes(run2).wifi()["state"], "warn")

    def test_failing_drive_says_back_up(self):
        def run(args, **kw):
            if args[0] == "lsblk":
                return probe(json.dumps({"blockdevices": [{"name": "/dev/sda", "type": "disk", "model": "X"}]}))
            return probe(json.dumps({"smart_status": {"passed": False}}), 8)
        row = doctor.Probes(run).drives()
        self.assertEqual(row["state"], "bad")
        self.assertIn("Back up", row["advice"])

    def test_missing_smartctl_is_not_checked(self):
        def run(args, **kw):
            if args[0] == "lsblk":
                return probe(json.dumps({"blockdevices": [{"name": "/dev/sda", "type": "disk"}]}))
            return probe("smartctl is not installed.", 127)
        self.assertEqual(doctor.Probes(run).drives()["state"], "unknown")

    def test_a_broken_probe_never_breaks_the_scan(self):
        class Boom(doctor.Probes):
            def memory(self):
                raise RuntimeError("kaboom")
        self.assertEqual(doctor.run_check(Boom(), "memory")["state"], "unknown")

class Verdict(unittest.TestCase):
    def test_unknown_and_skipped_never_block_green(self):
        rows = rows_ok()
        rows[2] = doctor.not_checked("drives", "drive health")
        rows[4] = doctor.finding("battery", "skipped", "No battery")
        self.assertEqual(doctor.verdict(rows), {"state": "ok", "count": 0})

    def test_problems_color_and_count(self):
        rows = rows_ok()
        rows[0] = doctor.finding("storage", "warn", "Your disk is 92% full", level=90, signature="/")
        self.assertEqual(doctor.verdict(rows), {"state": "warn", "count": 1})
        rows[1] = doctor.finding("services", "bad", "A background service failed", level=1, signature="x.service")
        self.assertEqual(doctor.verdict(rows), {"state": "bad", "count": 2})

class Flow(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.h = doctor.History(Path(self.dir.name) / "d.db")

    def tearDown(self):
        self.h.close()
        self.dir.cleanup()

    def disk(self, pct):
        rows = rows_ok()
        state = "bad" if pct >= 95 else "warn" if pct >= 90 else "ok"
        rows[0] = doctor.finding("storage", state, f"Your disk is {pct}% full", level=pct // 5 * 5, signature="/")
        return rows

    def test_its_fine_turns_green_until_it_gets_worse(self):
        self.h.save(self.disk(91))
        self.h.call_fine("storage")
        rows, _ = self.h.save(self.disk(92))
        self.assertEqual(doctor.verdict(rows)["state"], "ok")
        self.assertTrue(rows[0]["dismissed"])
        rows, _ = self.h.save(self.disk(96))
        self.assertEqual(doctor.verdict(rows)["state"], "bad")
        self.assertTrue(rows[0]["came_back"])

    def test_its_fine_is_forgotten_once_the_problem_clears(self):
        self.h.save(self.disk(91))
        self.h.call_fine("storage")
        self.h.save(self.disk(70))
        rows, _ = self.h.save(self.disk(91))
        self.assertEqual(doctor.verdict(rows)["count"], 1)

    def test_a_different_failed_service_comes_back(self):
        rows = rows_ok()
        rows[1] = doctor.finding("services", "bad", "A background service failed: a", level=1, signature="a.service")
        self.h.save(rows)
        self.h.call_fine("services")
        rows = rows_ok()
        rows[1] = doctor.finding("services", "bad", "A background service failed: b", level=1, signature="b.service")
        rows, _ = self.h.save(rows)
        self.assertEqual(doctor.verdict(rows)["count"], 1)

    def test_fix_counts_only_when_doctor_measures_it_healthy(self):
        rows = self.disk(92)
        self.h.save(rows)
        fix = self.h.open_fix(rows[0], "claude")
        _, updates = self.h.save([self.disk(92)[0]], recheck=True)
        self.assertEqual(updates[0]["status"], "not_fixed")
        _, updates = self.h.save([self.disk(60)[0]], recheck=True)
        self.assertEqual((updates[0]["id"], updates[0]["status"]), (fix, "fixed"))
        self.assertEqual(self.h.fixes()[0]["status"], "fixed")

    def test_recheck_keeps_the_other_results(self):
        self.h.save(self.disk(92))
        rows, _ = self.h.save([doctor.finding("memory", "ok", "Memory is fine")], recheck=True)
        self.assertEqual(len(rows), len(doctor.CHECKS))
        self.assertEqual(rows[0]["state"], "warn")

    def test_database_is_private(self):
        self.assertEqual(os.stat(self.h.path).st_mode & 0o777, 0o600)

class Cli(unittest.TestCase):
    def run_cli(self, *args, env=None):
        p = subprocess.run([sys.executable, str(ROOT / "doctor.py"), *args, "--database", self.db], capture_output=True, text=True,
                           env={**os.environ, **(env or {})}, timeout=60)
        return p.returncode, [json.loads(l) for l in p.stdout.splitlines() if l.strip()]

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = str(Path(self.dir.name) / "d.db")

    def tearDown(self):
        self.dir.cleanup()

    def test_scan_emits_eight_checks_and_a_verdict(self):
        code, events = self.run_cli("scan")
        self.assertEqual(code, 0)
        state = events[-1]
        self.assertEqual(state["type"], "state")
        self.assertEqual(len(state["rows"]), 8)
        self.assertIn(state["verdict"]["state"], ("ok", "warn", "bad"))

    def test_unknown_check_is_refused(self):
        code, events = self.run_cli("recheck", "journal")
        self.assertEqual((code, events[0]["type"]), (2, "error"))

    def test_fix_briefing_carries_the_problem_and_the_recheck(self):
        h = doctor.History(self.db)
        rows = rows_ok()
        rows[1] = doctor.finding("services", "bad", "A background service failed: backup", "Restart it.", "system: backup.service failed",
                                 "systemctl --failed", level=1, signature="backup.service")
        h.save(rows)
        h.close()
        code, events = self.run_cli("fix", "services", "--no-launch", "--agent", "claude")
        self.assertEqual(code, 0)
        prompt = events[0]["prompt"]
        for part in ("backup", "systemctl --failed", "recheck services", "Ask me before", "not the measurement"):
            self.assertIn(part, prompt)
        self.assertEqual(events[1]["fixes"][0]["status"], "working")

    def test_nothing_to_fix_when_healthy(self):
        h = doctor.History(self.db)
        h.save(rows_ok())
        h.close()
        code, events = self.run_cli("fix", "storage", "--no-launch", "--agent", "x")
        self.assertEqual((code, events[0]["type"]), (3, "error"))

if __name__ == "__main__":
    unittest.main()
