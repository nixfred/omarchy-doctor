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
    property string version: "1.6.0"
    property string page: "overview"
    property var verificationJobs: []
    readonly property bool verifying: verifier.running || smartStarter.running
    property string verificationCheck: ""
    property bool packageConfirmation: false
    property bool smartConfirmation: false
    property var smartPlan: ({inventory:[],commands:[],error:""})
    readonly property bool smartPlanBusy: smartPlanner.running
    property var results: []
    property var metrics: ({})
    property var samples: []
    property var historySamples: []
    property var scans: []
    property var changes: []
    property var fixes: []
    property string fixingId: ""
    property string workId: ""
    property bool showWork: false
    property var workDraft: null
    property real workObservedAt: 0
    property string workHistoryError: ""
    property bool recoverWorkPending: false
    property bool concernRoutingPending: false
    readonly property var workRecord: fixes.find(function(f){return f.id===root.workId}) || workDraft
    readonly property var workProgress: Model.workState(workRecord,now)
    readonly property bool workRelevant: !!workRecord&&Model.workActive(workRecord,now)
    property var archived: null
    property string selectedId: ""
    property string filter: "needs_fix"
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
    property string configuredAgent: ""
    property string databasePath: ""
    readonly property real readingHeight: Math.max(220,outer.viewportHeight)
    property int preferredWidth: Math.min(1440,Math.max(1100,panel.availableCardWidth-80))
    readonly property bool motion: root.setting("motion",true) === true
    readonly property int refreshSeconds: Number(root.setting("refreshSeconds",300))
    readonly property bool liveFresh: root.opened && root.vitalsAt > 0 && root.now-root.vitalsAt<20
    readonly property bool stale: !scanning && lastScan>0 && now-lastScan>600
    readonly property var counts: Model.counts(results)
    readonly property var presentation: Model.presentation(shownRows,complete,stale,now)
    readonly property var indicator: Model.indicator(shownRows,complete,stale,scanning,now)
    readonly property string overallState: indicator.state
    readonly property var findingCounts: Model.counts(Model.findingRows(results))
    readonly property int issueCount: indicator.badge
    readonly property int newEventCount: Model.findingRows(results).reduce(function(n,r){return n+(r.new_count||0)},0)
    readonly property bool historicalOnly: results.some(function(r){return r.findings&&r.findings.length}) && !newEventCount && !results.some(function(r){return (r.state==="warn"||r.state==="bad")&&!r.findings})
    readonly property var ordered: Model.sorted(Model.findingRows(results))
    readonly property var priority: indicator.target || null
    readonly property var shownRows: Model.lastMeasuredRows(results,scans)
    readonly property var viewRows: archived ? archived.rows : shownRows
    readonly property var filtered: Model.sorted(Model.findingRows(viewRows)).filter(function(r){return Model.matches(r,root.filter,root.now)})
    readonly property var selected: {
        for(var i=0;i<filtered.length;i++) if(filtered[i].id===selectedId)return filtered[i]
        return filtered.length ? filtered[0] : null
    }
    readonly property string headline: Model.healthHeadline(indicator,scanning,results.length>0)
    readonly property string summary: scanning?"Doctor reads the system and retains its evidence.":scanError?scanError:Model.issueSummary(shownRows,complete,false,now)+" "+presentation.logNotes+" log note(s) and "+presentation.historical+" past record(s) remain available."
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
    readonly property var pages:[{key:"overview",label:"Overview"},{key:"verification",label:"Verification"},{key:"issues",label:"Issues"},{key:"settings",label:"Settings"},{key:"about",label:"About"}]
    readonly property string repoUrl: "https://github.com/nixfred/omarchy-doctor"
    readonly property string homeUrl: "https://nixfred.com"
    readonly property int actionableCount: presentation.needs
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
    function routeConcern() {
        concernRoutingPending=true
        showWork=false;archived=null;selectedId=""
        var current=Model.indicator(shownRows,complete,stale,scanning,Date.now()/1000)
        if(current.state==="ok"){navigate("overview");notice="";return}
        if(current.state==="unknown"&&(current.coverage>0||current.filter==="investigate"&&!current.review)){navigate("verification");notice="Finish the checks below to establish healthy coverage.";return}
        navigate("issues");filter=current.filter
        if(current.target){selectedId=current.target.id;notice=current.label+" · "+current.reason}
        else{notice=current.label+" · "+current.reason+" Use Run Doctor above."}
    }
    function showFindings(key) {archived=null;filter="all";selectedId=key;page="issues"}
    function navigate(key) {showWork=false;if(key==="settings")readAgent();page=["findings","history","fixes"].indexOf(key)>=0?"issues":key;outer.reset();if(page==="issues"||page==="verification")loadHistory();if(key==="history")filter="historical"}
    function refresh(deep) {
        if(collector.running||verifier.running||packageStarter.running||smartStarter.running||testMode)return
        results=[];complete=false;receivedEnd=false;protocolError=false;scanning=true;completed=0;scanError="";archived=null;changes=[]
        activity="Starting "+(deep?"deep":"quick")+" scan";collector.command=args("scan",deep?["--deep"]:[]);collector.running=true;deadline.restart()
    }
    function abortScan() {scanError="Scan cancelled. Results are partial.";complete=false;receivedEnd=false;collector.running=false;deadline.stop()}
    function openFix(check) {for(var i=0;i<fixes.length;i++)if(fixes[i].check===check&&fixes[i].status!=="superseded")return fixes[i];return null}
    function fixable(row) {return !!row&&!archived&&(row.state==="bad"||row.state==="warn"||row.state==="unknown")}
    function viewWork(record) {if(!record)return;workId=record.id||"";workDraft=record;showWork=true;outer.reset()}
    function leaveWork() {showWork=false;outer.reset()}
    function openWorkLog() {if(!testMode&&workRecord&&workRecord.log_path)Quickshell.execDetached(["xdg-open",workRecord.log_path])}
    function openWorkSession() {if(!testMode&&workRecord&&workRecord.launch_mode==="background"&&!workRecord.supervisor_alive&&workRecord.exit_code!==null&&workRecord.exit_code!==undefined&&workRecord.exit_code>=0&&/^[0-9a-fA-F-]{36}$/.test(workRecord.session_id||""))Quickshell.execDetached(["omarchy-launch-tui","--app-id=org.omarchy.agent","codex","--approve-for-me","-C",workRecord.work_directory,"resume",workRecord.session_id])}
    function inspectWork() {if(workRecord){archived=null;filter="all";selectedId=workRecord.check};navigate("issues")}
    function recoverWork() {
        var active=fixes.find(function(f){return Model.workActive(f,root.now)})
        if(active){viewWork(active)}
        else if(!workId&&fixes.length&&now-fixes[0].started<3600){workId=fixes[0].id;workDraft=fixes[0]}
        recoverWorkPending=false
    }
    function fixIssue(check) {
        if(!check||testMode)return
        var active=fixes.find(function(f){return f.check===check&&Model.workActive(f,root.now)})
        if(active){viewWork(active);return}
        if(fixer.running){showWork=true;return}
        var row=Model.findingRows(shownRows).find(function(r){return r.id===check})||({id:check,title:check})
        fixingId=check;workId="";workObservedAt=0;workHistoryError=""
        viewWork({check:check,title:row.title,finding_number:row.finding_number,phase:"preparing",started:Date.now()/1000,agent:"",before_summary:row.summary,before_evidence:row.evidence,before_command:row.command,before_timestamp:row.timestamp})
        notice="";fixer.command=args("fix",[check]);fixer.running=true
    }
    function verificationJob(check){return verificationJobs.find(function(j){return j.check===check})||null}
    function updateVerification(job){verificationJobs=verificationJobs.filter(function(j){return j.check!==job.check}).concat([job])}
    function verifyShell(restart){if(verifier.running||collector.running||rechecker.running||testMode)return;verificationCheck="shell";notice="Reading a fixed journal snapshot…";verifier.command=args(restart?"restart-shell-verification":"verify-shell");verifier.running=true}
    function verifyJournal(restart){if(verifier.running||collector.running||rechecker.running||testMode)return;verificationCheck="journal";notice="Reading a fixed boot journal snapshot…";verifier.command=args(restart?"restart-journal-verification":"verify-journal");verifier.running=true}
    function cancelVerification(){if(verifier.running){notice="Cancelling at the last committed page…";verifier.signal(15)}}
    function requestSmartVerification(){smartConfirmation=true;smartPlan={inventory:[],commands:[],error:""};if(testMode)return;smartPlanner.command=args("smart-plan");smartPlanner.running=true}
    function startSmartVerification(){if(scanning||verifying||testMode||smartPlanBusy||smartPlan.error||!smartPlan.commands.length)return;smartConfirmation=false;smartStarter.command=args("start-smart-verification",["--devices-json",JSON.stringify(smartPlan.inventory)]);smartStarter.running=true;notice="Opening the normal SMART verification terminal. Authenticate there; Ctrl+C cancels."}
    function requestPackageVerification(){packageConfirmation=true}
    function startPackageVerification(){packageConfirmation=false;if(packageStarter.running||testMode)return;packageStarter.command=args("start-package-verification");packageStarter.running=true;notice="Opening the normal verification terminal. Authenticate there; Ctrl+C cancels."}
    function verificationTestItem(){return testMode&&page==="verification"?pageLoader.item:null}
    function barTestItem(){return testMode?button:null}
    function suppressFixtureWindow(){if(testMode)panel.visible=false}
    function recheck(check) {if(!check||rechecker.running||collector.running||testMode)return;fixingId=check;notice="Rechecking "+check+"…";rechecker.command=args("recheck",[check]);rechecker.running=true}
    function assessFinding(check,disposition,reason) {if(!reason.trim()){notice="Add the diagnosis or evidence behind your assessment.";return}if(assessor.running||testMode)return;assessor.command=args("assess",[check,"--disposition",disposition,"--reason",reason]);assessor.running=true}
    function loadHistory() {if(testMode)return;if(historyProcess.running){historyPending=true;return}historyPending=false;historyProcess.command=args("history",["--seconds",String(historySeconds)]);historyProcess.running=true}
    function chooseAgent(){if(!testMode)Quickshell.execDetached(["omarchy-menu","summon","setup.default.agent"])}
    function readAgent(){if(!testMode&&!agentReader.running){agentReader.command=["omarchy-default-agent"];agentReader.running=true}}
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
            if(source==="recheck"){var row={};for(var k in e.result)row[k]=e.result[k];row.change="rechecked";results=Model.mergeRows(results,row);return}
            results=Model.mergeRows(results,e.result);completed=e.completed;activity=e.result.title+" · "+Model.labels[e.result.state]
        } else if(e.type==="scan_end") {
            (e.event_checks||[]).forEach(function(row){results=Model.mergeRows(results,row)})
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
            workObservedAt=Date.now()/1000;workHistoryError=""
            if(e.verification_jobs)verificationJobs=e.verification_jobs;
            scans=e.scans||[];if(!scanning&&results.length&&scans.length)scans[0].rows.forEach(function(row){var old=results.find(function(r){return r.id===row.id});if(!old||row.timestamp>=old.timestamp)results=Model.mergeRows(results,row)});if(e.fixes)fixes=e.fixes;if(e.host)hostname=e.host
            var stored=e.samples||[],cutoff=stored.length?stored[stored.length-1].timestamp:0
            historySamples=stored.concat(historySamples.filter(function(s){return s.timestamp>cutoff&&s.timestamp>=Date.now()/1000-root.historySeconds}))
            if(!vitalsAt)samples=historySamples.filter(function(s){return s.timestamp>Date.now()/1000-3600}).slice(-240)
            if(!scanning&&!results.length&&scans.length){results=scans[0].rows;lastScan=scans[0].coverage_timestamp||scans[0].timestamp;complete=scans[0].complete===true;if(!complete)scanError="Saved scan has incomplete coverage. Run Doctor again."}
            if(!workId&&!workDraft){var savedWork=fixes.find(function(f){return Model.workActive(f,root.now)})||(fixes.length&&now-fixes[0].started<3600?fixes[0]:null);if(savedWork){workId=savedWork.id;workDraft=savedWork}}
            if(recoverWorkPending)recoverWork()
            if(concernRoutingPending){routeConcern();concernRoutingPending=false}
        } else if(e.type==="fix_start") {
            workId=e.id
            var draft={};for(var k in workDraft)draft[k]=workDraft[k]
            draft.id=e.id;draft.check=e.check;draft.title=e.title;draft.agent=e.agent;draft.launch_mode=e.launch_mode||"interactive";draft.started=e.started||draft.started||e.timestamp;draft.phase=e.launched?"running":"launch_failed";draft.error=e.error;draft.supervisor_alive=e.launched;draft.observed_at=e.timestamp;workDraft=draft;workObservedAt=e.timestamp
            notice=e.launched?e.title+" handed to "+(e.agent||"your agent")+". A completion receipt returns its report; Doctor verifies separately.":(e.error||"The agent could not be started.")
            loadHistory()
        } else if(e.type==="recheck_end") {
            var fixed=(e.fixes||[]).filter(function(f){return f.status==="fixed"}).length
            notice=fixed?"Fixed. "+e.summary:e.state==="ok"?"Healthy on recheck. "+e.summary:"Still "+Model.labels[e.state].toLowerCase()+" on recheck. "+e.summary
            loadHistory()
        } else if(e.type==="smart_plan"){smartPlan=e.plan}
        else if(e.type==="verification_progress"){updateVerification(e.job)}
        else if(e.type==="verification_end"){updateVerification(e.job);notice=e.job.phase==="complete"?"Verification completed. Warning notes and history remain visible.":"Verification is unfinished. "+(e.job.error||"Continue from the saved cursor below.");loadHistory()}
        else if(e.type==="assessment"){notice="Assessment saved. It does not mark a repair verified.";loadHistory()}
        else if(e.type==="export")notice="Saved report: "+e.path
        else if(e.type==="error"){notice=e.message;if(source==="scan"){scanError=e.message;protocolError=true}}
    }
    function statusRow(row,budget) {
        budget=budget||{remaining:24}
        var out={id:String(row.id||"").slice(0,160),finding_number:row.finding_number,title:String(row.title||"").slice(0,140),state:row.state,summary:String(row.summary||"").slice(0,180),timestamp:row.timestamp,needs_fix:row.needs_fix,disposition:row.disposition,resolution:row.resolution,severity:row.severity,priority:row.priority,activity:row.activity,new_count:row.new_count,event_count:row.event_count,first_seen:row.first_seen,last_seen:row.last_seen}
        if(row.findings){var shown=row.findings.slice(0,Math.max(0,budget.remaining));budget.remaining-=shown.length;out.findingCount=row.findings.length;out.omittedFindingCount=row.findings.length-shown.length;out.findings=shown.map(function(f){return root.statusRow(f,budget)})}
        return out
    }
    function status() {var budget={remaining:24};var selected=filtered.slice(0,40);return JSON.stringify({version:version,headline:headline,opened:opened,page:page,scanning:scanning,complete:complete,state:overallState,indicator:{label:indicator.label,reason:String(indicator.reason||"").slice(0,1200),target:indicator.target?indicator.target.id:"",badge:indicator.badge,actionable:indicator.actionable,coverage:indicator.coverage,review:indicator.review},counts:counts,lastScan:lastScan,vitalsAt:vitalsAt,liveFresh:liveFresh,sampleCount:samples.length,scanCount:scans.length,results:results.map(function(r){return root.statusRow(r,budget)}),verificationJobs:verificationJobs.map(function(j){return {check:j.check,phase:j.phase,raw_entries:j.raw_entries,pages:j.pages,error:String(j.error||"").slice(0,200)}}),filteredFindingCount:filtered.length,omittedFilteredFindingIds:Math.max(0,filtered.length-selected.length),filteredFindingIds:selected.map(function(r){return r.finding_number||r.id}),filter:filter,needsFixCount:actionableCount,badgeCount:issueCount,historicalCount:presentation.historical,unavailableCount:presentation.unavailable,presentation:presentation,retainedWarnings:shownRows.filter(function(row){return !!row.coverage_note}).map(function(r){return root.statusRow(r,budget)}),metrics:metrics,working:{shown:showWork,id:workId,stage:workProgress.key,title:workProgress.title,observed_at:workObservedAt,error:workHistoryError},fixCount:fixes.length,omittedFixes:Math.max(0,fixes.length-40),fixes:fixes.slice(0,40).map(function(f){return {id:f.id,check:f.check,finding_number:f.finding_number,handoff_number:f.handoff_number,status:f.status,phase:f.phase,verified:f.verified,report_received:!!(f.report&&f.report.summary)}}),motion:motion,width:implicitWidth,height:implicitHeight,panelWidth:panel.contentWidth,panelHeight:panel.contentHeight,panelX:panel.cardOrigin.x,panelY:panel.cardOrigin.y,contentHeight:outer.contentHeight,layout:{kind:"pages",page:outer.page+1,pages:outer.pageCount,viewport:outer.viewportHeight,header:header.implicitHeight,body:body.height,footerY:footer.y},notice:String(notice||"").slice(0,600),scanError:String(scanError||"").slice(0,600),readback:"Bounded metadata (24 child findings, 40 filtered IDs/attempts maximum); omitted counts are explicit; full evidence and repair receipts remain in the panel and local history."})}
    function capture(path) {var started=body.grabToImage(function(image){var saved=image.saveToFile(path);if(root.testMode)console.log("DOCTOR_CAPTURE",saved,path)});if(root.testMode)console.log("DOCTOR_CAPTURE_START",started,body.width,body.height)}
    function moveFinding(delta){if(page==="issues"&&pageLoader.item)pageLoader.item.moveSelection(delta)}
    function issueTestItem(){return testMode&&!showWork&&page==="issues"?pageLoader.item:null}
    function workResumeTestItem(){return testMode?resumeWorkAction:null}
    function workTestItem(){return testMode&&showWork?pageLoader.item:null}
    function findingFilters(){return page==="issues"&&pageLoader.item?pageLoader.item.filters:[]}
    function findingGeometry(){return page==="issues"&&pageLoader.item?pageLoader.item.selectionGeometry():({})}
    function animationSnapshot(){var phases=[];function walk(item){if(item.objectName==="doctor-hardware")phases.push(item.phase);for(var i=0;i<item.children.length;i++)walk(item.children[i])}walk(body);return phases}
    function applyFixture(rows,observations) {if(!testMode)return;results=rows;samples=observations;historySamples=observations;metrics=observations.length?observations[observations.length-1].metrics:{};lastScan=Date.now()/1000;vitalsAt=lastScan;complete=true;hostname="Fixture host"}
    Component.onCompleted:{loadHistory();readAgent()}
    onOpenedChanged: {
        if(opened){now=Date.now()/1000;recoverWorkPending=false;loadHistory();if(!testMode){if(!watcher.running){watcher.command=args("watch");watcher.running=true}if(!lastScan||now-lastScan>600)refresh(false)}}
        else{watcher.running=false;watchRestart.stop()}
    }
    onPageChanged:outer.reset()
    Timer {interval:root.opened?1000:30000;repeat:true;running:true;onTriggered:root.now=Date.now()/1000}
    Timer {interval:Math.max(30,root.refreshSeconds)*1000;repeat:true;running:root.opened&&root.refreshSeconds>0&&!root.testMode;onTriggered:root.refresh(false)}
    Timer {interval:5000;repeat:true;running:root.opened&&!root.testMode&&!root.scanning;onTriggered:root.loadHistory()}
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
        onExited:function(code){if(code!==0){root.workHistoryError="Progress refresh failed. Last saved state may be stale. "+String(historyErrors.text).slice(0,160);root.notice=root.workHistoryError;}if(root.historyPending)Qt.callLater(root.loadHistory)}
    }
    Process {id:fixer;stdout:SplitParser{onRead:function(line){root.ingest(line,"fix")}} stderr:StdioCollector{id:fixErrors} onExited:function(code){
        root.fixingId=""
        if(!root.workId){var draft={};for(var k in root.workDraft)draft[k]=root.workDraft[k];draft.phase="launch_failed";draft.error=root.notice||String(fixErrors.text).slice(0,400)||"The handoff returned no saved attempt. Refresh progress before trying again.";root.workDraft=draft;root.loadHistory()}
    }}
    Process {id:rechecker;stdout:SplitParser{onRead:function(line){root.ingest(line,"recheck")}} stderr:StdioCollector{id:recheckErrors} onExited:function(code){root.fixingId="";if(code!==0&&!root.notice.length)root.notice="Recheck failed. "+String(recheckErrors.text).slice(0,160)}}
    Process {id:agentReader;stdout:StdioCollector{id:agentText} onExited:function(code){if(code===0)root.configuredAgent=String(agentText.text).trim()}}
    Process {id:assessor;stdout:SplitParser{onRead:function(line){root.ingest(line,"assess")}}}
    Process {id:exporter;stdout:SplitParser{onRead:function(line){root.ingest(line,"export")}} onExited:function(code){if(code!==0)root.notice="Report export failed."}}
    Process {id:copier;onExited:function(code){root.notice=code===0?"Diagnostic command copied. Nothing was executed.":"Clipboard copy failed; the command is visible in Evidence."}}
    Process{id:verifier;stdout:SplitParser{onRead:function(line){root.ingest(line,"recheck")}} stderr:StdioCollector{id:verificationErrors} onExited:function(code){root.verificationCheck="";if(code!==0)root.notice="Verification interrupted; full coverage is unproven. "+String(verificationErrors.text).slice(0,160);root.loadHistory()}}
    Process{id:smartPlanner;stdout:SplitParser{onRead:function(line){root.ingest(line,"verification")}} stderr:StdioCollector{id:smartPlanErrors} onExited:function(code){if(code!==0)root.smartPlan={inventory:[],commands:[],error:"Device discovery failed. "+String(smartPlanErrors.text).slice(0,300)}}}
    Process{id:smartStarter;stdout:SplitParser{onRead:function(line){root.ingest(line,"verification")}} onExited:root.loadHistory()}
    Process{id:packageStarter;stdout:SplitParser{onRead:function(line){root.ingest(line,"verification")}} onExited:root.loadHistory()}
    Timer{interval:2000;repeat:true;running:root.opened&&root.page==="verification"&&root.verificationJobs.some(function(j){return (j.phase==="awaiting_auth"||j.phase==="verifying")&&root.now-j.updated<180});onTriggered:root.loadHistory()}
    IpcHandler {
        target:"nixfred.doctor"
        enabled:!root.testMode
        function open():void{root.routeConcern();root.open()}
        function close():void{root.close()}
        function toggle():void{if(!root.opened)root.routeConcern();root.toggle()}
        function scan():void{root.refresh(false)}
        function deepScan():void{root.refresh(true)}
        function fix(check:string):void{root.fixIssue(check)}
        function recheck(check:string):void{root.recheck(check)}
        function show(page:string):void{if(["overview","verification","issues","findings","history","fixes","settings","about"].indexOf(page)>=0){root.navigate(page);root.open()}}
        function status():string{return root.status()}
    }
    BarIconButton {
        id:button;anchors.fill:parent;bar:root.bar;text:""
        active:root.issueCount>0
        tooltipText:"Omarchy Doctor · "+root.indicator.label+"\n"+root.indicator.reason+"\nClick to finish incomplete checks or inspect the current concern. No repair starts automatically."
        iconComponent:Component {MedicalCross{state:root.overallState;count:root.issueCount;busy:root.motion&&root.scanning}}
        onPressed:function(code){if(code===Qt.MiddleButton)root.refresh(false);else if(code===Qt.RightButton){root.navigate("settings");root.open()}else{if(!root.opened)root.routeConcern();root.toggle()}}
    }
    KeyboardPanel {
        id:panel;anchorItem:button;owner:root;bar:root.bar;open:root.opened;focusTarget:body
        contentWidth:panel.fittedContentWidth(root.preferredWidth)
        contentHeight:panel.fittedContentHeight(1000)
        Item {
            id:body;anchors.fill:parent;focus:true
            Keys.onEscapePressed:root.close()
            Keys.onPressed:function(event){
                if(event.key===Qt.Key_R){root.refresh(false);event.accepted=true}
                else if(event.key===Qt.Key_C&&root.page==="issues"&&root.selected){root.copyCommand(root.selected.command);event.accepted=true}
            }
            Rectangle {anchors.fill:parent;anchors.margins:-8;radius:12;color:root.surface}
            Column {id:header;width:parent.width;spacing:12
                    Row {
                        width:parent.width;spacing:14
                        HardwareGlyph{width:52;height:52;tint:root.good;surface:root.surface;animate:root.motion&&root.opened;kind:"core"}
                        Column {
                            width:parent.width-66-actionRow.width-14;spacing:5
                            Text{font.family:Style.font.family;text:"OMARCHY / DOCTOR";color:root.dim;font.pixelSize:11;font.letterSpacing:2}
                            Text{width:parent.width;text:"A healthier desktop, one check at a time.";color:root.ink;font.pixelSize:25;font.family:Style.font.family;elide:Text.ElideRight}
                            Text{font.family:Style.font.family;text:root.hostname+" · "+(root.scanning?"Scanning…":"Checked "+Model.elapsed(root.lastScan,root.now));color:root.dim;font.pixelSize:12}
                        }
                        Row {
                            id:actionRow;spacing:8;anchors.verticalCenter:parent.verticalCenter
                            DoctorAction{text:root.scanning?"Cancel":"Deep scan";ink:root.ink;accent:root.warning;onClicked:root.scanning?root.abortScan():root.refresh(true)}
                            DoctorAction{text:root.scanning?"Scanning…":"Run Doctor";enabled:!root.scanning;ink:root.ink;accent:root.good;primary:true;onClicked:root.refresh(false)}
                        }
                    }
                    Flow {
                        width:parent.width;spacing:10
                        Repeater {
                            model:root.pages
                            DoctorAction{required property var modelData;text:modelData.label+(modelData.key==="issues"&&root.actionableCount?"  "+root.actionableCount:"");ink:root.ink;accent:root.good;selected:root.page===modelData.key;onClicked:root.navigate(modelData.key)}
                        }
                    }
                    Flow {
                        width:parent.width;spacing:10;visible:root.workRelevant&&!root.showWork
                        DoctorAction{id:resumeWorkAction;objectName:"doctor-resume-work";text:(root.workRecord?(root.workRecord.finding_number||root.workRecord.check)+" · "+root.workRecord.title+" · ":"")+root.workProgress.title+" · View handoff";width:Math.min(implicitWidth,parent.width);fitCaption:true;ink:root.ink;accent:root.unknown;primary:true;onClicked:root.viewWork(root.workRecord)}
                    }
                    Text{width:parent.width;text:root.indicator.label+" · "+root.indicator.reason;maximumLineCount:2;elide:Text.ElideRight;color:root.overallState==="ok"?root.good:root.overallState==="warn"?root.warning:root.overallState==="bad"?root.danger:root.dim;font.family:Style.font.family;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                    Rectangle{width:parent.width;height:1;color:root.edge}
                    Rectangle {
                        width:parent.width;height:noticeText.implicitHeight+18;visible:root.notice!=="";color:Qt.alpha(root.unknown,0.07);radius:8
                        Text{font.family:Style.font.family;id:noticeText;x:10;y:9;width:parent.width-45;text:root.notice;color:root.ink;font.pixelSize:12;wrapMode:Text.WordWrap;textFormat:Text.PlainText}
                        Text{font.family:Style.font.family;anchors.right:parent.right;anchors.rightMargin:12;anchors.verticalCenter:parent.verticalCenter;text:"×";color:root.dim;font.pixelSize:18}
                        MouseArea{anchors.right:parent.right;width:35;height:parent.height;onClicked:root.notice=""}
                    }
            }
            ReadPages {
                id:outer;anchors.top:header.bottom;anchors.topMargin:14;anchors.bottom:footer.top;anchors.bottomMargin:8;width:parent.width;ink:root.ink;accent:root.good
                    Loader {
                        id:pageLoader;width:parent.width;height:item?item.implicitHeight:0
                        sourceComponent:root.showWork?workingComponent:root.page==="verification"?verificationComponent:root.page==="overview"?overviewComponent:root.page==="issues"?issuesComponent:root.page==="about"?aboutComponent:settingsComponent
                        onLoaded:if(item)item.width=Qt.binding(function(){return pageLoader.width})
                        opacity:1
                        NumberAnimation on opacity {id:entrance;from:0;to:1;duration:220;running:root.motion&&root.opened}
                        onSourceComponentChanged:{outer.reset();if(root.motion&&root.opened)entrance.restart()}
                    }
            }
            Text{id:footer;anchors.bottom:parent.bottom;width:parent.width;text:"DOCTOR "+root.version+" · LOCAL DIAGNOSTICS · "+root.counts.skipped+" SKIPPED · R scan";color:root.dim;font.family:Style.font.family;font.pixelSize:11;wrapMode:Text.WordWrap}
        }
    }
    Component{id:verificationComponent;VerificationPane{host:root}}
    Component{id:workingComponent;WorkingPane{host:root}}
    Component{id:overviewComponent;OverviewPane{host:root}}
    Component{id:issuesComponent;IssuesPane{host:root}}
    Component{id:aboutComponent;AboutPane{host:root}}
    Component{id:settingsComponent;SettingsPane{host:root}}
}
