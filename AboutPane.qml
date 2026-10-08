import QtQuick
import qs.Commons

Column {
    id: pane
    required property var host
    width: parent ? parent.width : 0
    spacing: 16

    component Words: Text { font.family: Style.font.family; color: pane.host.ink; wrapMode: Text.WordWrap; textFormat: Text.PlainText }

    DoctorAction { text: "← Back"; ink: host.ink; accent: host.good; onClicked: host.page = "status" }

    Row {
        width: parent.width; spacing: 16
        MedicalCross { width: 48; height: 48; state: "ok"; anchors.verticalCenter: parent.verticalCenter }
        Column {
            width: parent.width - 64; spacing: 4; anchors.verticalCenter: parent.verticalCenter
            Words { width: parent.width; text: "Omarchy Doctor"; font.pixelSize: 22 }
            Words { width: parent.width; text: "Keeps an eye on your computer and tells you, in plain words, when something needs you."; font.pixelSize: 13; color: host.dim }
        }
    }

    Rectangle {
        width: parent.width; height: how.implicitHeight + 28; radius: 12; color: host.card; border.color: host.edge
        Column {
            id: how; x: 16; y: 14; width: parent.width - 32; spacing: 8
            Words { width: parent.width; text: "Green means there's nothing you need to do. Yellow means something is worth a look. Red means fix it soon. The number is how many things need you."; font.pixelSize: 13 }
            Words { width: parent.width; text: "Fix it for me hands the problem to your coding agent. It asks before anything risky, and the fix only counts once Doctor checks again and sees it's healthy."; font.pixelSize: 13 }
            Words { width: parent.width; text: "It's fine hides a problem until it gets worse. Everything stays on this computer."; font.pixelSize: 13 }
        }
    }

    Rectangle {
        width: parent.width; height: settingsColumn.implicitHeight + 28; radius: 12; color: host.card; border.color: host.edge
        Column {
            id: settingsColumn; x: 16; y: 14; width: parent.width - 32; spacing: 12
            Item {
                width: parent.width; height: autoButton.implicitHeight
                Words { width: parent.width - autoButton.width - 12; text: "Check every 15 minutes in the background"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                DoctorAction { id: autoButton; anchors.right: parent.right; text: host.autoCheck ? "On" : "Off"; selected: host.autoCheck; ink: host.ink; accent: host.good; onClicked: host.saveSetting("autoCheck", !host.autoCheck) }
            }
            Item {
                width: parent.width; height: agentButton.implicitHeight
                Words { width: parent.width - agentButton.width - 12; text: "Agent that fixes things: " + (host.agentName || "none chosen yet"); font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                DoctorAction { id: agentButton; anchors.right: parent.right; text: host.agentName ? "Change" : "Choose"; ink: host.ink; accent: host.good; onClicked: host.chooseAgent() }
            }
        }
    }

    Flow {
        width: parent.width; spacing: 10
        DoctorAction { text: "Source code on GitHub  →"; ink: host.ink; accent: host.good; onClicked: host.openUrl(host.repoUrl) }
        DoctorAction { text: "nixfred.com  →"; ink: host.ink; accent: host.good; onClicked: host.openUrl(host.homeUrl) }
    }
    Words { text: "Doctor " + host.version + " · made by Fred Nix · MIT license"; font.pixelSize: 11; color: host.dim }
}
