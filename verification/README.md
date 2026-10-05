# Native Doctor 1.0 delivery — October 1, 2026

Built and installed on Vic at `~/.config/omarchy/plugins/nixfred.doctor`, immediately after `nixfred.pulse`. Open its waveform/core glyph in the bar, or run `omarchy-shell nixfred.doctor open`.

## Delivered

Pulse-inspired native QML: animated system core and connections, CPU chip, memory fill wave, rotating disk and GPU glyph, real time-series graphs, animated page entrances and theme-aware colors. Overview, prioritized Findings/evidence, timestamped History and Settings are all functional. There is no browser wrapper or simulated production telemetry.

The bounded Python collector streams 16 checks, covers system and user services, separates sensor inputs from limits, inspects identified physical drives, and keeps unavailable, skipped, incomplete and stale data honest. Quick/deep scans, cancellation, seven-day local history, comparison annotations, report export, keyboard navigation, configurable automatic scans and reduced motion are implemented.

## Verification

- **47 unit tests pass:** [output](unit-tests.txt), covering diagnostic semantics, subprocess timeout, storage, change comparisons and installation failure recovery.
- **Native rendering passes:** all four pages, compact layout, light/dark colors, variable-height keyboard selection and unknown-state handling; [log](native-validation.log). History tests also verify partial archives stay incomplete, newer observations survive a history load, and obsolete range responses are ignored.
- **Actual partial process failure passes:** a fixture collector exits 7 after one healthy result; native UI retains the result but reports incomplete/unknown. [Log](partial-scan.log).
- **Installed live tests pass:** quick and deep scans produce all 16 results; live samples and saved scans accumulate; four pages render; closing stops the sampler. The raw status dumps from these runs are kept only on the test machine because they contain host network and journal data.
- **Local export passes:** valid JSON, mode 0600. [Evidence](export-verification.json). Motion settings persist through the public Omarchy API and update the running plugin; animation restored. [Evidence](settings-verification.json). Physical pointer button automation was unavailable; settings controls were rendered natively and their bindings inspected.
- **Performance:** isolated native fixture process used approximately **5.33% of one CPU core animated**, **0.17% with reduced motion**, and **0% closed** over short measurement windows. Animation phases advanced only when enabled and visible. These are measurements on this machine, not a guarantee for every system. [Results](performance.json), [harness](../tests/performance.py).
- **Plugin validation and ShellCheck pass.** Installation used Omarchy's public API without a shell restart.
- **Preservation passes:** existing shell configuration and widget order match before installation when Doctor is excluded; seven protected clipboard, Copilot and input files are unchanged by SHA-256. [Evidence](preservation.json).
- **Kimi3 reviewed the implementation:** two findings accepted directly, two suggestions used for additional hardening after rejecting inaccurate premises, and one incorrect finding rejected. [Decisions](KIMI-DECISIONS.md). Local GPU extraction was also attempted; its empty output was discarded.

## Installed screenshots

[Overview](live-overview.png) · [Findings](live-findings.png) · [History](live-history.png) · [Settings](live-settings.png). These show actual Vic data. `native-*.png` screenshots use explicitly labeled validation fixtures.

The observed deep scan reported recent boot-journal errors, nine missing package files, a current temperature warning, and unavailable SMART access for `/dev/nvme0n1`. These are diagnostic observations, not plugin failures. No system repair or privilege change was performed. A new history begins accumulating when Doctor is installed; it does not invent earlier data.

## Recovery

The current receipt at `~/.local/state/omarchy-doctor/installation.json` points to the exact backup. The original pre-install shell configuration is saved locally beside the receipt and is not published. Disable with `omarchy plugin disable nixfred.doctor`. For a prior plugin version, restore only its backed-up plugin directory and rescan; avoid replacing an entire shell config over unrelated later changes.

Project source remains in `/home/pi/Projects/omarchy.doctor.plugin`. It is not a usable Git checkout in this environment; no commit, push or public release was performed. Tracked as **OMW-DOCTOR** in the canonical Omarchy wish list.
