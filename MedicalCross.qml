import QtQuick
import QtQuick.Shapes
import qs.Commons

// Bar icon: a medical cross in one of three styles ("outline", "badge",
// "signal"), picked in About & settings. No count text anywhere — unreadable
// at bar height. The outline style keeps one plain corner dot (red/amber)
// when something needs you. The badge and signal styles carry the state in
// their own color, so they show no dot. Dimmed while not checked yet.
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
    property color ink: bar ? bar.barForeground : Color.foreground
    readonly property color badFill: bar ? bar.urgent : "#e5484d"
    readonly property color warnFill: "#d4a017"
    readonly property color stateColor: root.state === "bad" ? root.bad : root.state === "warn" ? root.warn : root.state === "ok" ? root.ok : root.dim
    readonly property color badgeFill: root.state === "bad" ? root.badFill : root.state === "warn" ? root.warnFill : root.state === "ok" ? root.ok : root.dim
    readonly property color badgeCross: root.state === "warn" ? "#191b20" : "#ffffff"
    readonly property color frameColor: root.state === "unknown" ? root.dim : root.ink
    readonly property color crossColor: root.style === "signal" ? root.stateColor : root.ink
    readonly property real glyphBase: root.state === "unknown" ? 0.45 : 1.0

    Item {
        id: glyph
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height)
        height: width
        opacity: root.glyphBase

        // 100-unit SVG box scaled to fit: visual size always equals glyph.
        Item {
            width: 100; height: 100
            scale: glyph.width / 100
            transformOrigin: Item.TopLeft
            visible: root.style !== "badge"
            Shape {
                width: 100; height: 100
                antialiasing: true
                layer.enabled: true
                layer.samples: 4
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: root.frameColor
                    strokeWidth: 6
                    PathSvg { path: "M 32 10 H 68 A 22 22 0 0 1 90 32 V 68 A 22 22 0 0 1 68 90 H 32 A 22 22 0 0 1 10 68 V 32 A 22 22 0 0 1 32 10 Z" }
                }
                ShapePath {
                    fillColor: "transparent"
                    strokeColor: root.crossColor
                    strokeWidth: 10
                    capStyle: ShapePath.RoundCap
                    PathSvg { path: "M 50 34 V 66 M 34 50 H 66" }
                }
            }
        }

        Rectangle {
            visible: root.style === "badge"
            anchors.centerIn: parent
            width: glyph.width; height: width
            radius: width * 0.22
            color: root.badgeFill
            Rectangle {
                anchors.centerIn: parent
                width: Math.max(2, Math.round(parent.width * 0.20)); height: Math.round(parent.height * 0.52)
                radius: width * 0.25; color: root.badgeCross
            }
            Rectangle {
                anchors.centerIn: parent
                width: Math.round(parent.width * 0.52); height: Math.max(2, Math.round(parent.height * 0.20))
                radius: height * 0.25; color: root.badgeCross
            }
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
