import QtQuick
import qs.Commons

// Bar icon: a white medical cross on a solid badge whose color is the verdict
// (green healthy, amber attention, red problem, gray not yet known), with the
// number of current actionable faults in a pill on the corner.
Item {
    id: root
    property string state: "unknown"
    property int count: 0
    property bool busy: false
    readonly property color symbol: state==="warn"?"#191b20":"#ffffff"
    readonly property color fill: state === "bad" ? "#e5484d" : state === "warn" ? "#d4a017" : state === "ok" ? "#2fa84f" : "#7d8590"

    Rectangle{anchors.centerIn:parent;width:parent.width*1.16;height:width;radius:width*0.28;color:root.state==="ok"?Qt.alpha(root.fill,0.16):"transparent";border.width:1;border.color:root.state==="ok"?Qt.alpha(root.fill,0.25):"transparent"}
    Rectangle {
        id: badge
        anchors.centerIn: parent
        width: Math.round(parent.width * 1.0); height: width
        radius: width * 0.24
        color: root.fill
        border.width: 1
        border.color: Qt.darker(root.fill, 1.35)
        Rectangle {
            anchors.centerIn: parent
            width: Math.max(2, Math.round(parent.width * 0.22)); height: Math.round(parent.height * 0.64)
            radius: width * 0.25; color: root.symbol
        }
        Rectangle {
            anchors.centerIn: parent
            width: Math.round(parent.width * 0.64); height: Math.max(2, Math.round(parent.height * 0.22))
            radius: height * 0.25; color: root.symbol
        }
        SequentialAnimation on opacity {
            running: root.busy; loops: Animation.Infinite
            NumberAnimation { to: 0.55; duration: 600; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1; duration: 600; easing.type: Easing.InOutSine }
            onRunningChanged: if (!running) badge.opacity = 1
        }
    }

    Rectangle {
        visible: root.count > 0
        anchors.right: parent.right; anchors.top: parent.top
        anchors.rightMargin: -Math.round(width * 0.7); anchors.topMargin: -Math.round(height * 0.45)
        height: Math.max(11, Math.round(parent.height * 0.56)); width: Math.max(height, label.implicitWidth + 6)
        radius: height / 2
        color: "#ffffff"
        border.width: 1; border.color: Qt.darker(root.fill, 1.2)
        Text {
            id: label
            anchors.centerIn: parent
            text: root.count > 99 ? "99+" : String(root.count)
            color: Qt.darker(root.fill, 1.25)
            font.family: Style.font.family
            font.pixelSize: Math.max(8, Math.round(parent.height * 0.78))
            font.bold: true
        }
    }
}
