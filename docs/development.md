# Development and verification

The [README](../README.md) covers everyday use. This guide covers source installation, diagnostic interfaces and contributions.

## Install from source

```bash
git clone https://github.com/nixfred/omarchy-doctor.git
cd omarchy-doctor
python3 install.py --enable
```

Run as the normal desktop user. The custom installer validates the plugin, backs up an existing installation and shell configuration, and uses the public bar API to place Doctor beside Pulse when present, otherwise at the start of the right section. Existing widget order and settings are preserved. Omit `--enable` to copy the installation without placing it on the bar. No shell restart is required.

To update a clean source checkout:

```bash
git pull --ff-only
python3 install.py --enable
```

Root QML/JavaScript and Python files are the editable source. The manifest selects a versioned runtime directory, currently `runtime-1.6.0-r3/`. The installer builds that snapshot from source; keep committed runtime files identical to their root counterparts. Distinct QML URLs prevent stale cache after a plugin rescan.

## Backups and recovery

The custom installer's `installation.json` under the local Doctor state directory names its backup. Each backup contains the prior plugin and a shell configuration reference. Restore plugin contents only when required, then rescan plugins. Do not replace a whole shell configuration over newer unrelated desktop changes; use Omarchy's public configuration APIs for narrow adjustments.

## Collector and IPC

```bash
python3 doctor.py scan
python3 doctor.py scan --deep
python3 doctor.py history --seconds 604800
python3 doctor.py export
python3 doctor.py fixes
omarchy-shell nixfred.doctor status
omarchy-shell nixfred.doctor scan
omarchy-shell nixfred.doctor deepScan
omarchy-shell nixfred.doctor show issues
omarchy-shell nixfred.doctor fix services
omarchy-shell nixfred.doctor recheck services
```

The collector emits versioned JSON-lines events. `--database PATH` selects an isolated SQLite database. Scans, history reconciliation, assessments and handoffs can write Doctor's own state; they are not suitable for read-only forensic inspection of a live database. `doctor-checks.sh` is a compatibility launcher; the old TSV interface is archived under `review/baseline/`.

Probes use four bounded workers, explicit command status checks and process-group cleanup on cancellation/timeouts. Missing or malformed evidence stays unknown. Journal queries are bounded to seven days and 500 records, with limited coverage shown explicitly. Temperature checks use each sensor's limits; compressed-memory devices are excluded from physical-drive SMART checks. Narrow known-harmless journal patterns keep ignored notices visible with reasons, and near-miss regression tests prevent broad suppression.

## Agent completion contract

```bash
python3 doctor.py fix services --no-launch
python3 doctor.py fix services --no-launch --agent your-agent
python3 doctor.py recheck services
python3 doctor.py assess services --disposition investigate --reason 'Evidence-backed diagnosis'
```

The shared handoff instructions give every agent a local receipt path and callback command:

```bash
python3 doctor.py report HANDOFF_ID --result-file RECEIPT_PATH --database DATABASE_PATH
```

The receipt is a JSON object with `outcome` (`completed`, `blocked`, `failed` or `interrupted`), `summary`, `changes`, `validation`, `rollback`, and optional boolean `needs_fix`. Use the exact paths and handoff ID in the briefing. Report real changes and checks, not plans. Never fabricate rollback instructions.

Doctor reconciles returned receipt files even if the callback is missed. Its detached supervisor records launch/terminal failures and missing results; a 24-hour missing-result fallback is not a repair verdict. Duplicate identical receipts are idempotent; conflicting reports are rejected, and late results cannot overwrite a newer attempt. Grok has an additional conservative, exactly correlated completed-session recovery adapter. Other agents use the shared receipt contract; agents may ignore it, in which case Doctor reports the missing result.

`DOCTOR_AGENT_COMMAND` overrides the launcher, normally `omarchy-agent-prompt`; the briefing is the last argument. Agent permissions remain independent of Doctor. Assessments control actionable classification but never establish verified health. Reports are untrusted plain text. Immutable verification receipts retain measured commands, outputs and timestamps; event silence never proves a crash/log repair.

## Checks

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
shellcheck doctor-checks.sh
```

The unit suite uses temporary databases and mocked probes/launchers. Native closed-panel suites need Quickshell, an Omarchy shell checkout and a working Wayland session:

```bash
export OMARCHY_PATH=/path/to/omarchy
python3 tests/qml_events.py
python3 tests/qml_novice.py
```

Set `DOCTOR_RUNTIME_ROOT` to test a versioned runtime instead of root source. Logs default to the temporary directory; `DOCTOR_QML_LOG` can specify a destination. The native suites keep the panel closed and exercise actual components with fixture state. The older `tests/native.py` opens a temporary visible panel; use it deliberately, not during another person's active desktop session.

## Documentation screenshots

```bash
python3 tools/render_docs.py --shell-root /path/to/omarchy/shell --output /tmp/doctor-docs
```

The renderer loads the actual QML panes into an offscreen Qt window, disables desktop display connections and uses only invented fixture data. It never opens the live Doctor panel, runs probes, invokes an agent or reads Doctor's history. README screenshots are illustrative native renders. History plots show explicit supplied samples, not real machine measurements. Review every generated image before publishing it.
