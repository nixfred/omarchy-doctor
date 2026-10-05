import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model

Column {
    id:root
    required property var host
    spacing:12
    property string section:"findings"
    property alias evidenceOpen:findings.evidenceOpen
    readonly property var repairPane:repairs
    readonly property var graphPane:history
    property bool historyOpen:host.filter==="historical"
    function moveSelection(delta){findings.moveSelection(delta)}
    function selectionGeometry(){return findings.selectionGeometry()}
    readonly property var filters:findings.filters
    Text{font.family:Style.font.family;width:parent.width;text:host.archived?"A past checkup":"Your issues · "+host.hostname;color:host.ink;font.pixelSize:27;wrapMode:Text.WordWrap}
    Text{font.family:Style.font.family;width:parent.width;text:Model.issueSummary(host.viewRows||host.shownRows||host.results,host.complete,!!host.archived,host.now)+" Past events and repair attempts stay here for review.";color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap}
    Flow{width:parent.width;spacing:8
        DoctorAction{text:"Findings";selected:root.section==="findings";ink:host.ink;accent:host.good;onClicked:root.section="findings"}
        DoctorAction{text:"Repair records";selected:root.section==="repairs";ink:host.ink;accent:host.good;onClicked:root.section="repairs"}
        DoctorAction{text:"Checkup history";selected:root.section==="history";ink:host.ink;accent:host.good;onClicked:{root.section="history";host.loadHistory()}}
    }
    FindingsPane{id:findings;width:parent.width;host:root.host;visible:root.section==="findings"}
    Row {
        width:parent.width;spacing:12;visible:root.section==="repairs"
        MedicalCross{width:28;height:28;state:host.selected?host.selected.state:"unknown";anchors.verticalCenter:parent.verticalCenter}
        Column{width:parent.width-40;spacing:4
            Text{font.family:Style.font.family;width:parent.width;text:host.selected?"Repair history for "+Model.number(host.selected):"Repair records";color:host.ink;font.pixelSize:20}
            Text{font.family:Style.font.family;width:parent.width;text:"An agent's answer is a report. The checks below show what Doctor actually verified.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
        }
    }
    FixesPane{id:repairs;width:parent.width;host:root.host;visible:root.section==="repairs"}
    HistoryPane{id:history;width:parent.width;host:root.host;visible:root.section==="history"}
    Connections{target:host;function onFilterChanged(){if(host.filter==="historical"){root.historyOpen=true;root.section="findings"}}}
}
