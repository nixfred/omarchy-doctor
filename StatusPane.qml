import QtQuick
import qs.Commons

// The whole of Doctor on one screen: the verdict, the problems in plain words
// with one button each, then everything that's fine folded into a single line.
Column {
    id: pane
    required property var host
    width: parent ? parent.width : 0
    spacing: 14

    component Words: Text { font.family: Style.font.family; color: pane.host.ink; wrapMode: Text.WordWrap; textFormat: Text.PlainText }

    Row {
        width: parent.width; spacing: 14
        MedicalCross { width: 44; height: 44; state: host.iconState; busy: host.scanning; anchors.verticalCenter: parent.verticalCenter }
        Column {
            width: parent.width - 58 - checkButton.width - 14; spacing: 3; anchors.verticalCenter: parent.verticalCenter
            Words { width: parent.width; text: host.headline; font.pixelSize: 24; color: host.rows.length ? host.tint(host.verdict.count ? host.verdict.state : "ok") : host.ink }
            Words { width: parent.width; text: host.hostname + " · " + (host.scanning ? "checking…" : host.ago(host.lastScan)); font.pixelSize: 12; color: host.dim }
        }
        DoctorAction { id: checkButton; text: host.scanning ? "Checking…" : "Check now"; enabled: !host.scanning; ink: host.ink; accent: host.good; anchors.verticalCenter: parent.verticalCenter; onClicked: host.scan() }
    }

    Rectangle {
        width: parent.width; visible: host.notice !== ""; height: visible ? noticeText.implicitHeight + 20 : 0; radius: 8
        color: Qt.alpha(host.ink, 0.06)
        Words { id: noticeText; x: 12; y: 10; width: parent.width - 48; text: host.notice; font.pixelSize: 13 }
        Words { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "×"; font.pixelSize: 18; color: host.dim }
        MouseArea { anchors.fill: parent; onClicked: host.notice = "" }
    }

    Words {
        width: parent.width; visible: host.rows.length > 0 && host.problems.length === 0
        text: "Nothing needs your attention. Doctor keeps an eye on things in the background."
        font.pixelSize: 14; color: host.dim
    }

    Repeater {
        model: host.problems
        Rectangle {
            id: problem
            required property var modelData
            readonly property var work: host.fixFor(modelData.id)
            readonly property bool busy: host.busyCheck === modelData.id
            width: pane.width; height: body.implicitHeight + 28; radius: 12
            color: Qt.alpha(host.tint(modelData.state), 0.07); border.color: Qt.alpha(host.tint(modelData.state), 0.45)
            Column {
                id: body; x: 16; y: 14; width: parent.width - 32; spacing: 8
                Row {
                    width: parent.width; spacing: 10
                    Rectangle { width: 9; height: 9; radius: 5; color: host.tint(problem.modelData.state); anchors.verticalCenter: parent.verticalCenter }
                    Words { width: parent.width - 19; text: problem.modelData.title; font.pixelSize: 16 }
                }
                Words { width: parent.width; text: problem.modelData.advice; font.pixelSize: 13; color: host.dim; visible: text !== "" }
                Words {
                    width: parent.width; font.pixelSize: 12; color: host.warning
                    visible: text !== ""
                    text: problem.modelData.came_back ? "This came back after you said it was fine, because it got worse."
                        : problem.work && problem.work.status === "working" ? "Your agent is working on this. Doctor checks again when it's done."
                        : problem.work && problem.work.status === "not_fixed" ? "Your agent finished, but Doctor still sees the problem." : ""
                }
                Flow {
                    width: parent.width; spacing: 8
                    DoctorAction {
                        text: problem.busy ? "Working…" : !host.agentName ? "Choose your agent first" : problem.work ? "Ask my agent again" : "Fix it for me"
                        primary: true; enabled: !problem.busy; ink: host.ink; accent: host.tint(problem.modelData.state)
                        onClicked: host.fix(problem.modelData.id)
                    }
                    DoctorAction { text: "Check again"; visible: !!problem.work; enabled: !problem.busy; ink: host.ink; accent: host.good; onClicked: host.act("recheck", problem.modelData.id) }
                    DoctorAction { text: "It's fine"; enabled: !problem.busy; ink: host.ink; accent: host.good; onClicked: host.act("fine", problem.modelData.id) }
                    DoctorAction { text: host.openDetails[problem.modelData.id] ? "Hide details" : "Details"; ink: host.ink; accent: host.good; onClicked: host.toggleDetails(problem.modelData.id) }
                }
                Column {
                    width: parent.width; spacing: 6; visible: !!host.openDetails[problem.modelData.id]
                    Words { width: parent.width; text: problem.modelData.details; font.pixelSize: 12; color: host.dim; visible: text !== "" }
                    Words { width: parent.width; text: problem.modelData.command ? "To look yourself: " + problem.modelData.command : ""; font.pixelSize: 12; font.family: "monospace"; color: host.dim; visible: text !== "" }
                }
            }
        }
    }

    Rectangle {
        width: parent.width; visible: host.others.length > 0; height: visible ? fineColumn.implicitHeight + 24 : 0; radius: 12
        color: host.card; border.color: host.edge
        Column {
            id: fineColumn; x: 16; y: 12; width: parent.width - 32; spacing: 8
            Item {
                width: parent.width; height: fineHeader.implicitHeight
                Words {
                    id: fineHeader; width: parent.width - 24
                    text: "✓  " + (host.problems.length ? host.others.length + " other check" + (host.others.length === 1 ? " is" : "s are") : "All " + host.others.length + " checks are") + " fine"
                    font.pixelSize: 14; color: host.good
                }
                Words { anchors.right: parent.right; text: host.showFine ? "▾" : "▸"; color: host.dim; font.pixelSize: 14 }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: host.showFine = !host.showFine }
            }
            Repeater {
                model: host.showFine ? host.others : []
                Item {
                    required property var modelData
                    width: fineColumn.width; height: Math.max(line.implicitHeight, undo.visible ? undo.implicitHeight : 0)
                    Words {
                        id: line; width: parent.width - (undo.visible ? undo.width + 8 : 0); font.pixelSize: 12
                        color: modelData.state === "unknown" ? host.dim : host.ink
                        text: modelData.name + " — " + (modelData.dismissed ? "you said this is fine (" + modelData.title.charAt(0).toLowerCase() + modelData.title.slice(1) + ")" : modelData.title)
                    }
                    DoctorAction { id: undo; visible: !!modelData.dismissed; anchors.right: parent.right; text: "Undo"; ink: host.ink; accent: host.warning; onClicked: host.act("notfine", modelData.id) }
                }
            }
        }
    }

    Words {
        width: parent.width; visible: host.recentFixes.length > 0; font.pixelSize: 12; color: host.dim
        text: "Recently fixed: " + host.recentFixes.map(function(f) {
            var r = host.rows.filter(function(x) { return x.id === f.check })[0]
            return (r ? r.name : f.check) + " · " + host.when(f.resolved)
        }).join("   ")
    }

    Item {
        width: parent.width; height: about.implicitHeight
        Words { text: "Doctor " + host.version; font.pixelSize: 11; color: host.dim; anchors.verticalCenter: parent.verticalCenter }
        DoctorAction { id: about; anchors.right: parent.right; text: "About & settings"; ink: host.ink; accent: host.good; onClicked: host.page = "about" }
    }
}
