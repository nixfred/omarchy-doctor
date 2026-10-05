import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model
Column {
    id:root
    required property var host
    property bool allRecords:false
    readonly property var records:host.selected&&!allRecords?host.fixes.filter(function(f){return f.check===host.selected.id}):host.fixes
    function showFirstWork(){var item=list.itemAtIndex(0);if(item)item.workOpen=true}
    function workIsOpen(){var item=list.itemAtIndex(0);return !!(item&&item.workOpen)}
    spacing:12
    Flow{width:parent.width;spacing:10
        Text{font.family:Style.font.family;text:root.records.length+" saved attempt(s)";color:host.dim;font.pixelSize:12;height:28;verticalAlignment:Text.AlignVCenter}
        DoctorAction{text:root.allRecords?"This issue only":"All repair records";ink:host.ink;accent:host.good;onClicked:root.allRecords=!root.allRecords}
    }
    Rectangle {
        width:parent.width;height:Math.max(90,Math.min(430,list.contentHeight+20));radius:12;color:host.card;border.color:host.edge
        ListView {
            id:list;x:10;y:10;width:parent.width-20;height:parent.height-20;clip:true;spacing:10;model:root.records
            boundsBehavior:Flickable.StopAtBounds
            ScrollBar.vertical:ScrollBar{policy:ScrollBar.AsNeeded}
            delegate:Rectangle {
                id:record
                required property var modelData
                property bool workOpen:false
                width:ListView.view.width-8;height:body.implicitHeight+28;radius:9;color:Qt.alpha(host.ink,0.025)
                Column {
                    id:body;x:14;y:14;width:parent.width-28;spacing:10
                    Text{font.family:Style.font.family;width:parent.width;text:record.modelData.finding_number+" · "+record.modelData.handoff_number+" · "+record.modelData.title;color:host.ink;font.pixelSize:14;font.bold:true;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Flow {width:parent.width;spacing:8
                        Repeater {model:[{label:"Started",done:true},{label:"Agent report",done:!!(record.modelData.report&&record.modelData.report.summary)},{label:"Doctor verified",done:record.modelData.verified}]
                            Rectangle{required property var modelData;width:stage.implicitWidth+22;height:28;radius:14;color:Qt.alpha(modelData.done?host.good:host.unknown,0.1);border.color:Qt.alpha(modelData.done?host.good:host.unknown,0.3)
                                Text{id:stage;font.family:Style.font.family;anchors.centerIn:parent;text:(modelData.done?"✓ ":"○ ")+modelData.label;color:modelData.done?host.good:host.dim;font.pixelSize:11}
                            }
                        }
                    }
                    Text{font.family:Style.font.family;width:parent.width;text:Model.fixLabel(record.modelData.status);color:record.modelData.verified?host.good:host.warning;font.pixelSize:14;wrapMode:Text.WordWrap}
                    Text{font.family:Style.font.family;width:parent.width;text:record.modelData.report&&record.modelData.report.summary?String(record.modelData.report.summary).slice(0,260)+(String(record.modelData.report.summary).length>260?"…":""):"No answer has returned yet. Doctor has not marked this repaired.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;text:Model.stamp(record.modelData.started)+(record.modelData.agent?" · "+record.modelData.agent:"");color:host.dim;font.pixelSize:11;wrapMode:Text.WordWrap}
                    DoctorAction{text:record.workOpen?"Hide the work":"Show the work";ink:host.ink;accent:host.good;onClicked:record.workOpen=!record.workOpen}
                    Column {
                        width:parent.width;spacing:10;visible:record.workOpen
                        Text{font.family:Style.font.family;width:parent.width;text:"AGENT REPORT · a claim, not proof\n"+(record.modelData.report.summary||"No report returned")+"\n\nActual changes · "+(record.modelData.report.changes||"Not supplied")+"\nUndo guidance · "+(record.modelData.report.rollback||"Unknown. Do not invent an undo step.")+"\nAgent validation · "+(record.modelData.report.validation||"Not supplied");color:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;width:parent.width;text:"BEFORE · "+Model.stamp(record.modelData.before_timestamp)+"\n"+record.modelData.before_summary+"\n"+(record.modelData.before_command||"")+"\n"+(record.modelData.before_evidence||"No additional output");color:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;width:parent.width;text:"AFTER · "+Model.stamp(record.modelData.verified_at)+"\n"+(record.modelData.after_summary||"No independent result yet")+"\n"+(record.modelData.after_command||"")+"\n"+(record.modelData.after_evidence||"No additional output");color:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
                        Repeater {model:record.modelData.verifications||[]
                            Text{required property var modelData;font.family:Style.font.family;width:body.width;text:"DOCTOR'S CHECK · "+Model.stamp(modelData.timestamp)+" · "+modelData.outcome+"\n"+(modelData.row.command||"")+"\n"+modelData.row.summary+"\n"+(modelData.row.evidence||"No additional output");color:modelData.outcome==="healthy"?host.good:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
                        }
                    }
                }
            }
        }
        Text{font.family:Style.font.family;anchors.centerIn:parent;visible:!root.records.length;width:parent.width-32;text:host.selected?"No work has been handed to an agent for this issue.":"Your repair records will appear here.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter}
    }
}
