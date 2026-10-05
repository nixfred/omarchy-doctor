import QtQuick
import qs.Commons

Column {
    id:root
    required property var host
    spacing:18
    Row {
        width:parent.width;spacing:20
        MedicalCross{width:62;height:62;state:"ok";anchors.verticalCenter:parent.verticalCenter}
        Column{width:parent.width-82;spacing:8
            Text{font.family:Style.font.family;text:"OMARCHY DOCTOR · "+host.version;color:host.dim;font.pixelSize:11;font.letterSpacing:1.6}
            Text{font.family:Style.font.family;width:parent.width;text:"A little help keeping your desktop healthy.";color:host.ink;font.pixelSize:27;wrapMode:Text.WordWrap}
            Text{font.family:Style.font.family;width:parent.width;text:"Check your system, understand a warning, and see the work behind a repair.";color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap}
        }
    }
    Grid {
        width:parent.width;columns:width>=720?3:1;spacing:14
        Repeater {
            model:[{n:"1",title:"Check",body:"Doctor reads 16 system checks. Missing evidence stays unknown.",state:"ok"},{n:"2",title:"Understand",body:"Issues explains what happened and keeps the evidence behind it.",state:"warn"},{n:"3",title:"Verify",body:"Your agent reports its work. Doctor checks the result before calling it healthy.",state:"unknown"}]
            Rectangle {
                required property var modelData
                width:(parent.width-(parent.columns-1)*14)/parent.columns;height:190;radius:14;color:host.card;border.color:host.edge
                Column{x:20;y:20;width:parent.width-40;spacing:12
                    Row{spacing:10
                        MedicalCross{width:30;height:30;state:modelData.state}
                        Text{font.family:Style.font.family;text:modelData.n+" / "+modelData.title;color:host.ink;font.pixelSize:20;anchors.verticalCenter:parent.verticalCenter}
                    }
                    Text{font.family:Style.font.family;width:parent.width;text:modelData.body;color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap}
                }
            }
        }
    }
    Rectangle {
        width:parent.width;height:trust.implicitHeight+36;radius:12;color:host.card;border.color:host.edge
        Column{id:trust;x:18;y:18;width:parent.width-36;spacing:8
            Text{font.family:Style.font.family;text:"Local. Clear. Your choice.";color:host.ink;font.pixelSize:17}
            Text{font.family:Style.font.family;width:parent.width;text:"Checks and repair records stay on this computer. Doctor's checks read only. Fix with agent lets your chosen agent make changes under its own permission settings.";color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap}
            Text{font.family:Style.font.family;width:parent.width;text:"A quiet log or an agent saying “done” is not proof of a repair.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
        }
    }
    Flow{width:parent.width;spacing:10
        DoctorAction{text:"Source code  →";ink:host.ink;accent:host.good;onClicked:host.openUrl(host.repoUrl)}
        DoctorAction{text:"nixfred.com  →";ink:host.ink;accent:host.good;onClicked:host.openUrl(host.homeUrl)}
    }
    Text{font.family:Style.font.family;text:"Made by Fred Nix · MIT license";color:host.dim;font.pixelSize:11}
}
