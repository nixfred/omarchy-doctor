import QtQuick
import QtQuick.Controls
import qs.Commons

Button {
    id: root
    property color ink: Color.popups.text
    property color accent: Color.accent
    property bool selected: false
    property bool primary: false
    implicitHeight: 34
    implicitWidth: caption.implicitWidth + 28
    padding: 0
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    contentItem: Text {
        id: caption
        text: root.text
        color: root.ink
        font.family: Style.font.family
        font.pixelSize: 12
        font.bold: root.primary || root.selected
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        textFormat: Text.PlainText
    }
    background: Rectangle {
        radius: 8
        color: Qt.alpha(root.primary || root.selected ? root.accent : root.ink, root.down ? 0.23 : root.hovered ? 0.13 : root.selected || root.primary ? 0.12 : 0.035)
        border.color: root.activeFocus || root.selected || root.primary ? root.accent : Qt.alpha(root.ink, 0.15)
        border.width: root.activeFocus ? 2 : 1
    }
}
