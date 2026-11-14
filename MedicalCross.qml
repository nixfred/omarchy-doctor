import QtQuick
import qs.Commons
import qs.Commons as Commons

// Bar icon: a medical cross in one of three styles ("outline", "badge",
// "signal"), picked in About & settings. No count text anywhere — unreadable
// at bar height. The outline style keeps one plain corner dot (red/amber)
// when something needs you. The badge and signal styles carry the state in
// their own color, so they show no dot. Dimmed while not checked yet.
//
// Plain Rectangles, not QtQuick.Shapes: the bar fits and centers a custom icon
// by measuring its painted bounds, and the old Shape behind a scaled wrapper
// measured 0x0 — so the icon drew at natural size from the canvas's middle
// instead of centered, sitting low and right of every neighbour.
Item {
    id: root
    property string state: "unknown"
    property int count: 0
    property bool busy: false
    property string style: "outline"
    property var bar: null
    property color ok: "#8fd694"
    property color warn: "#e8b572"
    property color bad: "#ef8a78"
    property color dim: "#7d8590"
    property color ink: bar ? bar.barForeground : Commons.Color.foreground
    readonly property color badFill: bar ? bar.urgent : "#e5484d"
    readonly property color warnFill: "#d4a017"
    readonly property color stateColor: root.state === "bad" ? root.bad : root.state === "warn" ? root.warn : root.state === "ok" ? root.ok : root.dim
    readonly property color badgeFill: root.state === "bad" ? root.badFill : root.state === "warn" ? root.warnFill : root.state === "ok" ? root.ok : root.dim
    readonly property color badgeCross: root.state === "warn" ? "#191b20" : "#ffffff"
    readonly property color frameColor: root.state === "unknown" ? root.dim : root.ink
    readonly property color crossColor: root.style === "signal" ? root.stateColor : root.ink
    readonly property color crossFill: root.style === "badge" ? root.badgeCross : root.crossColor
    readonly property real glyphBase: root.state === "unknown" ? 0.45 : 1.0

    Item {
        id: glyph
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height)
        height: width
        opacity: root.glyphBase

        Rectangle {
            visible: root.style === "badge"
            anchors.fill: parent
            radius: width * 0.22
            color: root.badgeFill
        }

        Rectangle {
            visible: root.style !== "badge"
            anchors.fill: parent
            radius: width * 0.22
            color: "transparent"
            border.width: Math.max(1, Math.round(width * 0.07))
            border.color: root.frameColor
        }

        Rectangle {
            anchors.centerIn: parent
            width: Math.max(2, Math.round(glyph.width * 0.12))
            height: Math.round(glyph.height * 0.49)
            radius: width / 2
            color: root.crossFill
        }
        Rectangle {
            anchors.centerIn: parent
            width: Math.round(glyph.width * 0.49)
            height: Math.max(2, Math.round(glyph.height * 0.12))
            radius: height / 2
            color: root.crossFill
        }

        SequentialAnimation on opacity {
            running: root.busy; loops: Animation.Infinite
            NumberAnimation { to: 0.45; duration: 600; easing.type: Easing.InOutSine }
            NumberAnimation { to: root.glyphBase; duration: 600; easing.type: Easing.InOutSine }
            onRunningChanged: if (!running) glyph.opacity = root.glyphBase
        }
    }

    Rectangle {
        visible: root.style === "outline" && root.count > 0
        anchors.right: parent.right; anchors.bottom: parent.bottom
        width: Math.max(7, Math.round(parent.width * 0.30)); height: width
        radius: width / 2
        color: root.state === "bad" ? root.badFill : root.warnFill
    }
}
