#!/usr/bin/env python3
"""Bounded read-only Omarchy diagnostics, JSONL events and local history."""
from __future__ import annotations
import argparse
import concurrent.futures
import csv
import datetime as dt
import io
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import uuid

VERSION = "1.4.2"
SCHEMA = 1
STATES = {"ok", "warn", "bad", "unknown", "skipped"}
RETENTION = 7 * 86400
MAX_OUTPUT = 20000
STOP = threading.Event()
CHILDREN = set()

def stop_children(*_):
    STOP.set()
    for proc in list(CHILDREN):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None

class Runner:
    def __call__(self, args, timeout=5, allowed=(0,)):
        command = shlex.join(args)
        if STOP.is_set():
            return dict(ok=False, code=124, output="Scan cancelled.", command=command)
        if not shutil.which(args[0]):
            return dict(ok=False, code=127, output="Command is not installed.", command=command)
        try:
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                    start_new_session=True, env={**os.environ, "LC_ALL": "C", "SYSTEMD_COLORS": "0", "SYSTEMD_PAGER": "cat"})
                CHILDREN.add(proc)
                if STOP.is_set():
                    stop_children()
                try:
                    code = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                    return dict(ok=False, code=124, output=f"Timed out after {timeout:g} seconds.", command=command)
                finally:
                    CHILDREN.discard(proc)
                out.seek(0); err.seek(0)
                stdout = out.read(1024 * 1024).decode("utf-8", "replace").strip()
                stderr = err.read(MAX_OUTPUT).decode("utf-8", "replace").strip()
                text = stdout + ("\n" if stdout and stderr else "") + stderr
                return dict(ok=code in allowed, code=code, output=text[:MAX_OUTPUT], stdout=stdout,
                            truncated=len(text) > MAX_OUTPUT, command=command)
        except OSError as exc:
            return dict(ok=False, code=126, output=str(exc), command=command)

def result(key, domain, title, state, summary, evidence="", command="", metrics=None):
    assert state in STATES
    return dict(id=key, domain=domain, title=title, state=state, summary=summary,
                evidence=str(evidence)[:MAX_OUTPUT], command=command, metrics=metrics or {}, timestamp=time.time())

def unavailable(key, domain, title, probe):
    return result(key, domain, title, "unknown",
        "Timed out; no healthy result can be inferred." if probe.get("code") == 124 else "Check unavailable; no healthy result can be inferred.",
        probe.get("output", "No data returned."), probe.get("command", ""))

def verdict(rows, complete=True):
    counts = {s: sum(r["state"] == s for r in rows) for s in STATES}
    state = "bad" if counts["bad"] else "warn" if counts["warn"] else "unknown" if not complete or counts["unknown"] or not counts["ok"] else "ok"
    return state, counts

def sensor_inputs(tree):
    readings = []
    def walk(node, path):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if isinstance(value, dict):
                walk(value, path + [key])
            elif re.fullmatch(r"temp\d+_input", key):
                n = number(value)
                if n is not None and -30 <= n <= 150:
                    readings.append((" / ".join(path + [key]), n))
    walk(tree, [])
    return readings

# Error-priority journal lines that are fixed facts about the hardware, printed on every boot or
# connection, which no repair can remove. Kept deliberately narrow and exact; matches stay visible
# in the evidence as ignored, with the reason.
BENIGN_JOURNAL = (
    (r"virt/tdx: TDX not supported by the host platform", "CPU has no Intel TDX; the kernel reports this once per boot"),
    (r"nl80211: kernel reports: multicast RX registrations are not supported", "Wi-Fi driver capability notice on each connection"),
    (r"avdtp_connect_cb\(\) connect to [0-9A-Fa-f:]{17}: Host is down \(112\)", "a paired Bluetooth audio device was off or out of range when bluez tried to reconnect"),
    (r"ucsi_acpi USBC\d+:\d+: GET_CURRENT_CAM command failed", "USB-C controller firmware does not support this query"),
)

# Package sensors on CPUs that report no limits of their own. Ryzen mobile parts boost into the
# 90s by design (Tjmax 95-100°C), so a flat 85°C rule flags normal load as a problem.
CPU_LIMITS = (("k10temp", 95, 100), ("zenpower", 95, 100), ("coretemp", 95, 100))
DEFAULT_LIMITS = (85, 95)

def sensor_limits(tree):
    """(label, current, warn, critical, source) per sensor, using the hardware's own limits when it has them."""
    out = []
    for chip, features in (tree.items() if isinstance(tree, dict) else []):
        if not isinstance(features, dict):
            continue
        for feature, values in features.items():
            if not isinstance(values, dict):
                continue
            for key, raw in values.items():
                m = re.fullmatch(r"(temp\d+)_input", key)
                n = number(raw)
                if not m or n is None or not -30 <= n <= 150:
                    continue
                def limit(name):
                    v = number(values.get(f"{m.group(1)}_{name}"))
                    return v if v is not None and 40 <= v <= 130 else None
                crit = limit("crit")
                if crit is not None:
                    warn, source = crit - 5, f"sensor critical {crit:.0f}°C"
                else:
                    cpu = next((c for c in CPU_LIMITS if chip.startswith(c[0])), None)
                    high = limit("max")
                    if cpu:
                        warn, crit, source = cpu[1], cpu[2], f"{cpu[0]} package limit {cpu[2]}°C"
                    elif high is not None:
                        warn, crit, source = high, high + 10, f"sensor high {high:.0f}°C"
                    else:
                        (warn, crit), source = DEFAULT_LIMITS, "general limit"
                out.append((f"{chip} / {feature} / {key}", n, warn, crit, source))
    return out

def read_values(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        parts = line.replace(":", " ", 1).split()
        if len(parts) >= 2 and number(parts[1]) is not None:
            values[parts[0]] = float(parts[1])
    return values

def pressure(kind):
    try:
        m = re.search(r"^some avg10=([\d.]+)", Path(f"/proc/pressure/{kind}").read_text(), re.M)
        return number(m.group(1)) if m else None
    except OSError:
        return None

def clock(ts):
    return dt.datetime.fromtimestamp(ts).strftime("%H:%M") if dt.date.fromtimestamp(ts) == dt.date.today() else dt.datetime.fromtimestamp(ts).strftime("%b %d %H:%M")

class Probes:
    # Event checks count history (crashes, journal records). A crash cannot un-happen, so once a
    # finding is handed to an agent, everything up to that moment counts as reviewed and the check
    # reports only what happened afterwards. New events after a fix mean it did not hold.
    def __init__(self, run=None, since=None):
        self.run = run or Runner()
        self.since = since or {}

    def window(self, key):
        cutoff = self.since.get(key)
        return (["--since", "@%d" % int(cutoff)], f" since the hand-off at {clock(cutoff)}") if cutoff else ([], "")

    def services(self):
        outputs, failed, errors = [], [], []
        for scope, flags in [("System", []), ("User", ["--user"])]:
            p = self.run(["systemctl", *flags, "--failed", "--no-legend", "--plain", "--no-pager"])
            outputs.append(scope + ":\n" + (p["output"] or "No failed units."))
            if not p["ok"]:
                errors.append(scope)
            else:
                failed += [scope + ": " + line.strip() for line in p.get("stdout", p["output"]).splitlines() if line.strip()]
        state = "bad" if failed else "unknown" if errors else "ok"
        summary = f"{len(failed)} failed unit(s)." if failed else "No failed system or user units." if not errors else "Could not inspect " + ", ".join(errors).lower() + " units."
        if failed and errors:
            summary += " Incomplete coverage: " + ", ".join(errors) + "."
        return result("services", "system", "System & user services", state, summary, "\n\n".join(outputs),
                      "systemctl --failed; systemctl --user --failed", {"failed_units": len(failed), "unavailable_scopes": len(errors)})

    def journal(self):
        since, after = self.window("journal")
        p = self.run(["journalctl", "-b", *since, "-p", "3", "-n", "200", "--no-pager", "-o", "json"])
        if not p["ok"]:
            return unavailable("journal", "system", "Boot journal", p)
        entries = []
        for line in p.get("stdout", p["output"]).splitlines():
            if not line.strip() or line.startswith("--"):
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                return unavailable("journal", "system", "Boot journal", {**p, "output": "Could not parse the journal response."})
        ignored = []
        for e in list(entries):
            reason = next((why for pattern, why in BENIGN_JOURNAL if re.search(pattern, str(e.get("MESSAGE", "")))), None)
            if reason:
                ignored.append(f"{e.get('SYSLOG_IDENTIFIER', e.get('_COMM', 'journal'))}: {e.get('MESSAGE', '')}  [ignored: {reason}]")
                entries.remove(e)
        count = f"{len(entries)}+" if len(entries) >= 200 else str(len(entries))
        return result("journal", "system", "Boot journal", "warn" if entries else "ok",
            (f"{count} new high-priority record(s){after}; inspect context." if after else f"{count} high-priority record(s) this boot; inspect context.") if entries
            else (f"No new high-priority entries{after}." if after else "No high-priority entries in this boot."),
            "\n\n".join([str(e.get("SYSLOG_IDENTIFIER", e.get("_COMM", "journal"))) + ": " + str(e.get("MESSAGE", "")) for e in entries] + ignored),
            "journalctl -b " + " ".join(since + ["-p", "3", "-n", "200", "--no-pager"]), {"journal_entries": len(entries), "journal_ignored": len(ignored)})

    def memory(self):
        try:
            v = read_values("/proc/meminfo")
            total, available = v.get("MemTotal"), v.get("MemAvailable")
            if total is None or total <= 0 or available is None or not 0 <= available <= total:
                raise ValueError("Missing or invalid MemTotal / MemAvailable values.")
            used = (total - available) / total * 100
            st, sf = v.get("SwapTotal", 0), v.get("SwapFree", 0)
            if st < 0 or not 0 <= sf <= st:
                raise ValueError("Invalid swap values.")
            swap = (st - sf) / st * 100 if st else 0
            psi = pressure("memory")
            m = {"ram_available_gib": available / 1048576, "ram_used_pct": used, "ram_total_gib": total / 1048576, "swap_used_pct": swap}
            if psi is not None:
                m["memory_pressure"] = psi
            state = "bad" if used >= 97 and psi is not None and psi >= 20 else "warn" if used >= 92 or (psi is not None and psi >= 10) else "ok"
            return result("memory", "ram", "Memory headroom", state,
                f"{available / 1048576:.1f} GiB available · {used:.0f}% used · {swap:.0f}% swap used.",
                json.dumps(m, indent=2) + "\nSwap occupancy alone does not prove active memory pressure.", "free -h; cat /proc/pressure/memory", m)
        except (OSError, ValueError) as exc:
            return unavailable("memory", "ram", "Memory headroom", {"output": str(exc), "command": "cat /proc/meminfo"})

    def cpu(self):
        def sample():
            values = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
            if len(values) < 5:
                raise ValueError("Incomplete CPU counters.")
            return sum(values), values[3] + values[4]
        try:
            a = sample(); time.sleep(0.15); b = sample()
            elapsed = b[0] - a[0]
            if elapsed <= 0:
                raise ValueError("CPU counters did not advance.")
            load = max(0, min(100, 100 * (1 - (b[1] - a[1]) / elapsed)))
            psi = pressure("cpu")
            m = {"cpu_pct": load, "cpu_threads": os.cpu_count() or 1, "load_1m": os.getloadavg()[0]}
            if psi is not None:
                m["cpu_pressure"] = psi
            return result("cpu", "cpu", "Processor activity", "warn" if psi is not None and psi >= 25 else "ok",
                f"{load:.0f}% busy across {os.cpu_count()} logical processors.",
                json.dumps(m, indent=2) + "\nA brief load spike alone is not a fault. Pressure measures work waiting for CPU time.",
                "cat /proc/pressure/cpu; uptime", m)
        except (OSError, ValueError) as exc:
            return unavailable("cpu", "cpu", "Processor activity", {"output": str(exc), "command": "cat /proc/stat"})

    def temperature(self):
        p = self.run(["sensors", "-j"])
        values = []
        if p["ok"]:
            try:
                values = sensor_limits(json.loads(p.get("stdout", p["output"])))
            except (ValueError, TypeError):
                pass
        if not values:
            for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
                try:
                    n = number(path.read_text().strip())
                    if n is not None and -30000 <= n <= 150000:
                        values.append(((path.parent / "type").read_text().strip(), n / 1000, *DEFAULT_LIMITS, "general limit"))
                except OSError:
                    pass
        if not values:
            return unavailable("temperature", "cpu", "Thermal sensors", p)
        rank = lambda v: 2 if v[1] >= v[3] else 1 if v[1] >= v[2] else 0
        worst = max(values, key=lambda v: (rank(v), v[1] - v[2]))
        hottest = max(values, key=lambda v: v[1])
        state = ("ok", "warn", "bad")[rank(worst)]
        summary = (f"{worst[0].split(' / ')[0]} at {worst[1]:.1f}°C, past its warning point of {worst[2]:.0f}°C ({worst[4]})." if state != "ok"
            else f"Highest current sensor: {hottest[1]:.1f}°C, within its limits.")
        return result("temperature", "cpu", "Thermal sensors", state, summary,
            "\n".join(f"{label}: {value:.1f}°C (warn {warn:.0f}, critical {crit:.0f}; {source})" for label, value, warn, crit, source in values)
            + "\nEach sensor is judged against its own hardware limits when it reports them.", "sensors -j", {"temperature_c": hottest[1]})

    def storage(self):
        try:
            d = shutil.disk_usage("/"); pct = d.used / d.total * 100
            m = {"disk_used_pct": pct, "disk_free_gib": d.free / 2**30, "disk_total_gib": d.total / 2**30}
            psi = pressure("io")
            if psi is not None:
                m["io_pressure"] = psi
            return result("storage", "disk", "Root filesystem", "bad" if pct >= 95 else "warn" if pct >= 85 else "ok",
                f"{pct:.0f}% used · {d.free / 2**30:.1f} GiB available on /.", json.dumps(m, indent=2), "df -h /; findmnt /", m)
        except (OSError, ZeroDivisionError) as exc:
            return unavailable("storage", "disk", "Root filesystem", {"output": str(exc), "command": "df -h /"})

    def drives(self):
        p = self.run(["lsblk", "-J", "-d", "-p", "-o", "NAME,TYPE,MODEL"])
        if not p["ok"]:
            return unavailable("drives", "disk", "Physical drive health", p)
        try:
            devices = [d for d in json.loads(p.get("stdout", p["output"])).get("blockdevices", [])
                       if d.get("type") == "disk" and not re.match(r"/dev/(zram|loop|ram)\d", d.get("name", ""))]
        except (ValueError, AttributeError):
            return unavailable("drives", "disk", "Physical drive health", {**p, "output": "Invalid lsblk JSON."})
        if not devices:
            return result("drives", "disk", "Physical drive health", "skipped", "No physical disks are exposed to this session.", command="lsblk")
        details, failed, unknown = [], [], []
        for device in devices[:16]:
            name = device.get("name", "")
            if not re.fullmatch(r"/dev/[A-Za-z0-9_.-]+", name):
                unknown.append(name); continue
            q = self.run(["smartctl", "-j", "-H", name], timeout=4, allowed=tuple(range(256)))
            # The kernel refuses the NVMe SMART log to non-root even with device access, so retry once
            # through sudo -n: it uses an existing passwordless rule or fails at once, never prompting.
            if q["code"] & 2 and "Permission denied" in q["output"]:
                s = self.run(["sudo", "-n", "smartctl", "-j", "-H", name], timeout=6, allowed=tuple(range(256)))
                if s["code"] & 1:
                    q["output"] += "\nsudo -n smartctl: " + (s["output"].strip().splitlines() or ["refused"])[-1]
                else:
                    q = s
            try:
                data = json.loads(q.get("stdout", q["output"]))
            except (ValueError, TypeError):
                data = {}
            passed = data.get("smart_status", {}).get("passed")
            details.append(name + " " + str(device.get("model") or "") + "\n" + q["output"])
            # Bits 0..2 represent command/device failures in smartctl's exit bitmask.
            if not q["ok"] or q["code"] & 7 or not isinstance(passed, bool):
                unknown.append(name)
            elif not passed:
                failed.append(name)
        if len(devices) > 16:
            unknown.append("drives beyond the 16-drive limit")
        summary = "SMART failure: " + ", ".join(failed) if failed else "Drive health unavailable: " + ", ".join(unknown) if unknown else f"SMART passed on all {len(devices)} inspected physical drives."
        if failed and unknown:
            summary += "; unavailable: " + ", ".join(unknown)
        return result("drives", "disk", "Physical drive health", "bad" if failed else "unknown" if unknown else "ok", summary,
            "\n\n".join(details), "lsblk -o NAME,TYPE,MODEL,MOUNTPOINTS", {"drives_checked": len(devices), "drives_unknown": len(unknown)})

    def gpu(self):
        p = self.run(["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,driver_version", "--format=csv,noheader,nounits"], timeout=4)
        if p["ok"]:
            rows = list(csv.reader(io.StringIO(p.get("stdout", p["output"]))))
            readings = []
            for row in rows:
                if len(row) != 6:
                    continue
                vals = [number(x.strip()) for x in row[1:5]]
                if any(v is None for v in vals) or not 0 <= vals[0] <= 150 or not 0 <= vals[1] <= 100 or vals[3] <= 0 or not 0 <= vals[2] <= vals[3]:
                    continue
                readings.append((row[0].strip(), *vals, row[5].strip()))
            if not readings or len(readings) != len(rows):
                return unavailable("gpu", "gpu", "Graphics & driver", {**p, "output": "Driver returned unavailable or invalid measurements.\n" + p["output"]})
            temp = max(r[1] for r in readings)
            m = {"gpu_temperature_c": temp, "gpu_pct": max(r[2] for r in readings), "vram_used_pct": max(r[3] / r[4] * 100 for r in readings)}
            return result("gpu", "gpu", "Graphics & driver", "bad" if temp >= 90 else "warn" if temp >= 82 else "ok",
                f"{len(readings)} GPU(s) responding · highest {temp:.0f}°C.", p["output"], "nvidia-smi", m)
        for path in Path("/sys/class/drm").glob("card[0-9]*/device/gpu_busy_percent"):
            try:
                busy = number(path.read_text().strip())
                if busy is not None and 0 <= busy <= 100:
                    return result("gpu", "gpu", "Graphics & driver", "ok", f"DRM GPU reports {busy:.0f}% activity.", str(path), "lspci -k", {"gpu_pct": busy})
            except OSError:
                pass
        # Not every DRM driver exports gpu_busy_percent (xe and AMD do not on this kernel),
        # but all expose the device power state. D0 means the GPU is powered and active -
        # a valid "the graphics stack answers" signal; any other state is reported as
        # inactive and is never treated as healthy.
        active, inactive = [], []
        for path in sorted(Path("/sys/class/drm").glob("card[0-9]*/device/power_state")):
            try:
                state = path.read_text().strip()
            except OSError:
                continue
            (active if state == "D0" else inactive).append(path.parent.parent.name + " (" + state + ")")
        if active:
            return result("gpu", "gpu", "Graphics & driver", "ok",
                f"{len(active)} active DRM GPU(s); the driver stack responds.",
                "\n".join(active + [str(x) + " - not active" for x in inactive]),
                "lspci -k", {"gpu_active": len(active), "gpu_inactive": len(inactive)})
        return unavailable("gpu", "gpu", "Graphics & driver", p)

    def battery(self):
        batteries = list(Path("/sys/class/power_supply").glob("BAT*"))
        if not batteries:
            return result("battery", "devices", "Battery", "skipped", "No laptop battery is exposed on this machine.")
        b = batteries[0]
        try:
            capacity = number((b / "capacity").read_text().strip())
            status = (b / "status").read_text().strip()
            if capacity is None or not 0 <= capacity <= 100:
                raise ValueError("Invalid battery percentage.")
            m = {"battery_pct": capacity}
            for unit in ["energy", "charge"]:
                full, design = b / (unit + "_full"), b / (unit + "_full_design")
                if full.exists() and design.exists():
                    f, d = number(full.read_text().strip()), number(design.read_text().strip())
                    if f is None or d is None or f < 0 or d <= 0:
                        raise ValueError("Invalid battery capacity data.")
                    m["battery_health_pct"] = f / d * 100
                    break
            health = m.get("battery_health_pct")
            return result("battery", "devices", "Battery", "warn" if health is not None and health < 60 else "ok",
                f"{capacity:.0f}% · {status}" + (f" · {health:.0f}% design capacity." if health is not None else ". Health capacity is not exposed."),
                json.dumps(m, indent=2), "upower -d", m)
        except (OSError, ValueError) as exc:
            return unavailable("battery", "devices", "Battery", {"output": str(exc), "command": "upower -d"})

    def network(self):
        routes, errors = [], []
        for version in ["-4", "-6"]:
            p = self.run(["ip", "-j", version, "route", "show", "default"])
            try:
                data = json.loads(p.get("stdout", p["output"])) if p["ok"] else None
                if not isinstance(data, list):
                    raise ValueError("Unavailable routes")
                routes += data
            except (ValueError, TypeError):
                errors.append(p["output"])
        if not routes:
            return result("network", "network", "Route & DNS", "unknown" if errors else "bad",
                "Routing could not be checked." if errors else "No IPv4 or IPv6 default route found.", "\n".join(errors), "ip route; ip -6 route")
        start = time.monotonic()
        dns = self.run(["getent", "ahosts", "example.com"], timeout=3)
        elapsed = (time.monotonic() - start) * 1000
        state = "ok" if dns["ok"] and not errors else "unknown" if dns.get("code") in (124, 127, 126) or errors else "warn"
        return result("network", "network", "Route & DNS", state,
            "Default route and DNS lookup work." if dns["ok"] and not errors else "DNS or routing needs inspection; see evidence.",
            json.dumps(routes, indent=2) + "\nDNS: " + dns["output"] + ("\nRoute query errors: " + "\n".join(errors) if errors else ""),
            "ip route; ip -6 route; getent ahosts example.com", {"dns_ms": elapsed} if dns["ok"] else {})

    def packages(self, deep=False):
        orphan_probe = self.run(["pacman", "-Qtdq"], allowed=(0, 1))
        orphan_text = orphan_probe.get("stdout", "").strip()
        orphan_ok = orphan_probe["ok"] and (orphan_probe["code"] == 0 or (orphan_probe["code"] == 1 and not orphan_probe["output"]))
        orphan_count = len(orphan_text.splitlines()) if orphan_ok else None
        if not deep:
            return result("packages", "system", "Package integrity", "skipped",
                "File integrity is included in Deep scan. " + (f"{orphan_count} orphan package(s) listed." if orphan_count is not None else "Orphan count unavailable."),
                orphan_probe["output"], "pacman -Qk; pacman -Qtdq", {"orphan_packages": orphan_count} if orphan_count is not None else {})
        p = self.run(["pacman", "-Qk"], timeout=25, allowed=(0, 1))
        if not p["ok"]:
            return unavailable("packages", "system", "Package integrity", p)
        text = p.get("stdout", p["output"])
        matches = re.findall(r"^.+: \d+ total files, (\d+) missing files", text, re.M)
        if not matches or len(text) >= 1024 * 1024 or (p["code"] == 1 and not any(int(v) for v in matches)):
            return unavailable("packages", "system", "Package integrity", {**p, "output": "Integrity output was incomplete or could not be interpreted.\n" + p["output"]})
        missing = sum(int(v) for v in matches)
        evidence = "\n".join(line for line in text.splitlines() if not line.endswith(" 0 missing files")) if missing else f"Verified {len(matches)} package summaries with zero missing files."
        metrics = {"missing_files": missing}
        if orphan_count is not None:
            metrics["orphan_packages"] = orphan_count
        return result("packages", "system", "Package integrity", "warn" if missing else "unknown" if orphan_count is None else "ok",
            f"{missing} missing file(s) across {len(matches)} packages. " + (f"{orphan_count} orphan package(s)." if orphan_count is not None else "Orphan count unavailable."),
            evidence + "\n\nOrphan packages (not automatically errors):\n" + orphan_probe["output"], "pacman -Qk; pacman -Qtdq", metrics)

    def audio(self):
        p = self.run(["wpctl", "status"])
        if not p["ok"] or not p["output"].strip():
            return unavailable("audio", "devices", "Audio graph", p)
        return result("audio", "devices", "Audio graph", "ok", "PipeWire / WirePlumber is responding.", p["output"], "wpctl status")

    def bluetooth(self):
        p = self.run(["bluetoothctl", "show"], timeout=3)
        if not p["ok"]:
            return unavailable("bluetooth", "devices", "Bluetooth", p)
        if "No default controller" in p["output"]:
            return result("bluetooth", "devices", "Bluetooth", "skipped", "No default Bluetooth controller.", p["output"], p["command"])
        powered = re.search(r"Powered:\s*(yes|no)", p["output"])
        if not powered:
            return unavailable("bluetooth", "devices", "Bluetooth", p)
        return result("bluetooth", "devices", "Bluetooth", "ok" if powered[1] == "yes" else "skipped",
            "Controller is powered on." if powered[1] == "yes" else "Bluetooth is switched off.", p["output"], p["command"])

    def wifi(self):
        p = self.run(["nmcli", "-t", "-f", "WIFI", "general"])
        if not p["ok"]:
            return unavailable("wifi", "network", "Wi-Fi radio", p)
        value = p.get("stdout", p["output"]).strip()
        if value not in ("enabled", "disabled"):
            return unavailable("wifi", "network", "Wi-Fi radio", p)
        return result("wifi", "network", "Wi-Fi radio", "ok" if value == "enabled" else "skipped",
            "Wi-Fi radio is " + value + ". This does not prove internet connectivity.", p["output"], "nmcli device status")

    def crashes(self):
        since, after = self.window("crashes")
        p = self.run(["coredumpctl", *(since or ["--since", "today"]), "--no-pager", "--no-legend", "list"], allowed=(0, 1))
        if p["code"] == 1 and re.fullmatch(r"No coredumps found\.?", p["output"].strip()):
            return result("crashes", "system", "Application crashes", "ok", f"No new core dumps{after}." if after else "No core dumps recorded today.", p["output"], p["command"], {"crashes": 0})
        if not p["ok"] or p["code"] != 0:
            return unavailable("crashes", "system", "Application crashes", p)
        lines = [x for x in p["output"].splitlines() if x.strip()]
        return result("crashes", "system", "Application crashes", "warn" if lines else "ok", f"{len(lines)} new core dump record(s){after}." if after else f"{len(lines)} core dump record(s) today.", p["output"], p["command"], {"crashes": len(lines)})

    def shell(self):
        since, after = self.window("shell")
        p = self.run(["journalctl", "--user", "-b", *since, "-n", "300", "--no-pager", "-o", "json"])
        if not p["ok"]:
            return unavailable("shell", "system", "Omarchy shell", p)
        lines = []
        for line in p.get("stdout", p["output"]).splitlines():
            if not line.strip() or line.startswith("--"):
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                return unavailable("shell", "system", "Omarchy shell", {**p, "output": "Could not parse the journal response."})
            identity = " ".join(str(entry.get(k, "")) for k in ("_COMM", "SYSLOG_IDENTIFIER", "_SYSTEMD_USER_UNIT"))
            priority = number(entry.get("PRIORITY"))
            message = str(entry.get("MESSAGE", ""))
            error_message = re.search(r"\b(warning|error|failed)\b|(?:Type|Reference|Syntax|Range)Error\b|binding loop|Unable to assign|Cannot assign", message, re.I)
            if re.search(r"quickshell|omarchy-shell|\bqs\b", identity, re.I) and ((priority is not None and priority <= 4) or error_message):
                lines.append(message)
        return result("shell", "system", "Omarchy shell", "warn" if lines else "ok",
            (f"{len(lines)} new shell warning/error record(s){after}." if after else f"{len(lines)} shell warning/error record(s) in the recent journal window.") if lines
            else (f"No new shell warnings{after}." if after else "No shell warnings in the recent 300-record user journal window."),
            "\n".join(lines), "journalctl --user -b -p 4 --no-pager", {"shell_warnings": len(lines)})


CHECKS = [("services", "System & user services"), ("journal", "Boot journal"), ("cpu", "Processor activity"),
    ("memory", "Memory headroom"), ("temperature", "Thermal sensors"), ("storage", "Root filesystem"),
    ("drives", "Physical drive health"), ("gpu", "Graphics & driver"), ("battery", "Battery"),
    ("network", "Route & DNS"), ("packages", "Package integrity"), ("audio", "Audio graph"),
    ("bluetooth", "Bluetooth"), ("wifi", "Wi-Fi radio"), ("crashes", "Application crashes"), ("shell", "Omarchy shell")]

class History:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.path, timeout=3)
        os.chmod(self.path, 0o600)
        self.db.execute("CREATE TABLE IF NOT EXISTS scans (id TEXT PRIMARY KEY, ts REAL, mode TEXT, state TEXT, rows TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS samples (ts REAL PRIMARY KEY, metrics TEXT)")
        self.db.execute("CREATE TABLE IF NOT EXISTS fixes (id TEXT PRIMARY KEY, check_id TEXT, title TEXT, started REAL, "
            "status TEXT, before TEXT, after TEXT, resolved REAL, agent TEXT, attempts INTEGER DEFAULT 0)")
        self.db.commit()

    def close(self):
        self.db.close()

    def sample(self, metrics, timestamp=None):
        self.db.execute("INSERT OR REPLACE INTO samples VALUES (?, ?)", (timestamp or time.time(), json.dumps(metrics)))
        self.db.execute("DELETE FROM samples WHERE ts < ?", (time.time() - RETENTION,))
        self.db.commit()

    def save(self, scan_id, mode, rows):
        previous = self.db.execute("SELECT rows FROM scans ORDER BY ts DESC LIMIT 1").fetchone()
        old = {r["id"]: r for r in json.loads(previous[0])} if previous else {}
        changes = []
        for row in rows:
            before = old.get(row["id"])
            comparable = before and before["state"] != "skipped" and row["state"] != "skipped"
            if row["state"] == "skipped":
                row["change"] = "not measured"
            elif before and before["state"] == "skipped":
                row["change"] = "measured"
            elif not previous:
                row["change"] = "baseline"
            elif not before:
                row["change"] = "new"
            elif row["state"] in ("bad", "warn"):
                row["change"] = "persistent" if before["state"] in ("bad", "warn") else "new"
            elif row["state"] == "ok" and before["state"] in ("bad", "warn"):
                row["change"] = "resolved"
            else:
                row["change"] = "unchanged" if before["state"] == row["state"] else "changed"
            if comparable and before["state"] != row["state"]:
                changes.append({"id": row["id"], "title": row["title"], "from": before["state"], "to": row["state"]})
        self.db.execute("INSERT INTO scans VALUES (?, ?, ?, ?, ?)", (scan_id, time.time(), mode, verdict(rows)[0], json.dumps(rows)))
        self.settle(rows, mode)
        self.db.execute("DELETE FROM scans WHERE ts < ? OR id NOT IN (SELECT id FROM scans ORDER BY ts DESC LIMIT 1000)", (time.time() - RETENTION,))
        self.db.commit()
        metrics = {}
        for row in rows:
            metrics.update(row["metrics"])
        self.sample(metrics)
        return changes

    def latest(self):
        row = self.db.execute("SELECT rows FROM scans ORDER BY ts DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else []

    def open_fix(self, row, agent):
        # A new hand-off supersedes any attempt still open for the same check,
        # so each check has at most one fix in progress.
        self.db.execute("UPDATE fixes SET status='superseded', resolved=? WHERE check_id=? AND status IN ('pending','still_failing')",
            (time.time(), row["id"]))
        fix_id = uuid.uuid4().hex
        self.db.execute("INSERT INTO fixes (id, check_id, title, started, status, before, agent) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
            (fix_id, row["id"], row["title"], time.time(), json.dumps(row), agent))
        self.db.commit()
        return fix_id

    def baselines(self):
        """Hand-off time per check: events up to then were given to an agent as evidence."""
        return dict(self.db.execute("SELECT check_id, MAX(started) FROM fixes WHERE status != 'abandoned' GROUP BY check_id").fetchall())

    def settle(self, rows, mode):
        """Close open fixes whose check now passes; count a failed recheck as an attempt."""
        updates = []
        for row in rows:
            if row["state"] == "skipped":
                continue
            for fix_id, status in self.db.execute("SELECT id, status FROM fixes WHERE check_id=? AND status IN ('pending','still_failing')", (row["id"],)).fetchall():
                if row["state"] == "ok":
                    self.db.execute("UPDATE fixes SET status='fixed', after=?, resolved=? WHERE id=?", (json.dumps(row), time.time(), fix_id))
                    updates.append({"id": fix_id, "check": row["id"], "title": row["title"], "status": "fixed"})
                elif mode == "recheck":
                    self.db.execute("UPDATE fixes SET status='still_failing', after=?, attempts=attempts+1 WHERE id=?", (json.dumps(row), fix_id))
                    updates.append({"id": fix_id, "check": row["id"], "title": row["title"], "status": "still_failing"})
            if row["state"] in ("bad", "warn"):
                # A fix that does not hold is not a fix: the problem came back within a day.
                for (fix_id,) in self.db.execute("SELECT id FROM fixes WHERE check_id=? AND status='fixed' AND resolved >= ?", (row["id"], time.time() - 86400)).fetchall():
                    self.db.execute("UPDATE fixes SET status='regressed', after=? WHERE id=?", (json.dumps(row), fix_id))
                    updates.append({"id": fix_id, "check": row["id"], "title": row["title"], "status": "regressed"})
        self.db.commit()
        return updates

    def fixes(self, limit=200):
        out = []
        for i, c, t, st, status, before, after, res, agent, attempts in self.db.execute(
                "SELECT id, check_id, title, started, status, before, after, resolved, agent, attempts FROM fixes ORDER BY started DESC LIMIT ?", (limit,)).fetchall():
            b, a = json.loads(before) if before else {}, json.loads(after) if after else {}
            out.append(dict(id=i, check=c, title=t, started=st, status=status, resolved=res, agent=agent or "", attempts=attempts or 0,
                before_state=b.get("state", ""), before_summary=b.get("summary", ""), after_state=a.get("state", ""), after_summary=a.get("summary", "")))
        return out

    def read(self, seconds=86400):
        raw = self.db.execute("SELECT ts, metrics FROM samples WHERE ts >= ? ORDER BY ts", (time.time() - seconds,)).fetchall()
        stride = max(1, math.ceil(len(raw) / 180))
        chosen = raw[::stride]
        if raw and (not chosen or chosen[-1] != raw[-1]):
            chosen.append(raw[-1])
        scans = self.db.execute("SELECT id, ts, mode, state, rows FROM scans ORDER BY ts DESC LIMIT 40").fetchall()
        saved = []
        expected = {key for key, _ in CHECKS}
        for i,t,m,s,r in scans:
            rows = json.loads(r)
            complete = len(rows) == len(CHECKS) and {row.get("id") for row in rows} == expected
            saved.append(dict(id=i,timestamp=t,mode=m,state=s,rows=rows,complete=complete))
        return {"samples": [{"timestamp": t, "metrics": json.loads(m)} for t, m in chosen],
                "scans": saved, "range_seconds": seconds, "fixes": self.fixes()}

def emit(kind, **values):
    print(json.dumps({"schema": SCHEMA, "type": kind, **values}, ensure_ascii=False, allow_nan=False), flush=True)

def run_check(probes, key, title, deep=False):
    began = time.monotonic()
    try:
        row = probes.packages(deep) if key == "packages" else getattr(probes, key)()
    except Exception as exc:
        row = result(key, "system", title, "unknown", "Check could not complete.", str(exc))
    row["duration_ms"] = round((time.monotonic() - began) * 1000)
    return row

def default_agent():
    try:
        return subprocess.run(["omarchy-default-agent"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""

HINTS = {
    "crashes": "\n\nFor crashes, follow Omarchy's diagnose-crash skill if your harness has it, or read\n$OMARCHY_PATH/default/agents/skills/diagnose-crash/SKILL.md directly. Work per crashing program.",
    "journal": "\n\nGroup the journal records by source and fix each real cause; say which ones are benign noise.",
}

def fix_prompt(row, host, fix_id):
    here = Path(__file__).resolve()
    hint = HINTS.get(row["id"], "")
    evidence = (row.get("evidence") or "No additional output was collected.")[:6000]
    return f"""Omarchy Doctor found a problem on this machine ({host}) and I want you to fix it.

Finding:   {row['title']}  [{row['id']}]
State:     {row['state']} ({row.get('change') or 'current'})
Summary:   {row['summary']}
Checked:   {dt.datetime.fromtimestamp(row.get('timestamp') or time.time()).strftime('%Y-%m-%d %H:%M:%S')}
Inspect:   {row.get('command') or 'n/a'}

Evidence Doctor collected:
{evidence}

How to work:
1. Inspect first. Re-run the inspect command and read the real state before changing anything.
2. Find the root cause and tell me what it is in one or two sentences.
3. Fix it the proper way for Arch/Omarchy: pacman/yay for packages, systemd units and drop-ins
   for services, never hand-edited vendor files under /usr.
4. Ask me before anything destructive or hard to undo (deleting data, removing packages,
   reformatting, force operations, changing boot or disk config).
5. If the finding is harmless or cannot be fixed from here, say so plainly instead of forcing it.
6. Fix the cause, never the measurement. Do not make the check pass by hiding evidence: no
   deleting core dumps, vacuuming or rotating journals, masking or disabling units just to
   silence them, or editing Doctor. Crash and journal checks already count only events after
   this hand-off, so earlier records are fine to leave alone. If the problem recurs within a
   day, Doctor marks this fix as regressed.{hint}

When you are done, verify with Doctor. It re-runs only this check and records the result
in its fix history (fix {fix_id}):

  omarchy-shell nixfred.doctor recheck {row['id']}

If the shell is not running, use: python3 {here} recheck {row['id']}
Report the recheck result. If it still fails, keep going or explain what is left."""

def run_scan(probes, deep=False):
    scan_id, start = uuid.uuid4().hex, time.monotonic()
    emit("scan_start", id=scan_id, total=len(CHECKS), timestamp=time.time(), host=socket.gethostname(), mode="deep" if deep else "quick")
    rows = []
    def work(key, title):
        return run_check(probes, key, title, deep)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(work, key, title) for key, title in CHECKS]
        for future in concurrent.futures.as_completed(futures):
            row = future.result(); rows.append(row)
            emit("check", result=row, completed=len(rows), total=len(CHECKS))
    return scan_id, rows, round((time.monotonic() - start) * 1000)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scan", "watch", "history", "export", "fix", "recheck", "fixes"], nargs="?", default="scan")
    parser.add_argument("check", nargs="?", default="")
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--no-launch", action="store_true", help="record the fix and print the prompt without opening an agent")
    parser.add_argument("--agent", default="", help="name recorded for this fix; defaults to the Omarchy default agent")
    parser.add_argument("--seconds", type=int, default=86400)
    parser.add_argument("--database", default=str(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "omarchy-doctor/history.sqlite3"))
    parser.add_argument("--interval", type=float, default=3)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    probes = Probes()
    if args.action in ("scan", "recheck") and Path(args.database).exists():
        try:
            history = History(args.database)
            try:
                probes.since = history.baselines()
            finally:
                history.close()
        except (OSError, sqlite3.Error):
            pass
    if args.action == "scan":
        scan_id, rows, duration = run_scan(probes, args.deep)
        changes, storage_error = [], ""
        if STOP.is_set():
            emit("error", message="Scan cancelled; partial results only.")
            return 1
        try:
            history = History(args.database)
            try:
                changes = history.save(scan_id, "deep" if args.deep else "quick", rows)
            finally:
                history.close()
        except (OSError, sqlite3.Error, ValueError) as exc:
            storage_error = str(exc)
        state, counts = verdict(rows)
        emit("scan_end", id=scan_id, state=state, counts=counts, complete=len(rows) == len(CHECKS),
            timestamp=time.time(), duration_ms=duration, changes=changes,
            annotations={r["id"]: r.get("change", "") for r in rows}, storage_error=storage_error)
    elif args.action in ("fix", "recheck"):
        titles = dict(CHECKS)
        if args.check not in titles:
            emit("error", message=f"Unknown check: {args.check or '(none)'}. Known: {', '.join(titles)}")
            return 2
        history = History(args.database)
        try:
            if args.action == "recheck":
                row = run_check(probes, args.check, titles[args.check])
                emit("check", result=row, completed=1, total=1)
                rows = [r for r in history.latest() if r.get("id") != args.check] + [row]
                # Stored as a scan so the panel, history and later diffs see the new state.
                history.db.execute("INSERT INTO scans VALUES (?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, time.time(), "recheck", verdict(rows)[0], json.dumps(rows)))
                history.db.commit()
                updates = history.settle([row], "recheck")
                emit("recheck_end", check=args.check, state=row["state"], summary=row["summary"], fixes=updates, timestamp=time.time())
            else:
                row = next((r for r in history.latest() if r.get("id") == args.check), None) or run_check(probes, args.check, titles[args.check])
                if row["state"] in ("ok", "skipped"):
                    emit("error", message=f"{row['title']} is {row['state']}; there is nothing to fix.")
                    return 3
                agent = args.agent or default_agent()
                fix_id = history.open_fix(row, agent)
                prompt = fix_prompt(row, socket.gethostname(), fix_id)
                launcher = shlex.split(os.environ.get("DOCTOR_AGENT_COMMAND", "omarchy-agent-prompt"))
                launched, error = False, ""
                if not args.no_launch:
                    if not agent and "DOCTOR_AGENT_COMMAND" not in os.environ:
                        error = "No default agent. Choose one with: omarchy default agent <name>"
                    else:
                        try:
                            subprocess.Popen(launcher + [prompt], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
                            launched = True
                        except OSError as exc:
                            error = f"Could not start the agent: {exc}"
                if error:
                    history.db.execute("UPDATE fixes SET status='abandoned', resolved=? WHERE id=?", (time.time(), fix_id))
                    history.db.commit()
                emit("fix_start", id=fix_id, check=args.check, title=row["title"], agent=agent, launched=launched,
                    error=error, prompt=prompt if args.no_launch else "", timestamp=time.time())
                if error:
                    return 4
        finally:
            history.close()
    elif args.action == "fixes":
        history = History(args.database)
        try:
            emit("fixes", fixes=history.fixes())
        finally:
            history.close()
    elif args.action == "watch":
        while not STOP.is_set():
            metrics, errors = {}, []
            for fn in [probes.cpu, probes.memory, probes.storage, probes.temperature, probes.gpu]:
                if STOP.is_set():
                    break
                row = fn(); metrics.update(row["metrics"])
                if row["state"] == "unknown":
                    errors.append(row["id"])
            if STOP.is_set():
                break
            timestamp, storage_error = time.time(), ""
            try:
                history = History(args.database)
                try:
                    history.sample(metrics, timestamp)
                finally:
                    history.close()
            except (OSError, sqlite3.Error) as exc:
                storage_error = str(exc)
            emit("vitals", timestamp=timestamp, metrics=metrics, unavailable=errors, storage_error=storage_error)
            STOP.wait(max(2, args.interval))
    else:
        history = History(args.database)
        try:
            data = history.read(max(60, min(RETENTION, args.seconds)))
        finally:
            history.close()
        if args.action == "history":
            emit("history", host=socket.gethostname(), **data)
        else:
            folder = Path(args.database).parent / "reports"
            folder.mkdir(exist_ok=True, mode=0o700)
            path = folder / ("doctor-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
            path.write_text(json.dumps({"version": VERSION, "host": socket.gethostname(), "generated_at": time.time(), "scans": data["scans"]}, indent=2))
            os.chmod(path, 0o600)
            emit("export", path=str(path))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        stop_children()
        raise SystemExit(0)
    except (OSError, sqlite3.Error, ValueError) as exc:
        emit("error", message=str(exc))
        raise SystemExit(1)
