import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Omarchy Doctor: one icon that answers "do I need to do anything?" and one
// screen that says what, in plain words, with a button to get it fixed.
Panel {
    id: root
    moduleName: "nixfred.doctor"
    ipcTarget: "nixfred.doctor"
    manageIpc: false
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    property string version: "2.0.0"
    property string page: "status"
    property var rows: []
    property var verdict: ({state: "unknown", count: 0})
    property var fixes: []
    property real lastScan: 0
    property real now: Date.now() / 1000
    property string hostname: "This computer"
    property string notice: ""
    property string busyCheck: ""
    property string agentName: ""
    property bool showFine: false
    property var openDetails: ({})
    readonly property bool scanning: collector.running
    readonly property bool autoCheck: root.setting("autoCheck", true) === true
    readonly property string repoUrl: "https://github.com/nixfred/omarchy-doctor"
    readonly property string homeUrl: "https://nixfred.com"

    readonly property var problems: rows.filter(function(r) { return (r.state === "warn" || r.state === "bad") && !r.dismissed })
                                        .sort(function(a, b) { return (b.state === "bad") - (a.state === "bad") })
    readonly property var others: rows.filter(function(r) { return r.state !== "skipped" && problems.indexOf(r) < 0 })
    readonly property var recentFixes: fixes.filter(function(f) { return f.status === "fixed" }).slice(0, 3)
    readonly property string iconState: rows.length ? verdict.state : "unknown"
    readonly property string headline: !rows.length ? (scanning ? "Checking your computer…" : "Let's check your computer")
        : verdict.count === 0 ? "All good" : verdict.count === 1 ? "1 thing needs you" : verdict.count + " things need you"

    readonly property color ink: Color.popups.text
    readonly property color dim: Qt.alpha(ink, 0.62)
    readonly property color surface: Color.popups.background
    readonly property color card: Qt.alpha(ink, 0.04)
    readonly property color edge: Qt.alpha(ink, 0.13)
    readonly property bool lightTheme: surface.r * 0.2126 + surface.g * 0.7152 + surface.b * 0.0722 > 0.55
    readonly property color good: lightTheme ? "#2f7a3a" : "#8fd694"
    readonly property color warning: lightTheme ? "#946300" : "#e8b572"
    readonly property color danger: lightTheme ? "#b63927" : "#ef8a78"
    function tint(state) { return state === "bad" ? danger : state === "warn" ? warning : state === "ok" ? good : dim }

    function ago(ts) {
        if (!ts) return "not checked yet"
        var s = Math.max(0, Math.round(now - ts))
        return s < 60 ? "checked just now" : s < 3600 ? "checked " + Math.floor(s / 60) + " min ago"
            : s < 86400 ? "checked " + Math.floor(s / 3600) + " h ago" : "checked " + Math.floor(s / 86400) + " days ago"
    }
    function when(ts) {
        var s = Math.max(0, Math.round(now - ts))
        return s < 3600 ? "just now" : s < 86400 ? "today" : s < 172800 ? "yesterday" : Math.floor(s / 86400) + " days ago"
    }
    function fixFor(check) {
        for (var i = 0; i < fixes.length; i++)
            if (fixes[i].check === check && (fixes[i].status === "working" || fixes[i].status === "not_fixed")) return fixes[i]
        return null
    }
    function args(action, extra) {
        var path = decodeURIComponent(String(Qt.resolvedUrl("doctor.py")).replace(/^file:\/\//, ""))
        return ["python3", "-u", path, action].concat(extra || [])
    }
    function saveSetting(key, value) {
        var next = {}
        for (var k in root.settings) next[k] = root.settings[k]
        next[key] = value
        root.settings = next
        if (root.bar && root.bar.shell) root.bar.shell.updateEntryInline(root.moduleName, next)
    }
    function openUrl(url) { Quickshell.execDetached(["xdg-open", url]); root.close() }
    function chooseAgent() { Quickshell.execDetached(["omarchy-menu", "summon", "setup.default.agent"]); root.close() }

    function scan() { if (!collector.running) { notice = ""; collector.command = args("scan"); collector.running = true } }
    function act(action, check) {
        if (actor.running) return
        busyCheck = check || ""
        actor.command = args(action, check ? [check] : [])
        actor.running = true
    }
    function fix(check) { if (!agentName) { chooseAgent(); return } act("fix", check) }
    function toggleDetails(id) { var d = {}; for (var k in openDetails) d[k] = openDetails[k]; d[id] = !d[id]; openDetails = d }

    function ingest(line) {
        var e
        try { e = JSON.parse(line) } catch (err) { return }
        if (e.type === "state") {
            rows = e.rows || []; verdict = e.verdict || verdict; fixes = e.fixes || []
            lastScan = e.last_scan || lastScan; hostname = e.host || hostname; now = Date.now() / 1000
            ;(e.updates || []).forEach(function(u) {
                var r = rows.filter(function(x) { return x.id === u.check })[0]
                var name = r ? r.name : u.check
                notice = u.status === "fixed" ? "Fixed! " + name + " is healthy again." : "Not fixed yet: " + (r ? r.title : name) + "."
            })
        } else if (e.type === "fix_start") {
            notice = "Your agent is on it. When it's done, Doctor checks again and tells you here."
        } else if (e.type === "error") {
            notice = e.message
        }
    }
    function status() {
        return JSON.stringify({version: version, opened: opened, page: page, verdict: verdict, iconState: iconState,
            problems: problems.map(function(r) { return {id: r.id, state: r.state, title: r.title} }),
            fine: others.length, fixes: fixes.slice(0, 5), notice: notice, lastScan: lastScan, scanning: scanning,
            panelWidth: panel.contentWidth, panelHeight: panel.contentHeight})
    }

    Component.onCompleted: { act("state"); agentReader.running = true }
    onOpenedChanged: if (opened) { now = Date.now() / 1000; page = "status"; agentReader.running = true; if (now - lastScan > 600) scan() }
    Timer { interval: root.opened ? 15000 : 60000; repeat: true; running: true; onTriggered: root.now = Date.now() / 1000 }
    // The icon is the product: keep it current in the background (eight light checks, about a second).
    Timer { interval: 30000; running: root.autoCheck; onTriggered: root.scan() }
    Timer { interval: 900000; repeat: true; running: root.autoCheck; onTriggered: root.scan() }

    Process { id: collector; stdout: SplitParser { onRead: function(line) { root.ingest(line) } } }
    Process { id: actor; stdout: SplitParser { onRead: function(line) { root.ingest(line) } } onExited: root.busyCheck = "" }
    Process { id: agentReader; command: ["omarchy-default-agent"]; stdout: StdioCollector { id: agentText } onExited: root.agentName = String(agentText.text).trim() }

    IpcHandler {
        target: "nixfred.doctor"
        function open(): void { root.open() }
        function close(): void { root.close() }
        function toggle(): void { root.toggle() }
        function scan(): void { root.scan() }
        function recheck(check: string): void { root.act("recheck", check) }
        function fix(check: string): void { root.fix(check) }
        function show(page: string): void { root.page = page === "about" ? "about" : "status"; root.open() }
        function status(): string { return root.status() }
    }

    BarIconButton {
        id: button; anchors.fill: parent; bar: root.bar; text: ""
        active: root.verdict.count > 0
        tooltipText: "Omarchy Doctor · " + (root.rows.length ? root.headline : "not checked yet")
        iconComponent: Component { MedicalCross { state: root.iconState; count: root.verdict.count; busy: root.scanning } }
        onPressed: function(code) {
            if (code === Qt.MiddleButton) root.scan()
            else if (code === Qt.RightButton) { root.page = "about"; root.open() }
            else root.toggle()
        }
    }

    KeyboardPanel {
        id: panel; anchorItem: button; owner: root; bar: root.bar; open: root.opened; focusTarget: body
        contentWidth: panel.fittedContentWidth(560)
        contentHeight: panel.fittedContentHeight(content.implicitHeight)
        Item {
            id: body; anchors.fill: parent; focus: true
            Keys.onEscapePressed: root.close()
            Keys.onPressed: function(event) { if (event.key === Qt.Key_R) { root.scan(); event.accepted = true } }
            Rectangle { anchors.fill: parent; anchors.margins: -8; radius: 12; color: root.surface }
            Flickable {
                anchors.fill: parent; contentWidth: width; contentHeight: content.implicitHeight; clip: true
                interactive: contentHeight > height; boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: content; width: parent.width; spacing: 14
                    Loader {
                        width: parent.width
                        sourceComponent: root.page === "about" ? aboutView : statusView
                    }
                }
            }
        }
    }
    Component { id: statusView; StatusPane { host: root } }
    Component { id: aboutView; AboutPane { host: root } }
}
