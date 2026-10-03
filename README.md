# Omarchy Doctor

![Omarchy Doctor](docs/omarchy-doctor.jpg)

A native, animated diagnostic companion to Pulse. Doctor combines a living system diagram, CPU/RAM/storage/GPU illustrations, live graphs, and evidence-backed findings in one Omarchy bar plugin.

![Installed Doctor with real system data](verification/live-overview.png)

[Delivery and verification](verification/README.md) · [Kimi3 review decisions](verification/KIMI-DECISIONS.md)

## What it does

- Animated system core, moving diagnostic connections, active processor cells, a memory fill wave, rotating disk and graphics glyphs, and staged page entrances.
- Live CPU, available RAM, root storage and GPU readings while the panel is open. Missing readings remain unavailable.
- Sixteen diagnostic checks: system and user services, boot journal, CPU, memory and pressure, current temperature inputs, root storage, physical-drive SMART coverage, graphics, battery, routes and DNS, packages, audio, Bluetooth, Wi-Fi, crashes, and Omarchy shell warnings.
- Findings ranked by severity, with actual output, timestamps, duration and copyable inspection commands. New, persistent and resolved findings are identified against the previous scan.
- Quick and deep scans. Deep scans add package-file integrity; routine scans report orphan counts without walking all package-owned files.
- Seven days of local observations and up to 1,000 checkups. History offers 1-hour, 24-hour and 7-day ranges, saved scan inspection, and JSON report export.
- **Fix with agent.** Any problem, attention or unavailable finding can be handed to your default Omarchy coding agent (`omarchy agent prompt`, the same path Omarchy's own crash notifications use). The agent gets the finding, its collected evidence and the inspect command, along with standing rules: inspect first, fix it the Arch/Omarchy way, ask before anything destructive. It finishes by running `omarchy-shell nixfred.doctor recheck <check>`, which re-probes only that check.
- **Fixes history.** Every hand-off is recorded. A fix counts only once Doctor itself measures the check healthy again, whether from the agent's recheck, your Recheck button or a later full scan. The Fixes tab shows what was fixed, what is still with an agent and what is still failing, with before and after summaries, the agent used and how long it took.
- Theme-aware colors, a single Omarchy typeface throughout, a compact layout, keyboard navigation, reduced motion and configurable automatic scans.

The Doctor collector never repairs, deletes, installs packages, restarts services, kills applications or uploads diagnostic output. Its only writes are its own history, its fix records and exported reports. Changes to the system happen only when you press **Fix with agent**, and then they are made by your own agent, in its own terminal window, under its own permission settings. Doctor's briefing tells the agent to ask before anything destructive, but the agent's configuration is what actually enforces that. Choose the agent with `omarchy default agent <name>`. DNS checking resolves `example.com`. Commands in findings are copied only when requested; they are never executed by clicking a result.

![Findings with Fix with agent](verification/live-findings.png)

![Fixes history](verification/live-fixes.png)

## Install

Requires Omarchy Quattro/Quickshell, Git, Python 3 and the Omarchy plugin CLI.

### Recommended: install with Omarchy

Open a terminal and run:

```bash
omarchy plugin add https://github.com/nixfred/omarchy-doctor.git --enable
```

Omarchy downloads the repository into `~/.config/omarchy/plugins/nixfred.doctor`, validates it, and enables the plugin. Follow the prompts to confirm installation and choose its bar section. Run this as your normal desktop user, without `sudo`; you do not need a separate source checkout or to run `install.py`.

Click the medical-cross icon on the bar to open Doctor, or run:

```bash
omarchy-shell nixfred.doctor open
```

Update this installation with:

```bash
omarchy plugin update nixfred.doctor
```

### Alternative: install from a source checkout

Use the custom installer if you want its installation backups and automatic placement beside Pulse.

Open a terminal in the directory where you want to keep the source code, then download and install Doctor:

```bash
git clone https://github.com/nixfred/omarchy-doctor.git
cd omarchy-doctor
python3 install.py --enable
```

Run these commands as your normal desktop user, without `sudo`. If you already cloned the repository, open a terminal in that checkout and run only `python3 install.py --enable`.

This validates and copies the runtime into `~/.config/omarchy/plugins/nixfred.doctor`, backs up any prior installation and shell configuration, and places Doctor beside Pulse through Omarchy's public bar API. If Pulse is not on your bar, Doctor is added to the start of the right section. Existing widgets keep their order and settings. No shell restart is required. Omit `--enable` to install without placing it on the bar.

After installation with `--enable`, click the medical-cross icon on the bar to open Doctor, or run:

```bash
omarchy-shell nixfred.doctor open
```

#### Update a source-checkout installation

From your existing source checkout, download the latest changes and run the installer again:

```bash
git pull --ff-only
python3 install.py --enable
```

### Optional hardware tools

`lm_sensors` and `smartmontools` improve hardware coverage. Other checks use system-provided tools such as systemctl, journalctl, ip, getent, nmcli and wpctl. NVIDIA measurements use nvidia-smi; DRM activity is a fallback on other GPUs. Missing tools, permissions and unsupported sensors produce unavailable or skipped results, never a fabricated healthy verdict. SMART runs without privilege prompts. Reading an NVMe health log needs root, so when the plain read is denied Doctor retries once with `sudo -n`, which uses an existing passwordless rule or fails immediately; the drive then stays unknown and the evidence shows why. To allow only that read, add a sudoers drop-in such as `yourname ALL=(root) NOPASSWD: /usr/bin/smartctl ^-j -H /dev/[a-z0-9]+$` with `visudo -f /etc/sudoers.d/doctor-smart`.

## Controls

- The bar icon is a white medical cross on a badge: green when every completed check is healthy, amber when something needs attention, red when there is a problem, gray until Doctor has a complete result. The corner number counts open issues (problems plus attention).
- Left-click the Doctor icon to open or close it; middle-click to scan; right-click for Settings.
- Run Doctor performs a quick scan. Deep scan checks package files too. Cancel keeps partial results explicitly incomplete.
- Click any hardware card or finding to inspect its evidence. A non-healthy finding shows **Fix with agent** and **Recheck**.
- `R` scans, `C` copies the selected finding's diagnostic command, and `Esc` closes the panel. Arrow keys navigate the focused findings list using actual row geometry. Tab traverses controls.
- About links to the source on GitHub and nixfred.com and explains how fixes, results and data work.
- Settings offers animation/reduced motion and manual, 2-minute or 5-minute automatic scans. Automatic scans and live sampling run only while Doctor is open. A scan already started may finish after closing.

## Health semantics

Healthy means completed checks reported no concern. Unavailable evidence, intentional skips, incomplete scans and results older than ten minutes are distinguished. A quick scan intentionally skips package integrity. A usage spike alone is not treated as a failure. Sensor critical limits are never mistaken for current temperatures, and virtual compressed-memory devices are not presented as physical SMART drives.

Three checks count history rather than current state: application crashes (core dumps today), the boot journal (high-priority records this boot) and Omarchy shell warnings. A crash cannot be un-crashed, so these could never clear without deleting evidence. Once one of them is handed to an agent, everything up to the hand-off counts as reviewed, and the check reports only events that happen afterwards. A fix that is followed by the same kind of problem within 24 hours is marked **regressed** (shown as "came back"). The agent briefing forbids passing a check by hiding evidence: no deleting core dumps, vacuuming journals, masking units or editing Doctor.

Graphs use timestamped real observations. A gap longer than two minutes is left unconnected. A fresh installation has no historical data; history accumulates from scans and while the panel is open. The overview retains recent observations; History reads the selected range from local storage.

## Data and recovery

Data defaults to `~/.local/state/omarchy-doctor/` (or `$XDG_STATE_HOME/omarchy-doctor`). The SQLite database is mode 0600. Evidence can contain device names, service names and journal messages, so inspect an exported report before sharing it. Exports remain until manually removed.

`installation.json` names the exact backup directory. To remove Doctor from the bar, use `omarchy plugin disable nixfred.doctor`. To restore an earlier plugin version, copy its backed-up `plugin/` contents into the installation and rescan plugins. Do not restore the whole shell configuration over unrelated later changes; its backup is a recovery reference.

## CLI and IPC

```bash
python3 doctor.py scan
python3 doctor.py scan --deep
python3 doctor.py history --seconds 604800
python3 doctor.py export
omarchy-shell nixfred.doctor open
omarchy-shell nixfred.doctor status
omarchy-shell nixfred.doctor scan
omarchy-shell nixfred.doctor deepScan
omarchy-shell nixfred.doctor show history
omarchy-shell nixfred.doctor fix services       # hand a finding to the default agent
omarchy-shell nixfred.doctor recheck services   # re-probe one check, settle its fix
python3 doctor.py fix services --no-launch      # record a fix and print the agent briefing only
python3 doctor.py recheck services
python3 doctor.py fixes
```

The collector emits versioned JSON-lines events. `DOCTOR_AGENT_COMMAND` overrides the launcher (default `omarchy-agent-prompt`); the briefing is passed as its last argument. `--database PATH` permits isolated testing. `doctor-checks.sh` is a compatibility launcher for this JSONL collector; the old TSV protocol is archived under `review/baseline/`.

## Development and verification

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
shellcheck doctor-checks.sh
python3 tests/native.py --shell-root /path/to/omarchy/shell
```

The native test opens a temporary panel, validates variable-height navigation and unknown-state handling, captures all pages, and closes automatically. It uses fixture data labeled as such in evidence. `verification/` holds native screenshots and validation records. The browser study in `design/` is an earlier sample-data concept; the installed interface is native QML.

The collector uses four bounded probe workers, explicit exit-status handling and process-group cleanup on timeouts/cancellation. Ambient Canvas drawing runs at 10 Hz only while visible, without expensive shadow blur. Separate QML components own hardware graphics, graphs, overview, evidence, history and settings.

License: MIT.
