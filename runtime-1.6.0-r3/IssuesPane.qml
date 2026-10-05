import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model

Column {
    id:root
    required property var host
    spacing:18
    property alias evidenceOpen:findings.evidenceOpen
    readonly property var repairPane:repairs
    readonly property var graphPane:history
    property bool historyOpen:host.filter==="historical"
    function moveSelection(delta){findings.moveSelection(delta)}
    function selectionGeometry(){return findings.selectionGeometry()}
    readonly property var filters:findings.filters
    Text{font.family:Style.font.family;width:parent.width;text:host.archived?"A past checkup":"Your issues · "+host.hostname;color:host.ink;font.pixelSize:27;wrapMode:Text.WordWrap}
    Text{font.family:Style.font.family;width:parent.width;text:"Start with Needs fixing. Investigate means Doctor needs more evidence. Old events and every repair attempt stay here, even when nothing new happens.";color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap}
    FindingsPane{id:findings;width:parent.width;host:root.host}
    Row {
        width:parent.width;spacing:12
        MedicalCross{width:28;height:28;state:host.selected?host.selected.state:"unknown";anchors.verticalCenter:parent.verticalCenter}
        Column{width:parent.width-40;spacing:4
            Text{font.family:Style.font.family;width:parent.width;text:host.selected?"Work on "+Model.number(host.selected):"Repair records";color:host.ink;font.pixelSize:20}
            Text{font.family:Style.font.family;width:parent.width;text:"An agent's answer is a report. The checks below show what Doctor actually verified.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
        }
    }
    FixesPane{id:repairs;width:parent.width;host:root.host}
    Row {
        width:parent.width;spacing:12
        Text{font.family:Style.font.family;width:parent.width-historyButton.implicitWidth-12;text:"History · what changed over time";color:host.ink;font.pixelSize:20;wrapMode:Text.WordWrap}
        DoctorAction{id:historyButton;text:root.historyOpen?"Hide history":"Show history";ink:host.ink;accent:host.good;onClicked:{root.historyOpen=!root.historyOpen;if(root.historyOpen)host.loadHistory()}}
    }
    HistoryPane{id:history;width:parent.width;host:root.host;visible:root.historyOpen;height:visible?implicitHeight:0}
    Connections{target:host;function onFilterChanged(){if(host.filter==="historical")root.historyOpen=true}}
}
