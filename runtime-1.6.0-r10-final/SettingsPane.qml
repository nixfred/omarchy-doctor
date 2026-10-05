import QtQuick
import qs.Commons
import "Model.js" as Model

Column {
    id:root
    required property var host
    spacing:17
    Text{font.family:Style.font.family;text:"Make Doctor feel right.";color:host.ink;font.pixelSize:27}
    Rectangle {
        width:parent.width;height:148;radius:12;color:host.card;border.color:host.edge
        Column {
            x:20;y:18;width:parent.width-40;spacing:11
            Text{font.family:Style.font.family;text:"COMFORT & MOTION";color:host.dim;font.pixelSize:11;font.letterSpacing:1.7}
            Row {
                spacing:10
                HardwareGlyph{objectName:"doctor-motion-preview";width:48;height:48;kind:"core";surface:host.surface;tint:host.good;animate:host.motion&&host.opened}
                DoctorAction{text:"Gentle movement";selected:host.motion;ink:host.ink;accent:host.good;onClicked:host.saveSetting("motion",true)}
                DoctorAction{text:"Still drawings";selected:!host.motion;ink:host.ink;accent:host.good;onClicked:host.saveSetting("motion",false)}
                Text{font.family:Style.font.family;text:"Stops moving drawings and page fades. Checks keep working.";color:host.dim;font.pixelSize:12;anchors.verticalCenter:parent.verticalCenter}
            }
        }
    }
    Rectangle {
        width:parent.width;height:140;radius:12;color:host.card;border.color:host.edge
        Column {
            x:20;y:18;width:parent.width-40;spacing:11
            Text{font.family:Style.font.family;text:"QUICK CHECKS";color:host.dim;font.pixelSize:11;font.letterSpacing:1.7}
            Row {
                spacing:10
                Repeater {
                    model:[{n:0,label:"Manual"},{n:120,label:"Every 2 minutes"},{n:300,label:"Every 5 minutes"},{n:900,label:"Every 15 minutes"}]
                    DoctorAction{required property var modelData;text:modelData.label;selected:host.refreshSeconds===modelData.n;ink:host.ink;accent:host.good;onClicked:host.saveSetting("refreshSeconds",modelData.n)}
                }
            }
            Text{font.family:Style.font.family;width:parent.width;text:"Only while Doctor is open. Quick checks skip the expensive package-file check. Deep scan checks those files manually; an earlier warning remains until a measured recheck clears it.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
        }
    }
    Rectangle {
        width:parent.width;height:agentInfo.implicitHeight+36;radius:12;color:host.card;border.color:host.edge
        Column{id:agentInfo;x:18;y:18;width:parent.width-36;spacing:10
            Text{font.family:Style.font.family;text:"YOUR AGENT";color:host.dim;font.pixelSize:11;font.letterSpacing:1.5}
            Text{font.family:Style.font.family;text:host.configuredAgent||"No agent selected";color:host.ink;font.pixelSize:19}
            Text{font.family:Style.font.family;width:parent.width;text:"Ask my agent uses Omarchy's chosen assistant. It works under its own permissions. Opening the chooser does not change your selection.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
            DoctorAction{text:"Choose an agent…";ink:host.ink;accent:host.good;onClicked:host.chooseAgent()}
        }
    }
    Rectangle {
        width:parent.width;height:historyInfo.implicitHeight+36;radius:12;color:host.card;border.color:host.edge
        Column{id:historyInfo;x:18;y:18;width:parent.width-36;spacing:10
            Text{font.family:Style.font.family;text:"YOUR HISTORY";color:host.dim;font.pixelSize:11;font.letterSpacing:1.5}
            Text{font.family:Style.font.family;width:parent.width;text:"System readings and checkups: up to 7 days. Repair records and finding numbers: kept for tracking.";color:host.ink;font.pixelSize:13;wrapMode:Text.WordWrap}
            Text{font.family:Style.font.family;width:parent.width;text:"Doctor uses in-app status messages. This version has no separate system-notification switch. Nothing here deletes your history.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
            DoctorAction{text:"Export saved checkups";ink:host.ink;accent:host.good;onClicked:host.exportReport()}
        }
    }
}
