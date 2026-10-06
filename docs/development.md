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

Root QML/JavaScript and Python files are the editable source. The manifest selects a versioned runtime directory, currently `runtime-1.6.0-r4/`. The installer builds that snapshot from source; keep committed runtime files identical to their root counterparts. Distinct QML URLs prevent stale cache after a plugin rescan.

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

The unit suite uses temporary databases, mocked probes/launchers and a fixture package-inventory fingerprint; it does not depend on an installed Arch package database. Native closed-panel suites need Quickshell, an Omarchy shell checkout and a working Wayland session:

```bash
export OMARCHY_PATH=/path/to/omarchy
python3 tests/qml_gray.py
python3 tests/qml_events.py
python3 tests/qml_novice.py
python3 tests/qml_packages.py
python3 tests/qml_handoff.py
```

Set `DOCTOR_RUNTIME_ROOT` to test a versioned runtime instead of root source. Logs default to the temporary directory; `DOCTOR_QML_LOG` can specify a destination. The native suites keep the panel closed and exercise actual components with fixture state. The older `tests/native.py` opens a temporary visible panel; use it deliberately, not during another person's active desktop session.

## Documentation screenshots

```bash
python3 tools/render_docs.py --shell-root /path/to/omarchy/shell --output /tmp/doctor-docs
```

The renderer loads the actual QML panes into an offscreen Qt window, disables desktop display connections and uses only invented fixture data. It never opens the live Doctor panel, runs probes, invokes an agent or reads Doctor's history. README screenshots are illustrative native renders. History plots show explicit supplied samples, not real machine measurements. Review every generated image before publishing it.

### Working view, launch transport and recovered findings

The full Working pane starts before launch acknowledgement and tracks the exact saved attempt. Backend launch claims use an immediate SQLite transaction and reuse a still-live supervisor by PID/start token, or a short preparing reservation. Receipt and independent verification remain separate; terminal exit and JSON turn completion are never repair proof. Returned reports trigger verification newer than the receipt, even when an earlier manual check exists.

Background transport capability-checks `exec --help`, requires the exact effective directory to be explicitly trusted and a real Git repository to be discovered, and preserves Omarchy's existing `--approve-for-me` automatic-review policy. It uses `exec --json --color never`. Non-repository or home-wide repository contexts, other agents, missing capabilities, untrusted directories and `fix --interactive` use the existing visible launcher. No repository-check bypass, trust change or permission-policy weakening is added. Custom launcher overrides stay explicit.

Only received JSON event types supply activity updates; unknown output cannot invent progress. Local launch logs remain available. A recorded exact Codex session may be opened after a known nonnegative launcher exit; an interrupted supervisor does not authorize concurrent resume. Blocked input/security decisions remain with the agent and user. No live repair was launched to test this path. See [official noninteractive documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

Traffic-light colors and icon routes use current concerns and coverage, ignoring historical signatures for bar counts/color. Reopening recomputes the target; gray without a finding explains incomplete/stale coverage and offers Run Doctor. All routes are diagnostic navigation only.

A valid healthy state measurement records recovery provenance, original warning and current evidence under the same finding ID, including after unknown/skipped intervals. Recovery without a Doctor handoff does not prove that no outside work occurred. Thermal warnings have a two-degree recovery margin below every sensor warning point; warnings/critical crossings are still immediate, unknown/skipped never prove recovery, and recurrence reuses the identity. No thresholds, hardware or power settings were changed.

Additional safe checks: `tests/qml_progress.py`, `tests/qml_traffic.py`, and unit suites `test_progress.py`, `test_background.py`, `test_recovery.py`. Native tests keep their panels closed. The background integration uses a fake Codex executable in a temporary trusted fixture; no real agent, repair or authentication call occurs.

Bar review candidates require fresh measurement and event last-seen times (the existing ten-minute freshness window). Aged saved new/recurring flags remain in Issues/history but cannot independently color, count or select as current unreviewed concerns. Explicit unresolved coverage remains gray and names old measurement ages. This is covered by the final installed r7 native traffic fixtures.


Local r8 UI staging separates findings, repair records and checkup history. The main reader and long evidence use visible Previous/Next pages, with no wheel scrolling or font shrinking. Current unknowns remain unknown; past events are labeled not reviewed, and failed handoff stages say no report/no verification. Background Codex requires exact existing trust plus real Git discovery; non-repository or home-wide contexts retain the guard through the visible interactive launcher. No failed attempt is automatically retried.

QA: 101 Python tests, native closed novice/events/traffic/packages/retained-handoff/progress fixtures, plus offscreen native qml_fit.py at 640x480 through 1800x1050 logical scenes and scales 1, 1.25 and 1.5. Installer packages WorkingPane and ReadPages explicitly. UI fixtures do not perform live repairs or launch a real agent.


### Local reader and alert correction (2026-10-05, r9)

Journal MESSAGE values now decode JSON byte arrays as UTF-8, normalize ANSI/control sequences, and retain valid warning evidence when an entry is invalid or untimed. Reaching the existing 500-entry limit, unreadable/lossy messages, and missing timestamps remain incomplete coverage; no broader journal query is introduced. Default UI warnings and explicit QA crashes are log notes. Current measured faults and explicit diagnoses drive repair badges; incomplete coverage and current unreviewed crashes stay gray with separate metadata. Historical failures and verified recovery remain visible without a current repair alarm. Existing event identity aliases, observations, handoffs and receipts are preserved.

Validation: 115 Python tests, plugin validation, native policy/traffic/novice/package/event/lifecycle/harmless-handoff fixtures, plus five viewport sizes at Qt scales 1, 1.25 and 1.5. A bounded journal read can reach its entry limit; that incomplete coverage stays unknown rather than claiming verified shell health. Validation performs no real repairs, privileged checks or agent launches.

The actual decoded warning volume also exposed an IPC metadata-size limit. Final runtime r9-final bounds only status metadata to 24 child summaries and 40 filtered IDs/attempts with explicit total/omission counts; all full findings remain in the panel and local database. A closed native 600-note regression checks the response stays below 32 KiB and retains all full UI records.


### Local finite verification workflow (2026-10-05, r10)

Gray clicks now open Finish verification with exact gaps, source evidence, cursor progress and useful actions. Shell collection uses fixed snapshot bounds and inclusive validated cursor pages, explicit EOF, adaptive page sizes, bounded resumable operations, persistent jobs, and existing immutable event-observation identities. Package verification uses a separate normal user terminal; only the fixed system pacman command is passed to sudo. Full-file evidence retains its measurement time and expires after the existing ten-minute freshness window or package metadata changes. No automatic authentication or actual privileged verification is part of implementation validation.

133 Python tests cover continuation/EOF, timeout, cancellation, missing cursors, malformed records, restart/boot changes, fixed elevated command, stale evidence and adaptive output bounds. Native fixtures exercise the real bar/button handler → actual Doctor CLI → temporary SQLite with fake journal/terminal dispatcher, plus confirmation cancellation and five viewport sizes at three scales. Fixture popups remain explicitly unmapped; authentication, real agents and repair probes are excluded.

The final runtime adds the same complete-read mechanism for Boot journal checks with invalid message fields. Scope remains priority 0–3/current boot/seven days, with all fields requested and original benign/crash-duplicate rules retained. 135 unit tests include exact scope/policy and invalid-field non-completion; no real collection or authentication is performed during activation.

Gray-state UI copy leads with the number of incomplete checks and offers Finish verification from an empty Needs fixing view. A completed boot-log read uses the log-coverage predicate; optional skipped package checks do not request authentication. `tests/qml_gray.py` exercises these states and navigation using closed native synthetic fixtures.
