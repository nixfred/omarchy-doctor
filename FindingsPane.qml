import QtQuick
import QtQuick.Controls
import qs.Commons
import "Model.js" as Model

Column {
    id:root
    objectName:"doctor-findings-pane"
    required property var host
    spacing:13
    property int findingPage:0
    readonly property int perPage:Math.max(1,Math.floor((cardHeight-70)/170))
    readonly property int findingPages:Math.max(1,Math.ceil(host.filtered.length/perPage))
    onFindingPagesChanged:findingPage=Math.min(findingPage,findingPages-1)
    function syncSelection(){var selected=host.selected;for(var i=0;i<host.filtered.length;i++)if(selected&&host.filtered[i].id===selected.id){root.findingPage=Math.floor(i/root.perPage);return}root.findingPage=0}
    function pageFindings(delta){root.findingPage=Math.max(0,Math.min(root.findingPages-1,root.findingPage+delta));var row=host.filtered[root.findingPage*root.perPage];if(row)host.selectedId=row.id}
    onPerPageChanged:syncSelection()
    Connections{target:host;function onFilterChanged(){root.syncSelection()} function onFilteredChanged(){root.syncSelection();if(!host.selected)root.showDetail=false} function onSelectedIdChanged(){root.syncSelection();root.showDetail=!!host.selected}}

    property bool evidenceOpen:false
    property bool showDetail:!!host.selected
    readonly property real cardHeight:Math.min(480,Math.max(240,(host.readingHeight||580)-230))
    readonly property var filters:[{key:"needs_fix",label:"Needs fixing"},{key:"investigate",label:"Investigate"},{key:"notes",label:"Log notes"},{key:"historical",label:"History"},{key:"all",label:"All"}]
    readonly property bool wide:width>=800
    function moveSelection(delta){list.move(delta)}
    function selectionGeometry(){var item=list.currentItem;return {index:list.currentIndex,scroll:list.contentY,viewport:list.height,y:item?item.y:0,height:item?item.height:0}}
    Flow {
        objectName:"doctor-finding-filters"
        width:parent.width
        spacing:8
        DoctorAction{visible:!root.wide;text:root.showDetail?"Findings list":"Selected finding";enabled:root.showDetail||!!host.selected;ink:host.ink;accent:host.good;onClicked:root.showDetail=!root.showDetail}
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
            width:root.wide?(parent.width-16)*0.42:parent.width;height:root.cardHeight;radius:12;color:host.card;border.color:host.edge
            visible:root.wide||!root.showDetail
            ListView {
                id:list;x:8;y:8;width:parent.width-16;height:parent.height-60;clip:true;spacing:7
                model:host.filtered.slice(root.findingPage*root.perPage,(root.findingPage+1)*root.perPage)
                currentIndex:{for(var i=0;i<model.length;i++)if(model[i].id===host.selectedId)return i;return 0}
                boundsBehavior:Flickable.StopAtBounds
                interactive:false
                keyNavigationEnabled:false
                function move(delta){if(!host.filtered.length)return;var index=root.findingPage*root.perPage+currentIndex;index=Math.max(0,Math.min(host.filtered.length-1,index+delta));root.findingPage=Math.floor(index/root.perPage);host.selectedId=host.filtered[index].id}
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
                            Text{font.family:Style.font.family;width:parent.width-14;text:Model.number(row.modelData)+" · "+row.modelData.title;color:host.ink;font.pixelSize:13;font.bold:true;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight;textFormat:Text.PlainText}
                        }
                        Text{font.family:Style.font.family;width:parent.width;text:row.modelData.summary;color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;width:parent.width;text:Model.disposition(row.modelData,host.now);color:Model.quietNote(row.modelData)&&!row.modelData.needs_fix?host.dim:host.stateColor(row.modelData.state);font.pixelSize:10;font.letterSpacing:1;wrapMode:Text.WordWrap}
                    }
                    MouseArea{anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;onClicked:function(mouse){host.selectedId=row.modelData.id;root.showDetail=true;list.forceActiveFocus();if(mouse.button===Qt.RightButton)host.copyCommand(row.modelData.command)}}
                    Accessible.role:Accessible.ListItem
                    Accessible.name:modelData.title+". "+Model.labels[modelData.state]+". "+modelData.summary
                }
            }
            Row{anchors.bottom:parent.bottom;anchors.bottomMargin:8;x:8;spacing:8;visible:host.filtered.length>0
                DoctorAction{text:"Previous";enabled:root.findingPage>0;ink:host.ink;accent:host.good;onClicked:root.pageFindings(-1)}
                Text{text:(root.findingPage+1)+" / "+root.findingPages;color:host.dim;font.family:Style.font.family;font.pixelSize:12;height:34;verticalAlignment:Text.AlignVCenter}
                DoctorAction{text:"Next";enabled:root.findingPage+1<root.findingPages;ink:host.ink;accent:host.good;onClicked:root.pageFindings(1)}
            }
            Column {
                anchors.centerIn:parent;width:Math.max(0,parent.width-32);visible:!host.filtered.length;spacing:12
                Text{objectName:"doctor-empty-findings";font.family:Style.font.family;width:parent.width;text:host.scanning?"Checks will appear as they finish…":host.filter==="needs_fix"?Model.issueSummary(host.viewRows||host.shownRows||host.results,host.complete,!!host.archived,host.now):"No findings in this view.";color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter;textFormat:Text.PlainText}
                DoctorAction{objectName:"doctor-empty-verification";anchors.horizontalCenter:parent.horizontalCenter;text:"Finish verification";visible:host.filter==="needs_fix"&&!host.archived&&host.overallState==="unknown";ink:host.ink;accent:host.unknown;onClicked:host.routeConcern()}
            }
        }
        Rectangle {
            width:root.wide?(parent.width-16)*0.58:parent.width;height:root.cardHeight;radius:12;color:host.card;border.color:host.edge
            visible:root.wide||root.showDetail
            ReadPages {
                id:evidence;x:21;y:20;width:parent.width-42;height:parent.height-40;ink:host.ink;accent:host.good
                Connections{target:host;function onSelectedChanged(){evidence.reset();root.evidenceOpen=false}}
                Column {
                    id:details;width:evidence.width;spacing:13
                    Text{font.family:Style.font.family;text:"WHAT HAPPENED";color:host.dim;font.pixelSize:11;font.letterSpacing:1.8}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?Model.number(host.selected)+" · "+host.selected.title:"Choose an issue";color:host.ink;font.pixelSize:25;wrapMode:Text.WordWrap;maximumLineCount:3;elide:Text.ElideRight;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?Model.labels[host.selected.state]+" · "+Model.stamp(host.selected.timestamp)+" · "+((host.selected.duration_ms||0)/1000).toFixed(2)+"s":"Run Doctor to collect evidence.";color:host.selected?host.stateColor(host.selected.state):host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
                    Flow {
                                width:parent.width;spacing:8;visible:host.fixable(host.selected)
                                DoctorAction{text:host.fixingId===(host.selected?host.selected.id:"")?"Working…":fixBox.open&&Model.workActive(fixBox.open,host.now)?"View agent progress":fixBox.open?"Hand to agent again":host.selected&&host.selected.needs_fix?"Ask my agent":"Ask agent to review";visible:!!host.selected&&host.selected.state!=="unknown"&&host.selected.evidence_kind!=="test_event";primary:!!host.selected&&host.selected.needs_fix;enabled:host.fixingId==="";ink:host.ink;accent:host.unknown;onClicked:host.fixIssue(host.selected.id)}
                                DoctorAction{text:host.selected&&host.selected.state==="unknown"&&(host.selected.id==="shell"||host.selected.id==="packages"||host.selected.id==="journal")?"Finish verification":"Recheck";enabled:host.fixingId===""&&!host.scanning;ink:host.ink;accent:host.good;onClicked:{if(host.selected.state==="unknown"&&(host.selected.id==="shell"||host.selected.id==="packages"||host.selected.id==="journal"))host.navigate("verification");else host.recheck(host.selected.id)}}
                            }
                    Text{font.family:Style.font.family;width:parent.width;visible:!!(host.selected&&host.selected.coverage_note);text:host.selected?(host.selected.coverage_note||""):"";color:host.warning;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{visible:!!host.selected&&host.selected.evidence_kind==="log_warning";width:parent.width;text:host.selected?"Recorded log level · "+(host.selected.log_level||"warning")+". Functional impact and repair need have not been established.":"";color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{objectName:"doctor-next-action";font.family:Style.font.family;width:parent.width;text:Model.nextAction(host.selected);color:host.unknown;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?host.selected.summary:"";color:host.ink;font.pixelSize:13;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;visible:!!host.selected&&host.selected.state!=="ok";text:"Cause · not independently confirmed. An agent’s diagnosis appears in the repair record.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap}
                    Text{font.family:Style.font.family;width:parent.width;text:host.selected?(host.selected.needs_fix?"Why it needs attention · ":"What we know · ")+(host.selected.diagnosis||"Cause not established. Open the evidence to investigate."):"";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{font.family:Style.font.family;width:parent.width;visible:root.evidenceOpen;text:host.selected?"Full finding title · "+host.selected.title+"\nSource · "+(host.selected.evidence_source||host.selected.command||"Unavailable")+"\nEvidence time · "+Model.stamp(host.selected.evidence_timestamp||host.selected.timestamp)+"\nWhy it matters · "+(host.selected.rationale||"Diagnosis pending"):"";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text {
                        font.family:Style.font.family;width:parent.width;visible:root.evidenceOpen&&!!(host.selected&&host.selected.signature)
                        text:host.selected&&host.selected.signature?"SIGNATURE · "+host.selected.id+"\nFirst seen · "+Model.stamp(host.selected.first_seen)+"\nLast seen · "+Model.stamp(host.selected.last_seen)+"\nObserved events · "+host.selected.event_count+" · "+host.selected.new_count+" new on this check\n"+(host.selected.activity==="recurring"?"RECURRING: a new event matches an earlier observed cause.":host.selected.activity==="new"?"NEW: a new event appeared after the previous check.":"HISTORICAL: rescanning old evidence does not mean it happened again."):""
                        color:host.dim;font.pixelSize:12;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText
                    }
                    Text{visible:root.evidenceOpen&&!!(host.selected&&host.selected.related_prior_numbers&&host.selected.related_prior_numbers.length);width:parent.width;text:host.selected?"Prior finding records retained · "+(host.selected.related_prior_numbers||[]).join(", "):"";color:host.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Text{visible:!!(host.selected&&host.selected.recovery);width:parent.width;text:host.selected&&host.selected.recovery?(host.selected.recovery.kind==="without_handoff"?"RECOVERED WITHOUT A DOCTOR HANDOFF":"MEASURED RECOVERY · CAUSE UNPROVEN")+" · "+Model.stamp(host.selected.recovery.timestamp)+"\nA valid healthy measurement cleared the active concern. Earlier warning and recovery evidence remain in history.":"";color:host.good;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Rectangle {
                        id:fixBox;width:parent.width;visible:host.fixable(host.selected)&&host.selected.state!=="unknown"&&host.selected.evidence_kind!=="test_event";height:visible?fixColumn.implicitHeight+24:0;radius:8
                        color:Qt.alpha(host.unknown,0.06);border.color:Qt.alpha(host.unknown,0.25)
                        readonly property var open:host.selected?host.openFix(host.selected.id):null
                        Column {
                            id:fixColumn;x:12;y:12;width:parent.width-24;spacing:9
                            Text{
                                font.family:Style.font.family
                                width:parent.width;color:host.ink;font.pixelSize:13;wrapMode:Text.WordWrap
                                text:fixBox.open?fixBox.open.handoff_number+" · "+Model.fixLabel(fixBox.open.status)+"\n"+(fixBox.open.report&&fixBox.open.report.summary?"The agent's report and Doctor's checks are in the repair record below.":"Waiting for the agent's answer. Doctor has not marked this repaired.") :"Your chosen agent can investigate this issue. Its answer and Doctor's recheck will stay here."
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
