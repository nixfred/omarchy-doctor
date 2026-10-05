import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model

Column {
    id: root
    required property var host
    readonly property var work: host.workRecord || ({})
    readonly property var report: work.report || ({})
    readonly property var progress: Model.workState(host.workRecord,host.now)
    readonly property color tint: work.verified?host.good:progress.key==="launch_failed"?host.danger:host.unknown
    spacing: 18
    Rectangle {
        width:parent.width;height:lead.implicitHeight+52;radius:16;color:Qt.alpha(root.tint,0.08);border.color:Qt.alpha(root.tint,0.45)
        Column {
            id:lead;x:26;y:26;width:parent.width-52;spacing:16
            Text{width:parent.width;text:"AGENT HANDOFF  /  "+(root.work.handoff_number||"PREPARING");color:root.tint;font.family:Style.font.family;font.pixelSize:12;font.letterSpacing:2;textFormat:Text.PlainText}
            Text{width:parent.width;text:root.progress.title;color:host.ink;font.family:Style.font.family;font.pixelSize:32;font.bold:true;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
            Text{width:parent.width;text:(root.work.finding_number||root.work.check||"")+" · "+(root.work.title||"Finding");color:host.ink;font.family:Style.font.family;font.pixelSize:20;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
            Flow{width:parent.width;spacing:10
                DoctorAction{objectName:"doctor-work-back";text:"Back to Doctor";ink:host.ink;accent:host.good;primary:true;onClicked:host.leaveWork()}
                DoctorAction{text:"View finding & history";ink:host.ink;accent:host.good;onClicked:host.inspectWork()}
                DoctorAction{text:"View launch log";visible:!!root.work.log_path;enabled:!host.testMode;ink:host.ink;accent:host.unknown;onClicked:host.openWorkLog()}
                DoctorAction{text:"Open agent session";visible:root.work.launch_mode==="background";enabled:!host.testMode&&!root.work.supervisor_alive&&root.work.exit_code!==null&&root.work.exit_code!==undefined&&root.work.exit_code>=0&&!!root.work.session_id;ink:host.ink;accent:host.unknown;onClicked:host.openWorkSession()}
                DoctorAction{text:"Refresh progress";enabled:!host.testMode;ink:host.ink;accent:host.unknown;onClicked:host.loadHistory()}
            }
            Text{width:parent.width;text:root.progress.detail;color:host.dim;font.family:Style.font.family;font.pixelSize:14;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
            Flow{width:parent.width;spacing:10
                Repeater{model:["Agent · "+(root.work.agent||"Not confirmed yet"),"Elapsed · "+Model.workDuration(root.work,host.now),"Stage · "+root.progress.key]
                    Rectangle{required property string modelData;height:32;width:chip.implicitWidth+24;radius:8;color:host.card;border.color:host.edge
                        Text{id:chip;anchors.centerIn:parent;text:modelData;color:host.ink;font.family:Style.font.family;font.pixelSize:12;textFormat:Text.PlainText}
                    }
                }
            }
            Text{width:parent.width;text:"Last saved update · "+Model.stamp(root.work.last_update||root.work.started)+"\n"+(host.workHistoryError?host.workHistoryError:host.workObservedAt?"Progress last checked "+Model.elapsed(host.workObservedAt,host.now)+". Launcher status is an observation, not an agent heartbeat.":"Waiting for saved progress.");color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
            Text{width:parent.width;text:"Launch · "+(root.work.launch_mode==="background"?"Background Codex · no terminal opened":root.work.launch_mode==="custom"?"Custom launcher":"Visible interactive agent session")+(root.work.agent_update?"\nLast agent event · "+root.work.agent_update+" · "+Model.stamp(root.work.agent_update_at):"");color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}

            Text{visible:root.work.launch_mode==="background";width:parent.width;text:"Live events and logs stay accessible here. Open the saved agent session after this run exits if it needs input or review. Doctor never answers security prompts for you.";color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap}
            Text{width:parent.width;text:"You can leave or close this panel. Doctor keeps the handoff and receipts. Returning does not start another agent.";color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap}
        }
    }
    Flow{width:parent.width;spacing:12
        Repeater{model:[{label:root.work.id?"1 · Handoff saved":"1 · Saving handoff",done:!!root.work.id},{label:root.work.report&&root.work.report.outcome?"2 · Agent report received":root.progress.key==="launch_failed"?"2 · No agent report":"2 · Awaiting agent report",done:!!(root.work.report&&root.work.report.outcome)},{label:root.work.verified===true?"3 · Measured healthy":root.progress.key==="launch_failed"?"3 · No verification":(root.work.verifications||[]).length?"3 · Verification unproven":"3 · Verification pending",done:root.work.verified===true}]
            Rectangle{required property var modelData;height:36;width:stage.implicitWidth+26;radius:9;color:host.card;border.color:modelData.done?host.good:host.edge
                Text{id:stage;anchors.centerIn:parent;text:(modelData.done?"✓  ":"○  ")+modelData.label;color:modelData.done?host.good:host.dim;font.family:Style.font.family;font.pixelSize:12}
            }
        }
    }
    Text{width:parent.width;text:"AGENT REPORT · "+(root.work.report&&root.work.report.summary?root.work.report.summary:"No completion report yet.");color:host.ink;font.family:Style.font.family;font.pixelSize:14;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
    Text{visible:!!(root.work.report&&root.work.report.outcome);width:parent.width;text:"Actual changes · "+(root.report.changes||"Not supplied")+"\nAgent validation · "+(root.report.validation||"Not supplied")+"\nUndo guidance · "+(root.report.rollback||"Unknown; review the actual changes before undoing anything.");color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
    Text{width:parent.width;text:"ORIGINAL FINDING · "+Model.stamp(root.work.before_timestamp)+"\n"+(root.work.before_summary||"")+"\n"+(root.work.before_command||"")+"\n"+(root.work.before_evidence||"Original evidence is loading.");color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
    Text{visible:!(root.work.verifications||[]).length;width:parent.width;text:"DOCTOR'S CHECK · No independent verification is saved for this attempt yet. A handoff or agent report alone does not prove repair.";color:host.warning;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap}
    Repeater{model:root.work.verifications||[]
        Text{required property var modelData;width:root.width;text:"DOCTOR'S CHECK · "+Model.stamp(modelData.timestamp)+" · "+modelData.outcome+"\n"+(modelData.row.command||"")+"\n"+(modelData.row.summary||"")+"\n"+(modelData.row.evidence||"No additional output");color:modelData.outcome==="healthy"?host.good:host.warning;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
    }
}
