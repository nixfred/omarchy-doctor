import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model

Column {
    id:root
    required property var host
    spacing:13
    property bool evidenceOpen:false
    readonly property var filters:[{key:"needs_fix",label:"Needs fixing"},{key:"investigate",label:"Investigate"},{key:"historical",label:"History"},{key:"all",label:"All"}]
    readonly property bool wide:width>=800
    function moveSelection(delta){list.move(delta)}
    function selectionGeometry(){var item=list.currentItem;return {index:list.currentIndex,scroll:list.contentY,viewport:list.height,y:item?item.y:0,height:item?item.height:0}}
    Flow {
        objectName:"doctor-finding-filters"
        width:parent.width
        spacing:8
        Repeater {
            model:root.filters
            DoctorAction{required property var modelData;text:modelData.label;selected:host.filter===modelData.key;accent:host.good;ink:host.ink;onClicked:host.filter=modelData.key}
        }
    }
    Row {
        visible:!!host.archived;height:visible?34:0;spacing:12
        Text{font.family:Style.font.family;text:host.archived?"Saved scan · "+Model.stamp(host.archived.timestamp):"";color:host.warning;font.pixelSize:13;anchors.verticalCenter:parent.verticalCenter}
        DoctorAction{text:"Back to current scan";ink:host.ink;accent:host.good;onClicked:host.archived=null}
    }
    Grid {
        width:parent.width;columns:root.wide?2:1;spacing:16
        Rectangle {
            width:root.wide?(parent.width-16)*0.42:parent.width;height:480;radius:12;color:host.card;border.color:host.edge
            ListView {
                id:list;x:8;y:8;width:parent.width-16;height:parent.height-16;clip:true;spacing:7
                model:host.filtered
                currentIndex:{for(var i=0;i<host.filtered.length;i++)if(host.filtered[i].id===host.selectedId)return i;return 0}
                boundsBehavior:Flickable.StopAtBounds
                ScrollBar.vertical:ScrollBar{policy:ScrollBar.AsNeeded}
                keyNavigationEnabled:false
                function move(delta){if(!count)return;var index=Math.max(0,Math.min(count-1,currentIndex+delta));host.selectedId=host.filtered[index].id;positionViewAtIndex(index,ListView.Contain)}
                Keys.onDownPressed:move(1)
                Keys.onUpPressed:move(-1)
                activeFocusOnTab:true
                delegate:Rectangle {
                    id:row
                    required property var modelData
                    required property int index
                    width:list.width-7;height:rowBody.implicitHeight+24;radius:9
                    color:host.selected&&host.selected.id===modelData.id?Qt.alpha(host.stateColor(modelData.state),0.10):Qt.alpha(host.ink,0.02)
                    border.color:host.selected&&host.selected.id===modelData.id?Qt.alpha(host.stateColor(modelData.state),0.6):"transparent"
                    Column {
                        id:rowBody;x:13;y:12;width:parent.width-26;spacing:7
                        Row {
                            width:parent.width;spacing:8
                            Rectangle{width:6;height:6;radius:3;color:host.stateColor(row.modelData.state);anchors.verticalCenter:parent.verticalCenter}
                            Text{font.family:Style.font.family;width:parent.width-14;text:Model.number(row.modelData)+" · "+row.modelData.title;color:host.ink;font.pixelSize:13;font.bold:true;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                        }
                        Text{font.family:Style.font.family;width:parent.width;text:row.modelData.summary;color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;width:parent.width;text:(row.modelData.severity||row.modelData.state).toUpperCase()+" · "+Model.disposition(row.modelData)+"\n"+(row.modelData.activity?row.modelData.activity.toUpperCase():Model.labels[row.modelData.state].toUpperCase())+(row.modelData.change?" · "+row.modelData.change.toUpperCase():"");color:host.stateColor(row.modelData.state);font.pixelSize:10;font.letterSpacing:1;wrapMode:Text.WordWrap}
                    }
                    MouseArea{anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;onClicked:function(mouse){host.selectedId=row.modelData.id;list.forceActiveFocus();if(mouse.button===Qt.RightButton)host.copyCommand(row.modelData.command)}}
                    Accessible.role:Accessible.ListItem
                    Accessible.name:modelData.title+". "+Model.labels[modelData.state]+". "+modelData.summary
                }
            }
            Text{font.family:Style.font.family;anchors.centerIn:parent;visible:!host.filtered.length;text:host.scanning?"Checks will appear as they finish…":host.filter==="needs_fix"?"No unresolved repair in this view. Investigate has checks that need more evidence.":"No issues in this view.";color:host.dim;font.pixelSize:13}
        }
        Rectangle {
            width:root.wide?(parent.width-16)*0.58:parent.width;height:480;radius:12;color:host.card;border.color:host.edge
            Flickable {
                id:evidence;x:21;y:20;width:parent.width-42;height:parent.height-40;contentWidth:width;contentHeight:details.implicitHeight;clip:true
                boundsBehavior:Flickable.StopAtBounds
                ScrollBar.vertical:ScrollBar{policy:ScrollBar.AsNeeded}
                Connections{target:host;function onSelectedChanged(){evidence.contentY=0;root.evidenceOpen=false}}
                Column {
                    id:details;width:evidence.width;spacing:13
                    Text{font.family:Style.font.family;text:"WHAT HAPPENED";color:host.dim;font.pixelSize:11;font.letterSpacing:1.8}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?Model.number(host.selected)+" · "+host.selected.title:"Choose an issue";color:host.ink;font.pixelSize:25;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?Model.labels[host.selected.state]+" · "+Model.stamp(host.selected.timestamp)+" · "+((host.selected.duration_ms||0)/1000).toFixed(2)+"s":"Run Doctor to collect evidence.";color:host.selected?host.stateColor(host.selected.state):host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
                    Text{font.family:Style.font.family;width:parent.width;visible:!!(host.selected&&host.selected.coverage_note);text:host.selected?(host.selected.coverage_note||""):"";color:host.warning;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?host.selected.summary:"";color:host.ink;font.pixelSize:13;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;visible:!!host.selected&&host.selected.state!=="ok";text:"Cause · not independently confirmed. An agent’s diagnosis appears in the repair record.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?(host.selected.needs_fix?"Why it needs attention · ":"What we know · ")+(host.selected.diagnosis||"Cause not established. Open the evidence to investigate."):"";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;visible:root.evidenceOpen;text:host.selected?"Source · "+(host.selected.evidence_source||host.selected.command||"Unavailable")+"\nEvidence time · "+Model.stamp(host.selected.evidence_timestamp||host.selected.timestamp)+"\nWhy it matters · "+(host.selected.rationale||"Diagnosis pending"):"";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text {
                        font.family:Style.font.family;width:parent.width;visible:root.evidenceOpen&&!!(host.selected&&host.selected.signature)
                        text:host.selected&&host.selected.signature?"SIGNATURE · "+host.selected.id+"\nFirst seen · "+Model.stamp(host.selected.first_seen)+"\nLast seen · "+Model.stamp(host.selected.last_seen)+"\nObserved events · "+host.selected.event_count+" · "+host.selected.new_count+" new on this check\n"+(host.selected.activity==="recurring"?"RECURRING: a new event matches an earlier observed cause.":host.selected.activity==="new"?"NEW: a new event appeared after the previous check.":"HISTORICAL: rescanning old evidence does not mean it happened again."):""
                        color:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText
                    }
                    Rectangle {
                        id:fixBox;width:parent.width;visible:host.fixable(host.selected);height:visible?fixColumn.implicitHeight+24:0;radius:8
                        color:Qt.alpha(host.unknown,0.06);border.color:Qt.alpha(host.unknown,0.25)
                        readonly property var open:host.selected?host.openFix(host.selected.id):null
                        Column {
                            id:fixColumn;x:12;y:12;width:parent.width-24;spacing:9
                            Text{
                                font.family:Style.font.family
                                width:parent.width;color:host.ink;font.pixelSize:13;wrapMode:Text.WordWrap
                                text:fixBox.open?fixBox.open.handoff_number+" · "+Model.fixLabel(fixBox.open.status)+"\n"+(fixBox.open.report&&fixBox.open.report.summary?"The agent's report and Doctor's checks are in the repair record below.":"Waiting for the agent's answer. Doctor has not marked this repaired.") :"Your chosen agent can investigate this issue. Its answer and Doctor's recheck will stay here."
                            }
                            Row {
                                spacing:8
                                DoctorAction{text:host.fixingId===(host.selected?host.selected.id:"")?"Working…":fixBox.open?"Hand to agent again":"Ask my agent";primary:true;enabled:host.fixingId==="";ink:host.ink;accent:host.unknown;onClicked:host.fixIssue(host.selected.id)}
                                DoctorAction{text:"Recheck";enabled:host.fixingId===""&&!host.scanning;ink:host.ink;accent:host.good;onClicked:host.recheck(host.selected.id)}
                            }
                        }
                    }
                    DoctorAction{text:root.evidenceOpen?"Hide evidence":"Show evidence & diagnosis";ink:host.ink;accent:host.good;onClicked:root.evidenceOpen=!root.evidenceOpen}
                    Text{font.family:Style.font.family;width:parent.width;visible:root.evidenceOpen&&!!host.selected&&!host.archived;text:"YOUR DIAGNOSIS · This assessment controls Needs fixing; it never marks a repair verified.";color:host.dim;font.pixelSize:11;wrapMode:Text.WordWrap}
                    TextField{id:assessmentReason;width:parent.width;visible:root.evidenceOpen&&!!host.selected&&!host.archived;placeholderText:"Diagnosis and supporting evidence";color:host.ink;selectByMouse:true;font.family:Style.font.family;background:Rectangle{radius:6;color:Qt.alpha(host.ink,0.04);border.color:host.edge}}
                    Connections{target:host;function onSelectedChanged(){assessmentReason.text=""}}
                    Flow{width:parent.width;spacing:8;visible:!!host.selected&&!host.archived
                        Repeater{model:[{key:"needs_fix",label:"Needs fixing"},{key:"investigate",label:"Investigate"},{key:"monitor",label:"Monitor"},{key:"benign",label:"Harmless"}]
                            DoctorAction{required property var modelData;text:modelData.label;enabled:assessmentReason.text.trim().length>0;ink:host.ink;accent:host.good;onClicked:host.assessFinding(host.selected.id,modelData.key,assessmentReason.text)}
                        }
                    }
                    Rectangle{width:parent.width;height:1;color:host.edge}
                    Text{font.family:Style.font.family;text:"INSPECT IT YOURSELF";color:host.dim;font.pixelSize:11;font.letterSpacing:1.6;visible:root.evidenceOpen&&host.selected&&!!host.selected.command}
                    Rectangle {
                        width:parent.width;height:commandText.implicitHeight+24;radius:8;color:Qt.alpha(host.ink,0.035)
                        visible:root.evidenceOpen&&host.selected&&!!host.selected.command
                        Text{id:commandText;x:12;y:12;width:parent.width-24;text:host.selected?(host.selected.command||""):"";color:host.good;font.family:"monospace";font.pixelSize:13;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText}
                    }
                    DoctorAction{text:"Copy diagnostic command";visible:root.evidenceOpen&&host.selected&&!!host.selected.command;ink:host.ink;accent:host.good;onClicked:host.copyCommand(host.selected.command)}
                    Text{visible:root.evidenceOpen;font.family:Style.font.family;text:"Clicking an issue runs nothing. Only Fix with agent starts anything.";color:host.dim;font.pixelSize:11}
                    Text{visible:root.evidenceOpen;font.family:Style.font.family;text:"COLLECTED OUTPUT";color:host.dim;font.pixelSize:11;font.letterSpacing:1.6}
                    Text{visible:root.evidenceOpen;width:parent.width;text:host.selected?(host.selected.evidence||"This check did not produce additional output."):"";color:host.dim;font.family:"monospace";font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText;lineHeight:1.25}
                }
            }
        }
    }
}
