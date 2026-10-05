# Omarchy Doctor

![Omarchy Doctor — check, understand, verify](docs/images/hero.png)

**A clearer picture of your Omarchy desktop.** Doctor checks your system, explains warnings, and keeps the evidence behind an agent's repair. Open it from your bar whenever something feels wrong—or just to see how your machine is doing.

Doctor's own checks read the system; they do not repair it. **Ask my agent** hands a selected issue to your chosen Omarchy assistant, which works under its own permissions. Its report and Doctor's independent recheck appear together.

The screenshots below are native Doctor 1.6.0 panes rendered with invented example data. They illustrate the interface, not anyone's real computer or a promised result. Colors follow your Omarchy theme.

## Install and open

You need Omarchy Quattro with Quickshell, Python 3, Git and the Omarchy plugin CLI. In a terminal, as your normal desktop user:

```bash
omarchy plugin add https://github.com/nixfred/omarchy-doctor.git --enable
```

Follow Omarchy's installation prompts. Click the medical cross in your bar, or open Doctor with:

```bash
omarchy-shell nixfred.doctor open
```

To get updates:

```bash
omarchy plugin update nixfred.doctor
```

Already keeping a source checkout? See the [source installation guide](docs/development.md#install-from-source). Use one installation approach consistently; neither needs `sudo`.

## Your first checkup

Click **Run Doctor** for a quick scan. Start with **Overview**: it shows the system diagram, hardware readings and concerns worth reviewing. Click **Review issues** to continue. A fresh installation builds its history as you use it.

![Native Overview with example health readings and one storage concern](docs/images/overview.png)

Quick scans cover services, logs, processor, memory, temperature, storage, drive health, graphics, battery, networking, audio, Bluetooth, Wi-Fi, crashes and shell warnings. **Deep scan** also inspects package-owned files; it can take longer. A quick scan skipping that work does not clear an earlier package warning. **Cancel** leaves unfinished coverage visible.

| Result | What to do |
| --- | --- |
| Healthy / green | Completed, fresh checks found no unresolved concern. |
| Attention / amber or Problem / red | Open Issues and read what triggered the result. |
| Unavailable or incomplete | Doctor needs more evidence; a missing tool or permission can be the reason. |
| Old result | Run a new scan. Results over ten minutes old cannot establish current health. |

The bar's number counts active actionable concerns and current unavailable checks. Past crash and log records have their own history count; rereading them does not create new repair work. A green result describes measured checks, not a guarantee about every part of the computer.

## Understand an issue

**Issues** brings findings, repair records, graphs and saved checkups together. Start with **Needs fixing**, the default filter. **Investigate** shows current uncertainty, **History** shows past events, and **All** keeps every check available. Old events can still need fixing when their cause has been diagnosed.

![Native Issues showing a selected example storage warning and agent controls](docs/images/issues.png)

Choose a finding, then open **Show evidence & diagnosis**. You can inspect its time, source, output and diagnostic command. Copying the command does not run it. Finding numbers such as `F-000001` stay stable on this computer, so you can follow the same issue across checkups.

![Native expanded evidence showing the example finding's source and evidence time](docs/images/evidence.png)

Crash and journal entries are grouped by a specific signature. **Historical** means the same old evidence was seen again; **New** means a new event appeared; **Recurring** means a new event matches an earlier signature. Those labels describe timing, not a confirmed cause. Known harmless journal notices remain in the evidence with an explanation.

Scroll within the evidence card to see the inspection command and collected output.

![Native evidence card scrolled to the example command and collected output](docs/images/inspect.png)

## Ask your agent—and check the result

Click **Ask my agent** to send the selected finding, its evidence and investigation instructions to your default Omarchy agent. Doctor asks it to inspect first, report actual changes and validation, and ask before destructive work. Your agent's own permission settings enforce what it may do.

The repair record tracks the attempt and the returned report. **Show the work** reveals changes, supplied undo guidance, and Doctor's measured before/after evidence.

![Native repair record with an illustrative agent report and an independent failing recheck](docs/images/repair.png)

Scroll through the expanded record to see the measured checks.

![Native repair record scrolled to before/after readings and independent verification](docs/images/repair-proof.png)

An agent saying “done” does not mark a repair verified. A state check must measure healthy again. Crashes and log events stay repair-unproven: a quiet log cannot prove their cause was fixed. If the agent returns no usable report, Doctor shows that honestly. A later failure reopens the concern while preserving earlier verification records. **Recheck** runs the selected diagnostic again.

## See what changed over time

In Issues, click **Show history**. Choose Processor, Memory, Storage or Graphics and a 1-hour, 24-hour or 7-day range. Select a saved checkup to inspect what Doctor saw at that time; use **Back to current scan** to return.

![Native history graph and saved checkups using invented example observations](docs/images/history.png)

Graphs use recorded observations. Blank stretches mean no readings were collected; Doctor does not invent values across long gaps. Live sampling and automatic scans run while its panel is open. A scan already underway may finish after you close it.

## Make it comfortable

**Settings** lets you choose gentle movement or still drawings, and manual checks or quick checks every 2, 5 or 15 minutes. Your current selection stays in place until you change it. **Choose an agent…** opens Omarchy's existing chooser.

![Native Settings with movement, check frequency, agent choice and retention information](docs/images/settings.png)

Left-click the bar icon to open or close Doctor; middle-click to scan; right-click for Settings. Inside the panel, `R` scans and `Esc` closes it. In Issues, `C` copies the selected command; arrows move through the focused list and Tab moves between controls.

**About** gives a short explanation and links to the project and its author.

![Native About page explaining Check, Understand and Verify](docs/images/about.png)

## Common questions

**Why is a hardware check unavailable?** Some sensors and tools are optional. `lm_sensors` improves temperature coverage; `smartmontools` adds drive-health checks. Unsupported hardware and denied permissions remain unknown. SMART checks never open a password prompt. Install optional tools only if you need that coverage.

**Why does package integrity still warn?** Deep scan uses package-tool output. Missing files and access-denied paths need investigation; a warning alone does not establish that files were deleted. Read the evidence with your agent before changing packages or permissions.

**Where is my data?** Observations and checkups stay locally in `~/.local/state/omarchy-doctor/` (or `$XDG_STATE_HOME/omarchy-doctor`). Readings/checkups retain up to seven days, with at most 1,000 checkups. Finding numbers and repair records persist for tracking. Each computer keeps its own state.

**Can I share a report?** **Export JSON report** saves a local file. Review it first: diagnostics can contain device names, service names and log messages. Doctor does not upload them itself. Handing evidence to a cloud-backed agent is subject to that agent's data handling. Exported files remain until you remove them.

**How do I remove it from the bar?** Run `omarchy plugin disable nixfred.doctor`. Source-install backup and recovery details are in the [development guide](docs/development.md#backups-and-recovery).

For command-line use, agent completion details and tests, see [Development and verification](docs/development.md).

Made by [Fred Nix](https://nixfred.com) · [Source on GitHub](https://github.com/nixfred/omarchy-doctor) · [MIT license](LICENSE).
