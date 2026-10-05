import QtQuick
import qs.Commons
import QtQuick.Controls
import "Model.js" as Model

Column {
    id:root
    required property var host
    readonly property var graphPoints:graph.points
    spacing:14
    Flow {
        width:parent.width
        spacing:8
        Repeater {
            model:Model.domains
            DoctorAction{required property var modelData;text:modelData.title;selected:host.historyMetric===modelData.metric;ink:host.ink;accent:host.domainTint(modelData.color);onClicked:host.historyMetric=modelData.metric}
        }
        Rectangle{width:1;height:30;color:host.edge}
        Repeater {
            model:[{n:3600,label:"1 hour"},{n:86400,label:"24 hours"},{n:604800,label:"7 days"}]
            DoctorAction{required property var modelData;text:modelData.label;selected:host.historySeconds===modelData.n;ink:host.ink;accent:host.good;onClicked:{host.historySeconds=modelData.n;host.loadHistory()}}
        }
    }
    Rectangle {
        width:parent.width;height:268;radius:12;color:host.card;border.color:host.edge
        Text{font.family:Style.font.family;x:20;y:17;text:"SYSTEM OVER TIME · "+host.historySamples.length+" SAMPLES";color:host.dim;font.pixelSize:11;font.letterSpacing:1.6}
        HistoryGraph{id:graph;x:20;y:39;width:parent.width-40;height:207;samples:host.historySamples;metric:host.historyMetric;unit:host.historyMetric==="ram_available_gib"?"GiB":"%";tint:host.good;ink:host.ink;detailed:true}
    }
    Text{font.family:Style.font.family;width:parent.width;text:"These are recorded system readings, not a prediction or proof of a repair. Doctor records while open; blank stretches mean no readings were collected.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
    Row {
        width:parent.width
        Text{font.family:Style.font.family;width:parent.width-155;text:"PAST CHECKUPS";color:host.dim;font.pixelSize:11;font.letterSpacing:1.6;anchors.verticalCenter:parent.verticalCenter}
        DoctorAction{text:"Export JSON report";ink:host.ink;accent:host.good;onClicked:host.exportReport()}
    }
    Rectangle {
        width:parent.width;height:235;radius:12;color:host.card;border.color:host.edge
        ListView {
            x:10;y:10;width:parent.width-20;height:parent.height-20;clip:true;spacing:6;model:host.scans
            ScrollBar.vertical:ScrollBar{policy:ScrollBar.AsNeeded}
            delegate:Rectangle {
                required property var modelData
                width:ListView.view.width-8;height:48;radius:8;color:scanMouse.containsMouse?Qt.alpha(host.ink,0.08):Qt.alpha(host.ink,0.025)
                Row {
                    x:13;anchors.verticalCenter:parent.verticalCenter;width:parent.width-26;spacing:13
                    Rectangle{width:6;height:6;radius:3;color:host.stateColor(modelData.state);anchors.verticalCenter:parent.verticalCenter}
                    Text{font.family:Style.font.family;width:parent.width*0.48;text:Model.stamp(modelData.timestamp);color:host.ink;font.pixelSize:13}
                    Text{font.family:Style.font.family;width:parent.width*0.18;text:String(modelData.mode||"saved").toUpperCase();color:host.dim;font.pixelSize:11}
                    Text{font.family:Style.font.family;text:Model.labels[modelData.state]+"  →";color:host.stateColor(modelData.state);font.pixelSize:12}
                }
                MouseArea{id:scanMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:{host.archived=modelData;host.filter="all";host.selectedId="";host.page="issues"}}
                activeFocusOnTab:true
                Keys.onReturnPressed:{host.archived=modelData;host.filter="all";host.selectedId="";host.page="issues"}
                Accessible.role:Accessible.Button
                Accessible.name:"Open saved "+modelData.mode+" scan from "+Model.stamp(modelData.timestamp)
            }
        }
        Text{font.family:Style.font.family;anchors.centerIn:parent;visible:!host.scans.length;text:"Your first completed scan becomes the baseline.";color:host.dim;font.pixelSize:13}
    }
}
