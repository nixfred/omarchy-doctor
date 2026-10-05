"""Native novice UI invariants, with a closed panel and isolated fixture state."""
import os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
OUT=Path(os.environ.get("DOCTOR_QML_LOG",str(Path(tempfile.gettempdir())/"omarchy-doctor-novice.log")))
if not os.environ.get('XDG_RUNTIME_DIR') or not os.environ.get('WAYLAND_DISPLAY'):
    raise SystemExit('A Wayland desktop environment is required: export its XDG_RUNTIME_DIR and WAYLAND_DISPLAY before native tests.')

with tempfile.TemporaryDirectory(prefix='doctor-novice-qa-') as folder:
 work=Path(folder)
 for name in ('Commons','Ui','services'):(work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
 for source in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(source,work/source.name)
 (work/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 HardwareGlyph{id:motionProbe;animate:true;visible:true}
 property real phaseBefore:0
 property int step:0
 function assertThat(value,message){if(!value)throw new Error(message);console.log("PASS "+message)}
 function row(id,state){return {id:id,finding_number:id==="packages"?"F-000001":"F-"+id,domain:"system",title:id,state:state,summary:"Measured "+state,metrics:{},timestamp:Date.now()/1000,needs_fix:state==="warn"||state==="bad",disposition:state==="warn"||state==="bad"?"needs_fix":state==="unknown"?"investigate":"monitor",resolution:state==="ok"?"verified_healthy":state==="unknown"?"unverified":"unresolved",command:"fixture inspect",evidence:"Exact fixture output",rationale:"Fixture trigger",diagnosis:"Cause unknown"}}
 function healthy(){return ["services","journal","cpu","memory","temperature","storage","drives","gpu","battery","network","packages","audio","bluetooth","wifi","crashes","shell"].map(function(id){return row(id,"ok")})}
 function apply(rows){doctor.now=Date.now()/1000;doctor.applyFixture(rows,[])}
 Timer{interval:220;running:true;repeat:true;onTriggered:{
  step++
  if(step===1){apply(healthy());assertThat(doctor.pages.map(function(p){return p.label}).join("|")==="Overview|Verification|Issues|Settings|About","five novice pages including explicit Verification");assertThat(doctor.overallState==="ok"&&doctor.issueCount===0,"genuinely healthy green with zero badge");assertThat(doctor.refreshSeconds===300,"current five-minute choice unchanged");phaseBefore=motionProbe.phase}
  if(step===2){assertThat(motionProbe.phase>phaseBefore,"motion drawing really moves");motionProbe.animate=false;phaseBefore=motionProbe.phase;doctor.settings={motion:false,refreshSeconds:300};assertThat(!doctor.motion,"still drawings accessibility works");doctor.navigate("settings")}
  if(step===3){assertThat(motionProbe.phase===phaseBefore,"reduced motion stops drawing");doctor.saveSetting("refreshSeconds",900);assertThat(doctor.refreshSeconds===900,"frequency control works in isolated fixture");doctor.settings={motion:true,refreshSeconds:300};doctor.complete=false;assertThat(doctor.overallState==="unknown","partial cannot glow healthy")}
  if(step===4){apply(healthy());doctor.now=doctor.lastScan+700;assertThat(doctor.overallState==="unknown","stale cannot glow healthy")}
  if(step===5){var rows=healthy();rows[15]=row("shell","unknown");apply(rows);assertThat(doctor.overallState==="unknown"&&doctor.issueCount===0&&doctor.indicator.coverage===1,"unavailable is unknown with one badge concern")}
  if(step===6){var rows=healthy(),events=[];for(var i=0;i<45;i++){var f=row("crashes:"+i,"warn");f.needs_fix=false;f.disposition="investigate";f.activity="historical";f.new_count=0;f.event_count=1;events.push(f)}rows[14].state="warn";rows[14].findings=events;apply(rows);doctor.filter="needs_fix";doctor.navigate("issues");assertThat(doctor.filtered.length===0&&doctor.presentation.historical===45&&doctor.issueCount===0&&doctor.overallState==="ok","45 historical events do not change current healthy color or active count")}
  if(step===7){var rows=healthy(),past=healthy();past[10]=row("packages","warn");past[10].timestamp=Date.now()/1000-300;rows[10]=row("packages","skipped");rows[10].needs_fix=false;doctor.scans=[{timestamp:Date.now()/1000-300,rows:past}];apply(rows);doctor.filter="needs_fix";doctor.selectedId="packages";assertThat(doctor.filtered.length===1&&doctor.actionableCount===1&&doctor.issueCount===1&&doctor.overallState==="warn","skipped package warning stays actionable and badge consistent");assertThat(doctor.selected.finding_number==="F-000001"&&doctor.selected.coverage_note.indexOf("Not checked")>=0&&doctor.selected.timestamp===past[10].timestamp,"last-warning identity original time and coverage are truthful");doctor.fixes=[{id:"handoff",check:"packages",finding_number:"F-000001",handoff_number:"H-000002",title:"Package files",status:"still_failing",started:Date.now()/1000-200,agent:"example-agent",verified:false,before_summary:"Before warning",after_summary:"Still warning",before_timestamp:Date.now()/1000-200,verified_at:Date.now()/1000-100,before_command:"inspect before",after_command:"inspect after",before_evidence:"Old exact evidence",after_evidence:"New exact evidence",report:{summary:"Agent claim only",changes:"none",validation:"Inspected only",rollback:"no changes"},verifications:[{timestamp:Date.now()/1000-100,outcome:"failing",row:{state:"warn",summary:"Still warning",command:"inspect",evidence:"Exact output"}}]}]}
  if(step===8){var ui=doctor.issueTestItem();assertThat(ui&&!ui.evidenceOpen,"novice evidence starts collapsed");ui.evidenceOpen=true;ui.repairPane.showFirstWork();ui.historyOpen=true;doctor.historyMetric="cpu_pct";doctor.historySamples=[{timestamp:Date.now()/1000-300,metrics:{cpu_pct:23}},{timestamp:Date.now()/1000,metrics:{cpu_pct:77}}]}
  if(step===9){var ui=doctor.issueTestItem();assertThat(ui.evidenceOpen&&ui.repairPane.workIsOpen(),"evidence and repair proof expand");assertThat(ui.graphPane.graphPoints.length===2&&ui.graphPane.graphPoints[0].value===23&&ui.graphPane.graphPoints[1].value===77,"history graph uses exact supplied readings");doctor.historySamples=[]}
  if(step===10){assertThat(doctor.issueTestItem().graphPane.graphPoints.length===0,"empty coverage never fabricates graph samples");doctor.navigate("about")}
  if(step===11){doctor.scans=[];apply(healthy());doctor.navigate("overview");assertThat(doctor.overallState==="ok"&&doctor.headline.indexOf("No known actionable")>=0,"healthy encouragement returns after verified healthy data");assertThat(!doctor.opened,"native QA never opens panel");console.log("NOVICE_UI_PASS");Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=10)
 log=p.stdout+p.stderr;OUT.write_text(log)
 assert p.returncode==0,log
 for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Flow will not function','Binding loop','Error:'):assert bad not in log,log
 assert 'NOVICE_UI_PASS' in log,log
 print('PASS: novice navigation, badge/filter truth, skip/stale/partial/unknown handling, real graph samples, expandable proof, actual motion and settings controls; panel stayed closed.')
