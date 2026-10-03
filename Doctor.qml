import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
    id: root
    moduleName: "nixfred.doctor"
    ipcTarget: "nixfred.doctor"
    manageIpc: false
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    property string version: "1.4.0"
    property string page: "overview"
    property var results: []
    property var metrics: ({})
    property var samples: []
    property var historySamples: []
    property var scans: []
    property var changes: []
    property var fixes: []
    property string fixingId: ""
    property var archived: null
    property string selectedId: ""
    property string filter: "all"
    property string historyMetric: "cpu_pct"
    property int historySeconds: 86400
    property bool historyPending: false
    property bool scanning: false
    property bool complete: false
    property bool receivedEnd: false
    property bool protocolError: false
    property int completed: 0
    property int total: 16
    property real lastScan: 0
    property real vitalsAt: 0
    property real now: Date.now()/1000
    property int duration: 0
    property string hostname: "This machine"
    property string activity: "Waiting for diagnostics"
    property string notice: ""
    property string scanError: ""
    property bool testMode: false
    property string databasePath: ""
    property int preferredWidth: Math.min(1440,Math.max(1100,panel.availableCardWidth-80))
    readonly property bool motion: root.setting("motion",true) === true
    readonly property int refreshSeconds: Number(root.setting("refreshSeconds",300))
    readonly property bool liveFresh: root.opened && root.vitalsAt > 0 && root.now-root.vitalsAt<20
    readonly property bool stale: !scanning && lastScan>0 && now-lastScan>600
    readonly property var counts: Model.counts(results)
    readonly property string overallState: stale ? "unknown" : Model.state(results,complete)
    readonly property var ordered: Model.sorted(results)
    readonly property var priority: ordered.length ? ordered[0] : null
    readonly property var viewRows: archived ? archived.rows : results
    readonly property var filtered: Model.sorted(viewRows).filter(function(r){return root.filter==="all" || (root.filter==="attention" && (r.state==="warn" || r.state==="bad")) || r.state===root.filter})
    readonly property var selected: {
        for(var i=0;i<filtered.length;i++) if(filtered[i].id===selectedId)return filtered[i]
        return filtered.length ? filtered[0] : null
    }
    readonly property string headline: scanning?"Reading the signals…":!lastScan&&!results.length?"Let's see how\nyou're doing.":!complete?"The scan is incomplete.":stale?"Time for a fresh look.":counts.bad?"Something needs\nyour attention.":counts.warn?"A few things\nto look at.":counts.unknown?"A clearer picture.\nA few blind spots.":"Looking good.\nChecks are healthy."
    readonly property string summary: scanning?"Checks appear as they finish. Missing evidence will never count as a healthy result.":scanError?scanError:stale?"These results are more than ten minutes old. Run Doctor for a current diagnosis.":!results.length?"A local, read-only checkup for your Omarchy machine. Inspect the evidence before deciding what to change.":counts.unknown?counts.unknown+" check(s) could not be completed. "+counts.skipped+" skipped or not applicable; inspect coverage in Findings.":counts.bad||counts.warn?"Findings are ranked by severity. Open a check to see what happened and how to inspect it.":"All completed checks are healthy. "+counts.skipped+" check(s) skipped or not applicable; this is a point-in-time result."
    readonly property color ink: Color.popups.text
    readonly property color dim: Qt.alpha(ink,0.65)
    readonly property color surface: Color.popups.background
    readonly property color card: Qt.alpha(ink,0.035)
    readonly property color edge: Qt.alpha(ink,0.14)
    readonly property bool lightTheme: surface.r*0.2126+surface.g*0.7152+surface.b*0.0722>0.55
    readonly property color good: lightTheme?"#367432":"#a9d98b"
    readonly property color warning: lightTheme?"#956007":"#e8b572"
    readonly property color danger: lightTheme?"#b63927":"#ed8a77"
    readonly property color unknown: lightTheme?"#1f7387":"#79c6d1"
    readonly property var pages:[{key:"overview",label:"Overview"},{key:"findings",label:"Findings"},{key:"history",label:"History"},{key:"fixes",label:"Fixes"},{key:"settings",label:"Settings"},{key:"about",label:"About"}]
    readonly property string repoUrl: "https://github.com/nixfred/omarchy-doctor"
    readonly property string homeUrl: "https://nixfred.com"
    readonly property int fixedCount: fixes.filter(function(f){return f.status==="fixed"}).length

    function stateColor(state) {return state==="bad"?danger:state==="warn"?warning:state==="ok"?good:state==="unknown"?unknown:dim}
    function domainTint(color) {return lightTheme?Qt.darker(color,2.1):color}
    function args(action,extra) {
        var path=decodeURIComponent(String(Qt.resolvedUrl("doctor.py")).replace(/^file:\/\//,""))
        var a=["python3","-u",path,action]
        if(databasePath)a=a.concat(["--database",databasePath])
        return a.concat(extra||[])
    }
    function saveSetting(key,value) {
        if(root.settings && root.settings[key]===value)return
        var next={};for(var k in root.settings)next[k]=root.settings[k];next[key]=value;root.settings=next
        if(root.bar&&root.bar.shell){if(root.bar.shell.updateEntryInline(root.moduleName,next)===false)notice="Changed for this session; settings could not be saved."}
    }
    // Detached so a cold browser start never blocks the panel.
    function openUrl(url) {Quickshell.execDetached(["xdg-open",url]);root.close()}
    function showFindings(key) {archived=null;filter="all";selectedId=key;page="findings"}
    function navigate(key) {page=key;outer.contentY=0;if(key==="history")loadHistory()}
    function refresh(deep) {
        if(collector.running||testMode)return
        results=[];complete=false;receivedEnd=false;protocolError=false;scanning=true;completed=0;scanError="";archived=null;changes=[]
        activity="Starting "+(deep?"deep":"quick")+" scan";collector.command=args("scan",deep?["--deep"]:[]);collector.running=true;deadline.restart()
    }
    function abortScan() {scanError="Scan cancelled. Results are partial.";complete=false;receivedEnd=false;collector.running=false;deadline.stop()}
    function openFix(check) {for(var i=0;i<fixes.length;i++)if(fixes[i].check===check&&(fixes[i].status==="pending"||fixes[i].status==="still_failing"))return fixes[i];return null}
    function fixable(row) {return !!row&&!archived&&(row.state==="bad"||row.state==="warn"||row.state==="unknown")}
    function fixIssue(check) {if(!check||fixer.running||testMode)return;fixingId=check;notice="Handing "+check+" to your agent…";fixer.command=args("fix",[check]);fixer.running=true}
    function recheck(check) {if(!check||rechecker.running||collector.running||testMode)return;fixingId=check;notice="Rechecking "+check+"…";rechecker.command=args("recheck",[check]);rechecker.running=true}
    function loadHistory() {if(testMode)return;if(historyProcess.running){historyPending=true;return}historyPending=false;historyProcess.command=args("history",["--seconds",String(historySeconds)]);historyProcess.running=true}
    function exportReport() {if(!exporter.running&&!testMode){exporter.command=args("export");exporter.running=true}}
    function copyCommand(text) {
        if(!text||copier.running)return
        copier.command=["bash","-c","printf %s \"$1\" | wl-copy","doctor-copy",text];copier.running=true
    }
    function ingest(line,source) {
        var e
        try{e=JSON.parse(line)}catch(err){if(source==="scan")protocolError=true;notice="Doctor received an invalid collector response.";return}
        if(e.schema!==1){notice="Unsupported Doctor data format.";if(source==="scan")protocolError=true;return}
        if(e.type==="scan_start") {total=e.total;hostname=e.host;activity="Checking "+hostname}
        else if(e.type==="check") {
            if(!Model.validRow(e.result)){protocolError=true;return}
            if(source==="recheck"){var row={};for(var k in e.result)row[k]=e.result[k];row.change="rechecked";results=Model.mergeRows(results,row);lastScan=e.result.timestamp;return}
            results=Model.mergeRows(results,e.result);completed=e.completed;activity=e.result.title+" · "+Model.labels[e.result.state]
        } else if(e.type==="scan_end") {
            receivedEnd=true;complete=e.complete===true&&!protocolError&&results.length===total
            lastScan=e.timestamp;duration=e.duration_ms;changes=e.changes||[]
            if(e.annotations)results=results.map(function(row){var copy={};for(var k in row)copy[k]=row[k];copy.change=e.annotations[row.id]||"";return copy})
            if(e.storage_error)notice="Results available, but history could not be saved: "+e.storage_error
            loadHistory()
        } else if(e.type==="vitals") {
            metrics=e.metrics||{};vitalsAt=e.timestamp
            var next=samples.slice();next.push({timestamp:e.timestamp,metrics:metrics});samples=next.slice(-240)
            var past=historySamples.filter(function(s){return s.timestamp>=e.timestamp-root.historySeconds});past.push({timestamp:e.timestamp,metrics:metrics})
            if(past.length>360)past=past.filter(function(s,i){return i%2===0||i===past.length-1})
            historySamples=past
            if(e.storage_error)notice="Live readings available; history storage failed: "+e.storage_error
        } else if(e.type==="history") {
            if(e.range_seconds!==undefined&&e.range_seconds!==historySeconds)return
            scans=e.scans||[];if(e.fixes)fixes=e.fixes;if(e.host)hostname=e.host
            var stored=e.samples||[],cutoff=stored.length?stored[stored.length-1].timestamp:0
            historySamples=stored.concat(historySamples.filter(function(s){return s.timestamp>cutoff&&s.timestamp>=Date.now()/1000-root.historySeconds}))
            if(!vitalsAt)samples=historySamples.filter(function(s){return s.timestamp>Date.now()/1000-3600}).slice(-240)
            if(!scanning&&!results.length&&scans.length){results=scans[0].rows;lastScan=scans[0].timestamp;complete=scans[0].complete===true;if(!complete)scanError="Saved scan has incomplete coverage. Run Doctor again."}
        } else if(e.type==="fix_start") {
            notice=e.launched?e.title+" handed to "+(e.agent||"your agent")+". It will recheck when done.":(e.error||"The agent could not be started.")
            loadHistory()
        } else if(e.type==="recheck_end") {
            var fixed=(e.fixes||[]).filter(function(f){return f.status==="fixed"}).length
            notice=fixed?"Fixed. "+e.summary:e.state==="ok"?"Healthy on recheck. "+e.summary:"Still "+Model.labels[e.state].toLowerCase()+" on recheck. "+e.summary
            loadHistory()
        } else if(e.type==="export")notice="Saved report: "+e.path
        else if(e.type==="error"){notice=e.message;if(source==="scan"){scanError=e.message;protocolError=true}}
    }
    function status() {return JSON.stringify({version:version,opened:opened,page:page,scanning:scanning,complete:complete,state:overallState,counts:counts,lastScan:lastScan,vitalsAt:vitalsAt,liveFresh:liveFresh,sampleCount:samples.length,scanCount:scans.length,results:results,metrics:metrics,fixes:fixes,motion:motion,width:implicitWidth,height:implicitHeight,panelWidth:panel.contentWidth,panelHeight:panel.contentHeight,panelX:panel.cardOrigin.x,panelY:panel.cardOrigin.y,contentHeight:content.implicitHeight,notice:notice,scanError:scanError})}
    function capture(path) {var started=body.grabToImage(function(image){var saved=image.saveToFile(path);if(root.testMode)console.log("DOCTOR_CAPTURE",saved,path)});if(root.testMode)console.log("DOCTOR_CAPTURE_START",started,body.width,body.height)}
    function moveFinding(delta){if(page==="findings"&&pageLoader.item)pageLoader.item.moveSelection(delta)}
    function findingGeometry(){return page==="findings"&&pageLoader.item?pageLoader.item.selectionGeometry():({})}
    function animationSnapshot(){var phases=[];function walk(item){if(item.objectName==="doctor-hardware")phases.push(item.phase);for(var i=0;i<item.children.length;i++)walk(item.children[i])}walk(body);return phases}
    function applyFixture(rows,observations) {if(!testMode)return;results=rows;samples=observations;historySamples=observations;metrics=observations.length?observations[observations.length-1].metrics:{};lastScan=Date.now()/1000;vitalsAt=lastScan;complete=true;hostname="Fixture host"}
    Component.onCompleted:loadHistory()
    onOpenedChanged: {
        if(opened){now=Date.now()/1000;loadHistory();if(!testMode){if(!watcher.running){watcher.command=args("watch");watcher.running=true}if(!lastScan||now-lastScan>600)refresh(false)}}
        else{watcher.running=false;watchRestart.stop()}
    }
    onPageChanged:outer.contentY=0
    Timer {interval:root.opened?1000:30000;repeat:true;running:true;onTriggered:root.now=Date.now()/1000}
    Timer {interval:Math.max(30,root.refreshSeconds)*1000;repeat:true;running:root.opened&&root.refreshSeconds>0&&!root.testMode;onTriggered:root.refresh(false)}
    Timer {id:deadline;interval:100000;onTriggered:{root.scanError="Scan exceeded its deadline. Results are partial.";root.complete=false;collector.running=false}}
    Timer {id:watchRestart;interval:10000;onTriggered:if(root.opened&&!root.testMode){watcher.command=root.args("watch");watcher.running=true}}
    Process {
        id:collector
        stdout:SplitParser {onRead:function(line){root.ingest(line,"scan")}}
        stderr:StdioCollector{id:scanStderr}
        onExited:function(code){deadline.stop();root.scanning=false;if(code!==0||!root.receivedEnd||root.protocolError){root.complete=false;if(!root.scanError)root.scanError=String(scanStderr.text||"Collector did not finish. Results are partial.").slice(0,400)} }
    }
    Process {
        id:watcher
        stdout:SplitParser{onRead:function(line){root.ingest(line,"watch")}}
        stderr:StdioCollector{}
        onExited:function(code){if(root.opened&&!root.testMode){root.notice="Live observations stopped; retrying in ten seconds.";watchRestart.restart()}}
    }
    Process {
        id:historyProcess
        stdout:SplitParser{onRead:function(line){root.ingest(line,"history")}}
        stderr:StdioCollector{id:historyErrors}
        onExited:function(code){if(code!==0)root.notice="History could not be loaded. "+String(historyErrors.text).slice(0,160);if(root.historyPending)Qt.callLater(root.loadHistory)}
    }
    Process {id:fixer;stdout:SplitParser{onRead:function(line){root.ingest(line,"fix")}} onExited:function(code){root.fixingId=""}}
    Process {id:rechecker;stdout:SplitParser{onRead:function(line){root.ingest(line,"recheck")}} stderr:StdioCollector{id:recheckErrors} onExited:function(code){root.fixingId="";if(code!==0&&!root.notice.length)root.notice="Recheck failed. "+String(recheckErrors.text).slice(0,160)}}
    Process {id:exporter;stdout:SplitParser{onRead:function(line){root.ingest(line,"export")}} onExited:function(code){if(code!==0)root.notice="Report export failed."}}
    Process {id:copier;onExited:function(code){root.notice=code===0?"Diagnostic command copied. Nothing was executed.":"Clipboard copy failed; the command is visible in Evidence."}}
    IpcHandler {
        target:"nixfred.doctor"
        enabled:!root.testMode
        function open():void{root.open()}
        function close():void{root.close()}
        function toggle():void{root.toggle()}
        function scan():void{root.refresh(false)}
        function deepScan():void{root.refresh(true)}
        function fix(check:string):void{root.fixIssue(check)}
        function recheck(check:string):void{root.recheck(check)}
        function show(page:string):void{if(["overview","findings","history","fixes","settings","about"].indexOf(page)>=0){root.navigate(page);root.open()}}
        function status():string{return root.status()}
    }
    BarIconButton {
        id:button;anchors.fill:parent;bar:root.bar;text:""
        active:root.counts.bad>0||root.counts.warn>0
        tooltipText:"Omarchy Doctor · "+(root.scanning?"Scanning":root.complete?(root.stale?"Results are stale":Model.labels[root.overallState]):"Not fully checked")+" · "+(root.counts.bad+root.counts.warn)+" findings"
        iconComponent:Component {MedicalCross{state:root.counts.bad?"bad":root.counts.warn?"warn":root.results.length&&root.complete&&root.counts.ok?"ok":"unknown";count:root.counts.bad+root.counts.warn;busy:root.motion&&root.scanning}}
        onPressed:function(code){if(code===Qt.MiddleButton)root.refresh(false);else if(code===Qt.RightButton){root.navigate("settings");root.open()}else root.toggle()}
    }
    KeyboardPanel {
        id:panel;anchorItem:button;owner:root;bar:root.bar;open:root.opened;focusTarget:body
        contentWidth:panel.fittedContentWidth(root.preferredWidth)
        contentHeight:panel.fittedContentHeight(content.implicitHeight)
        Item {
            id:body;anchors.fill:parent;focus:true
            Keys.onEscapePressed:root.close()
            Keys.onPressed:function(event){
                if(event.key===Qt.Key_R){root.refresh(false);event.accepted=true}
                else if(event.key===Qt.Key_C&&root.page==="findings"&&root.selected){root.copyCommand(root.selected.command);event.accepted=true}
            }
            Rectangle {anchors.fill:parent;anchors.margins:-8;radius:12;color:root.surface}
            Flickable {
                id:outer;anchors.fill:parent;contentWidth:width;contentHeight:content.implicitHeight;clip:true
                interactive:contentHeight>height;boundsBehavior:Flickable.StopAtBounds
                ScrollBar.vertical:ScrollBar{policy:outer.contentHeight>outer.height?ScrollBar.AlwaysOn:ScrollBar.AlwaysOff}
                Column {
                    id:content;width:outer.width;spacing:16
                    Row {
                        width:parent.width;spacing:14
                        HardwareGlyph{width:52;height:52;tint:root.good;surface:root.surface;animate:root.motion&&root.opened;kind:"core"}
                        Column {
                            width:parent.width-66-actionRow.width-14;spacing:5
                            Text{font.family:Style.font.family;text:"OMARCHY / DOCTOR";color:root.dim;font.pixelSize:11;font.letterSpacing:2}
                            Text{width:parent.width;text:"Your system, understood.";color:root.ink;font.pixelSize:25;font.family:Style.font.family;elide:Text.ElideRight}
                            Text{font.family:Style.font.family;text:root.hostname+" · "+(root.scanning?"Scanning…":"Checked "+Model.elapsed(root.lastScan,root.now));color:root.dim;font.pixelSize:12}
                        }
                        Row {
                            id:actionRow;spacing:8;anchors.verticalCenter:parent.verticalCenter
                            DoctorAction{text:root.scanning?"Cancel":"Deep scan";ink:root.ink;accent:root.warning;onClicked:root.scanning?root.abortScan():root.refresh(true)}
                            DoctorAction{text:root.scanning?"Scanning…":"Run Doctor";enabled:!root.scanning;ink:root.ink;accent:root.good;primary:true;onClicked:root.refresh(false)}
                        }
                    }
                    Row {
                        width:parent.width;spacing:10
                        Repeater {
                            model:root.pages
                            DoctorAction{required property var modelData;text:modelData.label+(modelData.key==="findings"?"  "+(root.counts.bad+root.counts.warn):modelData.key==="fixes"&&root.fixedCount?"  "+root.fixedCount:"");ink:root.ink;accent:root.good;selected:root.page===modelData.key;onClicked:root.navigate(modelData.key)}
                        }
                    }
                    Rectangle{width:parent.width;height:1;color:root.edge}
                    Rectangle {
                        width:parent.width;height:noticeText.implicitHeight+18;visible:root.notice!=="";color:Qt.alpha(root.unknown,0.07);radius:8
                        Text{font.family:Style.font.family;id:noticeText;x:10;y:9;width:parent.width-45;text:root.notice;color:root.ink;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;text:"×";color:root.dim;font.pixelSize:18}
                        MouseArea{anchors.right:parent.right;width:35;height:parent.height;onClicked:root.notice=""}
                    }
                    Loader {
                        id:pageLoader;width:parent.width;height:item?item.implicitHeight:0
                        sourceComponent:root.page==="overview"?overviewComponent:root.page==="findings"?findingsComponent:root.page==="history"?historyComponent:root.page==="fixes"?fixesComponent:root.page==="about"?aboutComponent:settingsComponent
                        onLoaded:if(item)item.width=Qt.binding(function(){return pageLoader.width})
                        opacity:1
                        NumberAnimation on opacity {id:entrance;from:0;to:1;duration:220;running:root.motion&&root.opened}
                        onSourceComponentChanged:if(root.motion&&root.opened)entrance.restart()
                    }
                    Row {
                        width:parent.width
                        Text{font.family:Style.font.family;width:parent.width*0.7;text:"DOCTOR "+root.version+" · LOCAL / READ ONLY · "+root.counts.skipped+" SKIPPED";color:root.dim;font.pixelSize:10;font.letterSpacing:1}
                        Text{font.family:Style.font.family;width:parent.width*0.3;text:"R scan  ·  C copy evidence command";horizontalAlignment:Text.AlignRight;color:root.dim;font.pixelSize:11}
                    }
                }
            }
        }
    }
    Component{id:overviewComponent;OverviewPane{host:root}}
    Component{id:findingsComponent;FindingsPane{host:root}}
    Component{id:historyComponent;HistoryPane{host:root}}
    Component{id:fixesComponent;FixesPane{host:root}}
    Component{id:aboutComponent;AboutPane{host:root}}
    Component{id:settingsComponent;SettingsPane{host:root}}
}
