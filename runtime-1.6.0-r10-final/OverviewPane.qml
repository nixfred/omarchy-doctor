import QtQuick
import qs.Commons
import "Model.js" as Model

Column {
    id: root
    required property var host
    spacing:14
    property int section:0
    Flow{width:parent.width;spacing:8
        Repeater{model:["Summary","Vital signs","System map"]
            DoctorAction{required property string modelData;required property int index;text:modelData;selected:root.section===index;ink:host.ink;accent:host.good;onClicked:root.section=index}
        }
    }
    readonly property bool wide:width>=850
    Grid {
        width:parent.width;columns:1;spacing:14;visible:root.section===0||root.section===2
        Rectangle {
            visible:root.section===2;width:parent.width;height:355;radius:13
            color:host.card; border.color:host.edge
            Rectangle{anchors.fill:parent;radius:parent.radius;color:host.overallState==="ok"?Qt.alpha(host.good,0.07):"transparent";border.width:2;border.color:host.overallState==="ok"?Qt.alpha(host.good,0.22):"transparent"}
            Text {font.family:Style.font.family; x:20;y:17;text:"01 / SYSTEM ANATOMY";color:host.dim;font.pixelSize:11;font.letterSpacing:1.8 }
            SystemMap { x:12;y:39;width:parent.width-24;height:264;host:root.host }
            Text {font.family:Style.font.family; x:20;anchors.bottom:parent.bottom;anchors.bottomMargin:12;text:host.scanning?"DIAGNOSTICS IN PROGRESS":"LOCAL · READ ONLY";color:host.dim;font.pixelSize:10;font.letterSpacing:1 }
        }
        Rectangle {
            visible:root.section===0;width:parent.width;height:355;radius:13
            color:host.card;border.color:host.edge
            Column {
                x:23;y:21;width:parent.width-46;spacing:14
                Row {
                    spacing:9
                    Rectangle {width:7;height:7;radius:4;color:host.stateColor(host.overallState);anchors.verticalCenter:parent.verticalCenter}
                    Text {font.family:Style.font.family;text:host.scanning?"SCAN IN PROGRESS":host.complete?"SCAN COMPLETE":"EVIDENCE FIRST";color:host.dim;font.pixelSize:11;font.letterSpacing:1.6}
                }
                Text {width:parent.width;text:host.headline;color:host.ink;font.pixelSize:28;font.family:Style.font.family;wrapMode:Text.WordWrap;lineHeight:1.1}
                Text {font.family:Style.font.family;width:parent.width;text:host.summary;maximumLineCount:4;elide:Text.ElideRight;color:host.dim;font.pixelSize:13;wrapMode:Text.WordWrap;lineHeight:1.3}
                Row {
                    width:parent.width;spacing:10
                    Repeater {
                        model:[{n:host.counts.ok,label:"Checked healthy",state:"ok"},{n:host.actionableCount,label:"Needs fixing",state:"warn"},{n:host.presentation.unavailable,label:"Incomplete",state:"unknown"}]
                        Column {
                            required property var modelData
                            width:(parent.width-20)/3;spacing:6
                            Rectangle {width:parent.width;height:1;color:host.edge}
                            Text {font.family:Style.font.family;text:modelData.n;color:host.stateColor(modelData.state);font.pixelSize:29}
                            Text {font.family:Style.font.family;text:modelData.label;color:host.dim;font.pixelSize:11}
                        }
                    }
                }
                DoctorAction {objectName:"doctor-overview-review";text:host.indicator&&host.indicator.state==="unknown"?"Finish verification  →":"Browse check evidence  →";accent:host.good;ink:host.ink;onClicked:{if(host.indicator&&host.indicator.state==="ok"){host.filter="all";host.navigate("issues")}else host.routeConcern()}}
            }
        }
    }
    Row {
        visible:root.section===1;width:parent.width
        Text {font.family:Style.font.family;width:parent.width*0.5;text:"02 / VITAL SIGNS";color:host.dim;font.pixelSize:11;font.letterSpacing:1.8}
        Text {font.family:Style.font.family;width:parent.width*0.5;text:host.liveFresh?"Live · "+Model.elapsed(host.vitalsAt,host.now):"Waiting for live observations";horizontalAlignment:Text.AlignRight;color:host.dim;font.pixelSize:11}
    }
    Grid {
        visible:root.section===1;width:parent.width;columns:root.wide?4:2;spacing:12
        Repeater {
            model:Model.domains
            Rectangle {
                id:tile
                required property var modelData
                width:(parent.width-(parent.columns-1)*12)/parent.columns;height:202;radius:12
                color:tileMouse.containsMouse?Qt.alpha(host.ink,0.07):host.card
                border.color:tileMouse.containsMouse?host.domainTint(modelData.color):host.edge
                property real lift:tileMouse.containsMouse&&host.motion?-3:0
                transform:Translate {y:tile.lift}
                Behavior on lift {enabled:host.motion;NumberAnimation{duration:150;easing.type:Easing.OutCubic}}
                HardwareGlyph {x:parent.width-74;y:4;width:66;height:66;kind:tile.modelData.key;tint:host.domainTint(tile.modelData.color);surface:host.surface;level:Number(host.metrics[tile.modelData.key==="ram"?"ram_used_pct":tile.modelData.metric]||0);animate:host.motion&&host.opened&&root.visible}
                Column {
                    x:16;y:20;width:parent.width-32;spacing:7
                    Text {font.family:Style.font.family;text:tile.modelData.title.toUpperCase();color:host.dim;font.pixelSize:11;font.letterSpacing:1.3}
                    Item {width:1;height:8}
                    Row {
                        spacing:7
                        Text {font.family:Style.font.family;text:host.liveFresh?Model.reading(host.metrics,tile.modelData.metric):"—";color:host.ink;font.pixelSize:31}
                        Text {font.family:Style.font.family;text:tile.modelData.unit;color:host.dim;font.pixelSize:13;anchors.bottom:parent.bottom;anchors.bottomMargin:5}
                    }
                    Text {font.family:Style.font.family;text:tile.modelData.caption;color:host.dim;font.pixelSize:11}
                    HistoryGraph {width:parent.width;height:47;samples:host.samples;metric:tile.modelData.metric;unit:tile.modelData.unit;tint:host.domainTint(tile.modelData.color);ink:host.ink}
                    Text {font.family:Style.font.family;text:"Inspect evidence  →";color:host.domainTint(tile.modelData.color);font.pixelSize:11}
                }
                MouseArea {id:tileMouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:host.showFindings(tile.modelData.check)}
                Accessible.role:Accessible.Button
                Accessible.name:modelData.title+" diagnostics"
                Accessible.onPressAction:host.showFindings(modelData.check)
                activeFocusOnTab:true
                Keys.onReturnPressed:host.showFindings(modelData.check)
                Keys.onSpacePressed:host.showFindings(modelData.check)
                Rectangle {anchors.fill:parent;radius:parent.radius;color:"transparent";border.width:2;border.color:tile.activeFocus?host.good:"transparent"}
            }
        }
    }
    Grid {
        visible:root.section===0;width:parent.width;columns:root.wide?2:1;spacing:14
        Rectangle {
            width:(parent.width-(parent.columns-1)*14)/parent.columns;height:119;radius:12;color:host.card;border.color:host.edge
            Column {
                x:19;y:17;width:parent.width-38;spacing:10
                Text {font.family:Style.font.family;text:"03 / FIRST THING TO LOOK AT";color:host.dim;font.pixelSize:11;font.letterSpacing:1.5}
                Text {font.family:Style.font.family;width:parent.width;text:host.priority?host.priority.title:host.results.length?"No known actionable problems in checked scope":"Run a scan to establish a baseline";color:host.ink;font.pixelSize:14;elide:Text.ElideRight}
                Text {font.family:Style.font.family;width:parent.width;text:host.priority?host.priority.summary:"Doctor will show the evidence behind every result.";color:host.dim;font.pixelSize:12;wrapMode:Text.WordWrap;maximumLineCount:2;elide:Text.ElideRight}
            }
            MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:host.showFindings(host.priority?host.priority.id:"")}
        }
        Rectangle {
            width:(parent.width-(parent.columns-1)*14)/parent.columns;height:119;radius:12;color:host.card;border.color:host.edge;clip:true
            Column {
                x:19;y:17;width:parent.width-38;spacing:10
                Text {font.family:Style.font.family;text:"04 / SCAN ACTIVITY";color:host.dim;font.pixelSize:11;font.letterSpacing:1.5}
                Text {font.family:Style.font.family;width:parent.width;text:host.scanning?host.completed+" / "+host.total+" checks completed":host.lastScan?"Last scan · "+(host.duration/1000).toFixed(1)+" seconds":"Ready when you are";color:host.ink;font.pixelSize:14}
                Text {font.family:Style.font.family;width:parent.width;text:host.scanning?host.activity:host.changes.length?host.changes.length+" check state(s) changed since the previous scan.":"No system changes. Evidence stays on this machine.";color:host.dim;font.pixelSize:12;elide:Text.ElideRight}
            }
            Rectangle {anchors.bottom:parent.bottom;width:parent.width;height:3;color:host.edge}
            Rectangle {anchors.bottom:parent.bottom;width:parent.width*(host.scanning?host.completed/Math.max(1,host.total):host.complete?1:0);height:3;color:host.good;Behavior on width{enabled:host.motion;NumberAnimation{duration:180}}}
        }
    }
}
