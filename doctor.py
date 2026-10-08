#!/usr/bin/env python3
"""Omarchy Doctor: eight plain-English health checks, a little local history,
and a hand-off to your own coding agent when something needs fixing.

Green means there is nothing you need to do. Only problems a person can act on
change the bar icon. Checks that cannot run are listed, never counted.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime as dt
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

VERSION = "2.0.0"
SCHEMA = 2
MAX_OUTPUT = 12000
STOP = threading.Event()
CHILDREN = set()
RANK = {"ok": 0, "unknown": 0, "skipped": 0, "warn": 1, "bad": 2}

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
    """Runs one bounded, read-only command. Never raises."""
    def __call__(self, args, timeout=5, allowed=(0,)):
        command = shlex.join(args)
        if STOP.is_set():
            return dict(ok=False, code=124, output="Cancelled.", command=command)
        if not shutil.which(args[0]):
            return dict(ok=False, code=127, output=f"{args[0]} is not installed.", command=command)
        try:
            with tempfile.TemporaryFile() as out:
                proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT, start_new_session=True,
                    env={**os.environ, "LC_ALL": "C", "SYSTEMD_COLORS": "0", "SYSTEMD_PAGER": "cat"})
                CHILDREN.add(proc)
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
                out.seek(0)
                text = out.read(MAX_OUTPUT).decode("utf-8", "replace").strip()
                return dict(ok=code in allowed, code=code, output=text, stdout=text, command=command)
        except OSError as exc:
            return dict(ok=False, code=126, output=str(exc), command=command)

def finding(key, state, title, advice="", details="", command="", level=0, signature="", metrics=None):
    """One check's result. `title` is the plain-English headline; `advice` is what to do.
    `level` and `signature` decide whether a problem the user called fine has got worse."""
    assert state in RANK
    return dict(id=key, name=dict(CHECKS)[key], state=state, title=title, advice=advice,
                details=str(details)[:MAX_OUTPUT], command=command, level=level, signature=signature,
                metrics=metrics or {}, timestamp=time.time())

def not_checked(key, why, probe=None):
    return finding(key, "unknown", f"Couldn't check: {why}", details=(probe or {}).get("output", ""), command=(probe or {}).get("command", ""))

# Hardware limits for temperature. CPUs that report no limit of their own boost
# into the 90s by design, so they get their package limit instead of a flat 85°C.
CPU_LIMITS = (("k10temp", 95, 100), ("zenpower", 95, 100), ("coretemp", 95, 100))
DEFAULT_LIMITS = (85, 95)

def sensor_limits(tree):
    """(label, current, warn, critical) per sensor, using the hardware's own limits when it has them."""
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
                crit, high = limit("crit"), limit("max")
                cpu = next((c for c in CPU_LIMITS if chip.startswith(c[0])), None)
                if crit is not None:
                    warn = crit - 5
                elif cpu:
                    warn, crit = cpu[1], cpu[2]
                elif high is not None:
                    warn, crit = high, high + 10
                else:
                    warn, crit = DEFAULT_LIMITS
                out.append((f"{chip} {feature}", n, warn, crit))
    return out

def read_values(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        parts = line.replace(":", " ", 1).split()
        if len(parts) >= 2 and number(parts[1]) is not None:
            values[parts[0]] = float(parts[1])
    return values

def pressure(kind):
    """Share of the last minute that tasks waited on `kind` (a one-minute average, so brief spikes don't count)."""
    try:
        m = re.search(r"^some .*\bavg60=([\d.]+)", Path(f"/proc/pressure/{kind}").read_text(), re.M)
        return number(m.group(1)) if m else None
    except OSError:
        return None

class Probes:
    def __init__(self, run=None):
        self.run = run or Runner()

    def storage(self):
        try:
            d = shutil.disk_usage("/")
            pct = d.used / d.total * 100
        except (OSError, ZeroDivisionError) as exc:
            return not_checked("storage", "disk space", {"output": str(exc), "command": "df -h /"})
        free = d.free / 2**30
        state = "bad" if pct >= 95 else "warn" if pct >= 90 else "ok"
        title = f"Your disk is {pct:.0f}% full" if state != "ok" else f"{free:.0f} GB free ({pct:.0f}% used)"
        return finding("storage", state, title,
            "Free up space: empty the trash, delete big downloads you no longer need, or remove old snapshots." if state != "ok" else "",
            f"{free:.1f} GiB free of {d.total / 2**30:.1f} GiB on /.", "df -h /",
            level=int(pct // 5 * 5), signature="/", metrics={"disk_used_pct": pct, "disk_free_gib": free})

    def services(self):
        failed, details, errors = [], [], 0
        for scope, flags in (("system", []), ("user", ["--user"])):
            p = self.run(["systemctl", *flags, "--failed", "--no-legend", "--plain", "--no-pager"])
            details.append(f"{scope}: " + (p["output"] or "none failed"))
            if not p["ok"]:
                errors += 1
                continue
            failed += [line.split()[0] for line in p["stdout"].splitlines() if line.strip()]
        if not failed and errors == 2:
            return not_checked("services", "background services", {"output": "\n".join(details), "command": "systemctl --failed"})
        if not failed:
            return finding("services", "ok", "All background services are running", details="\n".join(details), command="systemctl --failed")
        names = ", ".join(n.removesuffix(".service") for n in failed[:3]) + (f" and {len(failed) - 3} more" if len(failed) > 3 else "")
        title = f"A background service failed: {names}" if len(failed) == 1 else f"{len(failed)} background services failed: {names}"
        return finding("services", "bad", title, "Restart it, or find out why it stopped so it does not happen again.",
            "\n".join(details), "systemctl --failed; systemctl --user --failed",
            level=len(failed), signature=" ".join(sorted(failed)), metrics={"failed_units": len(failed)})

    def drives(self):
        p = self.run(["lsblk", "-J", "-d", "-p", "-o", "NAME,TYPE,MODEL"])
        try:
            devices = [d for d in json.loads(p["stdout"]).get("blockdevices", []) if d.get("type") == "disk"
                       and not re.match(r"/dev/(zram|loop|ram)\d", d.get("name", ""))] if p["ok"] else None
        except (ValueError, AttributeError, KeyError):
            devices = None
        if devices is None:
            return not_checked("drives", "drive health", p)
        if not devices:
            return finding("drives", "skipped", "No physical drives to check")
        failed, unknown, details = [], [], []
        for device in devices[:16]:
            name = device.get("name", "")
            if not re.fullmatch(r"/dev/[A-Za-z0-9_.-]+", name):
                continue
            q = self.run(["smartctl", "-j", "-H", name], timeout=4, allowed=tuple(range(256)))
            # The kernel only gives the NVMe health log to root. sudo -n uses an existing
            # passwordless rule or fails at once; it never prompts.
            if q["code"] & 2 and "Permission denied" in q["output"]:
                s = self.run(["sudo", "-n", "smartctl", "-j", "-H", name], timeout=6, allowed=tuple(range(256)))
                if not s["code"] & 1:
                    q = s
            try:
                passed = json.loads(q["stdout"]).get("smart_status", {}).get("passed")
            except (ValueError, TypeError, KeyError):
                passed = None
            details.append(f"{name} {device.get('model') or ''}\n{q['output']}")
            if q["code"] == 127:
                return not_checked("drives", "drive health (install smartmontools)", q)
            if q["code"] & 7 or not isinstance(passed, bool):
                unknown.append(name)
            elif not passed:
                failed.append(name)
        if failed:
            return finding("drives", "bad", f"A drive is failing: {', '.join(failed)}",
                "Back up your files now, then plan to replace the drive.", "\n\n".join(details), "smartctl -H " + failed[0],
                level=len(failed), signature=" ".join(failed))
        if unknown and len(unknown) == len(devices[:16]):
            return not_checked("drives", "drive health (needs permission to read it)", {"output": "\n\n".join(details), "command": "smartctl -H"})
        return finding("drives", "ok", f"{len(devices) - len(unknown)} drive(s) report healthy", details="\n\n".join(details), command="smartctl -H")

    def temperature(self):
        p = self.run(["sensors", "-j"])
        values = []
        try:
            values = sensor_limits(json.loads(p["stdout"])) if p["ok"] else []
        except (ValueError, TypeError):
            pass
        if not values:
            for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
                try:
                    n = number(path.read_text().strip())
                    if n is not None and -30000 <= n <= 150000:
                        values.append(((path.parent / "type").read_text().strip(), n / 1000, *DEFAULT_LIMITS))
                except OSError:
                    pass
        if not values:
            return not_checked("temperature", "temperature (no sensors found)", p)
        rank = lambda v: 2 if v[1] >= v[3] else 1 if v[1] >= v[2] else 0
        worst = max(values, key=lambda v: (rank(v), v[1] - v[2]))
        hottest = max(values, key=lambda v: v[1])
        state = ("ok", "warn", "bad")[rank(worst)]
        title = (f"Your computer is running hot ({worst[1]:.0f}°C)" if state == "warn" else f"Your computer is too hot ({worst[1]:.0f}°C)") if state != "ok" else f"Temperature is normal ({hottest[1]:.0f}°C)"
        return finding("temperature", state, title,
            "Close heavy apps, and make sure the vents are not blocked or dusty." if state != "ok" else "",
            "\n".join(f"{label}: {value:.1f}°C (warns at {warn:.0f}, critical at {crit:.0f})" for label, value, warn, crit in values),
            "sensors", level=RANK[state], signature=worst[0].split()[0], metrics={"temperature_c": hottest[1]})

    def battery(self):
        batteries = sorted(Path("/sys/class/power_supply").glob("BAT*"))
        if not batteries:
            return finding("battery", "skipped", "No battery on this computer")
        b = batteries[0]
        try:
            capacity = number((b / "capacity").read_text().strip())
            health = None
            for unit in ("energy", "charge"):
                full, design = b / f"{unit}_full", b / f"{unit}_full_design"
                if full.exists() and design.exists():
                    f, d = number(full.read_text().strip()), number(design.read_text().strip())
                    if f is not None and d:
                        health = f / d * 100
                    break
        except OSError as exc:
            return not_checked("battery", "battery", {"output": str(exc)})
        if health is not None and health < 60:
            return finding("battery", "warn", f"Your battery only holds {health:.0f}% of its original charge",
                "It still works, but it runs out sooner. A replacement brings back full battery life.",
                f"Charge now {capacity:.0f}%. Health {health:.0f}% of design capacity.", "upower -d",
                level=-int(health // 10 * 10), signature="health", metrics={"battery_health_pct": health})
        return finding("battery", "ok", "Battery is healthy" + (f" ({health:.0f}% of original capacity)" if health is not None else ""),
            details=f"Charge now {capacity:.0f}%.", command="upower -d", metrics={"battery_pct": capacity})

    def network(self):
        routes = []
        for version in ("-4", "-6"):
            p = self.run(["ip", "-j", version, "route", "show", "default"])
            try:
                routes += json.loads(p["stdout"]) if p["ok"] else []
            except ValueError:
                pass
        if not routes:
            return finding("network", "bad", "You are not connected to the internet",
                "Connect to Wi-Fi or plug in a network cable.", "No default route.", "ip route",
                level=2, signature="offline")
        dns = self.run(["getent", "ahosts", "example.com"], timeout=4)
        if dns["code"] in (126, 127):
            return not_checked("network", "internet (getent is missing)", dns)
        if not dns["ok"]:
            return finding("network", "warn", "Connected, but websites can't be found",
                "Your network is up but name lookups (DNS) fail. Reconnect, or restart your router.",
                dns["output"], "getent ahosts example.com", level=1, signature="dns")
        return finding("network", "ok", "Connected to the internet", details=json.dumps(routes, indent=1)[:2000], command="ip route")

    def wifi(self):
        p = self.run(["nmcli", "-t", "-f", "WIFI-HW,WIFI", "general"])
        if not p["ok"]:
            return finding("wifi", "skipped", "Wi-Fi is not managed by NetworkManager here", details=p["output"])
        hw, _, radio = p["stdout"].strip().partition(":")
        if hw == "missing":
            return finding("wifi", "skipped", "No Wi-Fi on this computer")
        if radio == "enabled":
            return finding("wifi", "ok", "Wi-Fi is on", command="nmcli radio wifi")
        wired = self.run(["ip", "-j", "-4", "route", "show", "default"])
        if wired["ok"] and wired["stdout"].strip() not in ("", "[]"):
            return finding("wifi", "ok", "Wi-Fi is off (you are on a wired connection)", command="nmcli radio wifi")
        return finding("wifi", "warn", "Wi-Fi is turned off", "Turn Wi-Fi on from the network menu in the bar.",
            p["output"], "nmcli radio wifi on", level=1, signature="off")

    def memory(self):
        try:
            v = read_values("/proc/meminfo")
            total, available = v["MemTotal"], v["MemAvailable"]
            used = (total - available) / total * 100
        except (OSError, KeyError, ZeroDivisionError) as exc:
            return not_checked("memory", "memory", {"output": str(exc)})
        psi = pressure("memory")
        free = available / 1048576
        # Linux uses spare memory as cache, so a high "used" number alone is normal.
        # Pressure (time spent waiting on memory) is what you feel as slowness.
        state = "bad" if psi is not None and psi >= 25 else "warn" if (psi is not None and psi >= 10) or used >= 95 else "ok"
        title = "Your computer is short on memory" if state != "ok" else f"Memory is fine ({free:.1f} GB available)"
        return finding("memory", state, title,
            "Close apps or browser tabs you don't need." if state != "ok" else "",
            f"{free:.1f} GiB available, {used:.0f}% in use, memory pressure {psi if psi is not None else 'n/a'}%.",
            "free -h", level=RANK[state], signature="memory", metrics={"ram_available_gib": free, "ram_used_pct": used})

CHECKS = [("storage", "Disk space"), ("services", "Background services"), ("drives", "Drive health"),
          ("temperature", "Temperature"), ("battery", "Battery"), ("network", "Internet"),
          ("wifi", "Wi-Fi"), ("memory", "Memory")]

def run_check(probes, key):
    try:
        return getattr(probes, key)()
    except Exception as exc:  # a broken probe must never break the scan
        return not_checked(key, dict(CHECKS)[key].lower(), {"output": repr(exc)})

def actionable(rows):
    return [r for r in rows if RANK.get(r["state"], 0) > 0 and not r.get("dismissed")]

def verdict(rows):
    need = actionable(rows)
    state = "bad" if any(r["state"] == "bad" for r in need) else "warn" if need else "ok" if rows else "unknown"
    return {"state": state, "count": len(need)}

class History:
    """Latest results, repairs handed to an agent, and problems the user called fine."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.path, timeout=5)
        os.chmod(self.path, 0o600)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS scans (ts REAL, rows TEXT);
            CREATE TABLE IF NOT EXISTS fixes (id TEXT PRIMARY KEY, check_id TEXT, title TEXT, agent TEXT,
                started REAL, status TEXT, after TEXT, resolved REAL);
            CREATE TABLE IF NOT EXISTS fine (check_id TEXT PRIMARY KEY, state TEXT, level REAL, signature TEXT, ts REAL);
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def latest(self):
        row = self.db.execute("SELECT rows FROM scans ORDER BY ts DESC LIMIT 1").fetchone()
        return json.loads(row[0]) if row else []

    def apply_fine(self, rows):
        """Hide a problem the user called fine until it gets worse or changes; forget it once it clears."""
        fine = {c: (s, l, sig) for c, s, l, sig in self.db.execute("SELECT check_id, state, level, signature FROM fine")}
        for row in rows:
            row.pop("dismissed", None)
            if row["id"] not in fine or row["state"] in ("unknown", "skipped"):
                continue
            state, level, signature = fine[row["id"]]
            if row["state"] == "ok":
                self.db.execute("DELETE FROM fine WHERE check_id=?", (row["id"],))
            elif RANK[row["state"]] <= RANK.get(state, 0) and row["level"] <= level and row["signature"] == signature:
                row["dismissed"] = True
            else:
                self.db.execute("DELETE FROM fine WHERE check_id=?", (row["id"],))
                row["came_back"] = True
        self.db.commit()
        return rows

    def settle(self, rows, recheck=False):
        """A repair counts only when Doctor measures the check healthy again."""
        updates = []
        for row in rows:
            for fix_id, status in self.db.execute("SELECT id, status FROM fixes WHERE check_id=? AND status IN ('working','not_fixed')", (row["id"],)).fetchall():
                if row["state"] in ("ok", "skipped"):
                    self.db.execute("UPDATE fixes SET status='fixed', after=?, resolved=? WHERE id=?", (row["title"], time.time(), fix_id))
                    updates.append({"id": fix_id, "check": row["id"], "status": "fixed"})
                elif recheck and RANK[row["state"]] > 0:
                    self.db.execute("UPDATE fixes SET status='not_fixed', after=? WHERE id=?", (row["title"], fix_id))
                    updates.append({"id": fix_id, "check": row["id"], "status": "not_fixed"})
        self.db.commit()
        return updates

    def save(self, rows, recheck=False):
        if recheck:
            merged = {r["id"]: r for r in self.latest()}
            merged.update({r["id"]: r for r in rows})
            rows = [merged[k] for k, _ in CHECKS if k in merged]
        self.apply_fine(rows)
        updates = self.settle(rows, recheck)
        self.db.execute("INSERT INTO scans VALUES (?, ?)", (time.time(), json.dumps(rows)))
        self.db.execute("DELETE FROM scans WHERE ts NOT IN (SELECT ts FROM scans ORDER BY ts DESC LIMIT 50)")
        self.db.commit()
        return rows, updates

    def call_fine(self, check):
        row = next((r for r in self.latest() if r["id"] == check), None)
        if not row or RANK.get(row["state"], 0) == 0:
            return None
        self.db.execute("INSERT OR REPLACE INTO fine VALUES (?, ?, ?, ?, ?)", (check, row["state"], row["level"], row["signature"], time.time()))
        self.db.commit()
        return row

    def not_fine(self, check):
        self.db.execute("DELETE FROM fine WHERE check_id=?", (check,))
        self.db.commit()

    def open_fix(self, row, agent):
        self.db.execute("UPDATE fixes SET status='replaced', resolved=? WHERE check_id=? AND status IN ('working','not_fixed')", (time.time(), row["id"]))
        fix_id = uuid.uuid4().hex[:12]
        self.db.execute("INSERT INTO fixes VALUES (?, ?, ?, ?, ?, 'working', '', NULL)", (fix_id, row["id"], row["title"], agent, time.time()))
        self.db.commit()
        return fix_id

    def fixes(self, limit=20):
        cols = ("id", "check", "title", "agent", "started", "status", "after", "resolved")
        return [dict(zip(cols, r)) for r in self.db.execute(
            "SELECT id, check_id, title, agent, started, status, after, resolved FROM fixes WHERE status != 'replaced' ORDER BY started DESC LIMIT ?", (limit,))]

def emit(kind, **values):
    print(json.dumps({"schema": SCHEMA, "type": kind, **values}, ensure_ascii=False), flush=True)

def state_event(history, rows=None, updates=None):
    rows = history.latest() if rows is None else rows
    last = history.db.execute("SELECT MAX(ts) FROM scans").fetchone()[0]
    emit("state", host=socket.gethostname(), rows=rows, verdict=verdict(rows), fixes=history.fixes(),
         updates=updates or [], last_scan=last or 0)

def default_agent():
    try:
        return subprocess.run(["omarchy-default-agent"], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""

def fix_prompt(row, host):
    here = Path(__file__).resolve()
    return f"""Omarchy Doctor found a problem on this computer ({host}) and I'd like you to fix it.

Problem: {row['title']}
Doctor's advice: {row['advice'] or 'none'}
Details: {row['details'] or 'none'}
Command to look at it yourself: {row['command'] or 'none'}

Please:
1. Look first. Run the command above and check the real state before changing anything.
2. Tell me the cause in a sentence or two, in plain words.
3. Fix it the proper way for Arch/Omarchy: pacman or yay for packages, systemd units and
   drop-ins for services. Never hand-edit files under /usr.
4. Ask me before anything that deletes data or is hard to undo.
5. Fix the cause, not the measurement. Never hide the problem to make the check pass.

When you are done, ask Doctor to check again. It records the result:

  omarchy-shell nixfred.doctor recheck {row['id']}

(If that does not work: python3 {here} recheck {row['id']})
Then tell me what Doctor reported."""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["scan", "state", "recheck", "fix", "fine", "notfine"], nargs="?", default="scan")
    parser.add_argument("check", nargs="?", default="")
    parser.add_argument("--no-launch", action="store_true", help="record the fix and print the briefing without opening an agent")
    parser.add_argument("--agent", default="", help="name recorded for this fix (default: the Omarchy default agent)")
    parser.add_argument("--database", default=str(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "omarchy-doctor/doctor-v2.sqlite3"))
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)
    names = dict(CHECKS)
    if args.action in ("recheck", "fix", "fine", "notfine") and args.check not in names:
        emit("error", message=f"Unknown check '{args.check}'. Known: {', '.join(names)}")
        return 2
    probes = Probes()
    history = History(args.database)
    try:
        if args.action == "scan":
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                rows = list(pool.map(lambda key: run_check(probes, key), names))
            if STOP.is_set():
                emit("error", message="Check cancelled.")
                return 1
            rows, updates = history.save(rows)
            state_event(history, rows, updates)
        elif args.action == "state":
            state_event(history, history.apply_fine(history.latest()))
        elif args.action == "recheck":
            rows, updates = history.save([run_check(probes, args.check)], recheck=True)
            state_event(history, rows, updates)
        elif args.action in ("fine", "notfine"):
            if args.action == "fine" and not history.call_fine(args.check):
                emit("error", message="There is nothing to hide for that check right now.")
                return 3
            if args.action == "notfine":
                history.not_fine(args.check)
            state_event(history, history.apply_fine(history.latest()))
        else:
            row = next((r for r in history.latest() if r["id"] == args.check), None) or run_check(probes, args.check)
            if RANK.get(row["state"], 0) == 0:
                emit("error", message=f"{row['name']} looks fine; there is nothing to fix.")
                return 3
            agent = args.agent or default_agent()
            if not args.no_launch and not agent and "DOCTOR_AGENT_COMMAND" not in os.environ:
                emit("error", message="Pick a default agent first: omarchy default agent <name>")
                return 4
            prompt = fix_prompt(row, socket.gethostname())
            fix_id = history.open_fix(row, agent)
            if not args.no_launch:
                launcher = shlex.split(os.environ.get("DOCTOR_AGENT_COMMAND", "omarchy-agent-prompt"))
                try:
                    subprocess.Popen(launcher + [prompt], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                except OSError as exc:
                    history.db.execute("UPDATE fixes SET status='replaced' WHERE id=?", (fix_id,))
                    history.db.commit()
                    emit("error", message=f"Could not start your agent: {exc}")
                    return 4
            emit("fix_start", id=fix_id, check=args.check, agent=agent, prompt=prompt if args.no_launch else "")
            state_event(history, history.apply_fine(history.latest()))
    finally:
        history.close()
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        stop_children()
        raise SystemExit(0)
    except (OSError, sqlite3.Error) as exc:
        emit("error", message=str(exc))
        raise SystemExit(1)
