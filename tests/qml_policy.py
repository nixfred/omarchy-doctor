"""Closed native alert/note/coverage policy, with fixture-only state."""
import os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
with tempfile.TemporaryDirectory(prefix='doctor-policy-') as folder:
 w=Path(folder)
 for n in ('Commons','Ui','services'):(w/n).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/n,target_is_directory=True)
 for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,w/p.name)
 (w/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 MedicalCross{id:icon;state:doctor.overallState;count:doctor.issueCount}
 property int step:0
 function ok(v,m){if(!v)throw new Error(m);console.log("PASS "+m)}
 function row(id,state){return {id:id,title:id,domain:"system",finding_number:"F-fixture-"+id,state:state,summary:"Fixture "+state,command:"fixture inspect",evidence:"Normalized fixture evidence",timestamp:Date.now()/1000,metrics:{},needs_fix:state==="warn"||state==="bad",resolution:state==="unknown"?"unverified":state==="ok"?"verified_healthy":"unresolved",disposition:state==="unknown"?"investigate":state==="ok"?"monitor":"needs_fix"}}
 function note(){var f=row("shell:audio","warn");f.check_id="shell";f.evidence_kind="log_warning";f.log_level="error";f.needs_fix=false;f.disposition="monitor";f.activity="recurring";f.new_count=20;f.last_seen=Date.now()/1000;f.title="pi.audio TypeError fixture";return f}
 function group(f,limited){var r=row("shell",limited?"unknown":"warn");r.needs_fix=false;r.findings=[f];r.limited=limited;r.coverage_incomplete=limited;return r}
 function apply(rows){doctor.now=Date.now()/1000;doctor.applyFixture(rows,[])}
 function caption(item,text){if(item.text!==undefined&&String(item.text).indexOf(text)>=0)return true;for(var i=0;i<item.children.length;i++)if(caption(item.children[i],text))return true;return false}
 Timer{interval:170;repeat:true;running:true;onTriggered:{
  step++
  if(step===1){apply([row("services","ok"),group(note(),true)]);doctor.routeConcern();ok(doctor.overallState==="unknown"&&doctor.issueCount===0&&doctor.indicator.coverage===1,"unknown coverage stays gray without a repair badge");ok(doctor.page==="verification"&&doctor.indicator.target.id==="shell","coverage routes to exact aggregate even with warning children");ok(Model.findingRows(doctor.shownRows).length===3,"warning and incomplete coverage both retained")}
  if(step===2){doctor.navigate("issues");doctor.filter="notes";doctor.selectedId="shell:audio";ok(doctor.filtered.length===1&&doctor.selected.evidence.indexOf("Normalized")>=0,"real warning evidence exposed in Log notes");ok(doctor.findingFilters().some(function(f){return f.key==="notes"}),"Log notes is visible navigation");ok(caption(doctor.issueTestItem(),"LOG WARNING · FUNCTIONAL IMPACT NOT ESTABLISHED"),"native details explicitly separate warning from repair")}
  if(step===3){apply([row("services","ok"),group(note(),false)]);ok(doctor.overallState==="ok"&&doctor.issueCount===0,"recurring log warnings alone do not become repair alarms");ok(doctor.indicator.reason.indexOf("checked scope")>=0&&doctor.headline.indexOf("No known actionable")>=0,"healthy wording is scoped rather than all checks verified");ok(Model.domainState(doctor.shownRows,"system",doctor.now)==="ok","anatomy does not falsely color log notes as faults")}
  if(step===4){var f=note();f.needs_fix=true;f.disposition="needs_fix";f.priority=2;apply([row("services","ok"),group(f,true)]);ok(doctor.overallState==="warn"&&doctor.issueCount===1&&doctor.indicator.coverage===1,"explicit supported diagnosis still produces actionable badge while preserving coverage")}
  if(step===5){var q=note();q.id="crashes:qa";q.check_id="crashes";q.evidence_kind="test_event";q.contexts=["test session"];var g=row("crashes","warn");g.findings=[q];g.needs_fix=false;apply([row("services","ok"),g]);ok(doctor.overallState==="ok"&&doctor.issueCount===0&&doctor.indicator.review===0,"explicit QA event stays quiet and accessible")}
  if(step===6){var event=row("crashes:desktop","warn");event.needs_fix=false;event.disposition="investigate";event.evidence_kind="crash_event";event.activity="new";event.new_count=1;event.last_seen=doctor.now;var g=row("crashes","warn");g.findings=[event];apply([row("services","ok"),g]);ok(doctor.overallState==="unknown"&&doctor.issueCount===0&&doctor.indicator.review===1,"unproven current crash needs review without claiming an ongoing fault")}
  if(step===7){var recovered=row("temperature","ok");recovered.recovery={kind:"without_handoff",timestamp:doctor.now};apply([row("services","ok"),recovered]);ok(doctor.overallState==="ok"&&doctor.issueCount===0&&Model.matches(recovered,"historical",doctor.now),"measured recovery remains in quiet history without an active warning")}
  if(step===8){apply([row("services","bad"),row("packages","unknown")]);doctor.routeConcern();ok(doctor.overallState==="bad"&&doctor.issueCount===1&&doctor.indicator.coverage===1,"real current fault remains prominent and coverage separate")}
  if(step===9){var g=group(note(),true);g.findings=[];for(var n=0;n<600;n++){var f=note();f.id="shell:fixture-"+n;f.finding_number="F-fixture-"+n;g.findings.push(f)}apply([row("services","ok"),g]);var payload=doctor.status(),saved=JSON.parse(payload);ok(payload.length<32768&&saved.results[1].findings.length===24&&saved.results[1].omittedFindingCount===576,"large actual journal metadata stays within IPC with explicit omission counts");ok(doctor.shownRows[1].findings.length===600,"metadata bounds never discard full panel/history findings")}
  if(step===10){apply([row("services","ok"),group(note(),true)]);doctor.workDraft={id:"failed",check:"shell",phase:"launch_failed",status:"launch_failed",started:doctor.now-100,agent:"fixture",verified:false,report:{}};doctor.workId="failed";ok(!doctor.workRelevant,"past agent launch failure does not become a machine-health alert");ok(!doctor.fixingId&&!doctor.opened,"policy fixtures launch no agent and keep live panel closed");console.log("POLICY_UI_PASS");Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=8);log=p.stdout+p.stderr
 assert p.returncode==0 and 'POLICY_UI_PASS' in log,log
 for bad in ('ERROR:','TypeError:','ReferenceError:','Unable to assign','Binding loop','Error:'):assert bad not in log,log
 print(log)
