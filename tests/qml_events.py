"""Load event finding pages in a hidden native process; never open a panel."""
import json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get("DOCTOR_RUNTIME_ROOT",str(Path(__file__).resolve().parents[1])))
OUT=Path(os.environ.get("DOCTOR_QML_LOG",str(Path(tempfile.gettempdir())/"omarchy-doctor-events.log")))
with tempfile.TemporaryDirectory(prefix='doctor-qml-events-') as folder:
 work=Path(folder)
 for name in ('Commons','Ui','services'):(work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
 for source in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(source,work/source.name)
 (work/'shell.qml').write_text('''import QtQuick
import Quickshell
ShellRoot {
 Doctor {id:doctor;testMode:true}
 property int step:0
 Timer {interval:180;running:true;repeat:true;onTriggered:{
  step++
  if(step===1){
   console.log("DEFAULT_FILTER "+doctor.filter)
   doctor.applyFixture([{id:"crashes",domain:"system",title:"Crashes",state:"warn",summary:"Historical",metrics:{},timestamp:Date.now()/1000,findings:[{id:"crashes:abc",check_id:"crashes",domain:"system",title:"Fixture application SIGSEGV",finding_number:"F-000042",needs_fix:true,disposition:"needs_fix",resolution:"unresolved",severity:"moderate",priority:2,state:"warn",summary:"Historical event",evidence:"Fixture",command:"coredumpctl info 42",metrics:{},timestamp:Date.now()/1000,first_seen:Date.now()/1000-100,last_seen:Date.now()/1000-90,event_count:2,new_count:0,activity:"historical",signature:"fixture"}]}],[])
   doctor.navigate("findings")
  }
  if(step===2){console.log("TOP_FILTERS "+doctor.findingFilters().map(function(f){return f.label}).join("|"));doctor.filter="recent";console.log("NEW_FILTER "+doctor.filtered.length)}
  if(step===3){doctor.filter="historical";console.log("HIST_FILTER "+doctor.filtered.length);console.log("SPECIFIC_ID "+doctor.selected.id);console.log("CLOSED "+doctor.opened)}
  if(step===4){doctor.filter="needs_fix";console.log("NEEDS_FILTER "+doctor.filtered.length);console.log("VISIBLE_NUMBER "+doctor.selected.finding_number);doctor.fixes=[{id:"test",finding_number:"F-000042",handoff_number:"H-000043",title:"Fixture",status:"reviewed_unproven",started:Date.now()/1000,agent:"any-agent",before_summary:"Before",after_summary:"After",before_evidence:"exact old evidence",before_timestamp:Date.now()/1000,before_command:"inspect old",after_evidence:"exact new evidence",after_command:"inspect new",verified_at:Date.now()/1000,verified:false,report:{summary:"Completed report",changes:"No changes",validation:"Fixture",rollback:"Nothing to undo"},verifications:[{timestamp:Date.now()/1000,outcome:"unproven",row:{summary:"Historical",command:"inspect",evidence:"Exact event"}}]}];doctor.navigate("fixes")}
  if(step===5){doctor.navigate("findings");doctor.filter="investigate";console.log("INVESTIGATE_FILTER "+doctor.filtered.length)}
  if(step===6){doctor.filter="attention";console.log("ATTENTION_FILTER "+doctor.filtered.length);doctor.navigate("about")}
  if(step===7)doctor.navigate("overview")
  if(step===8){console.log("HEADLINE "+doctor.headline.replace(/\\n/g," "));
   var event=doctor.results[0].findings[0]
   doctor.applyFixture([{id:"crashes",domain:"system",title:"Crashes",state:"warn",summary:"History",metrics:{},findings:[event]},
    {id:"active",finding_number:"F-000001",domain:"system",title:"Critical active fault",state:"bad",summary:"Active failure",metrics:{},priority:0,needs_fix:true,disposition:"needs_fix",resolution:"unresolved"},
    {id:"new-monitor",finding_number:"F-000003",domain:"system",title:"New assessed harmless symptom",state:"warn",summary:"Monitored",metrics:{},priority:5,needs_fix:false,disposition:"monitor",resolution:"unresolved",activity:"new",new_count:1},
    {id:"unavailable",finding_number:"F-000004",domain:"system",title:"No evidence",state:"unknown",summary:"Unknown",metrics:{},priority:3,needs_fix:false,disposition:"investigate",resolution:"unverified"}],[])
   doctor.navigate("findings");doctor.filter="needs_fix";console.log("COMBINED_NEEDS "+doctor.filtered.length);console.log("PRIORITY_FIRST "+doctor.filtered[0].id)
  }
  if(step===9){doctor.filter="recent";console.log("NEW_MONITOR "+doctor.filtered.length+" "+doctor.filtered[0].needs_fix)}
  if(step===10){doctor.filter="historical";console.log("HIST_ACTIONABLE "+doctor.filtered.length+" "+doctor.filtered[0].needs_fix)}
  if(step===11){doctor.filter="unknown";console.log("UNAVAILABLE_UNVERIFIED "+doctor.filtered[0].resolution)}
  if(step===12){doctor.filter="investigate";console.log("INVESTIGATE_UNAVAILABLE "+doctor.filtered.length);console.log("READBACK_VERSION "+JSON.parse(doctor.status()).version);console.log("READBACK_OPENED "+JSON.parse(doctor.status()).opened);Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=8)
 log=p.stdout+p.stderr;OUT.write_text(log)
 assert p.returncode==0,log
 for bad in ('ERROR:', 'ReferenceError','TypeError','Unable to assign','Flow will not function'):
  assert bad not in log,log
 for expected in ('DEFAULT_FILTER needs_fix','TOP_FILTERS Needs fixing|Investigate|History|All','NEW_FILTER 0','HIST_FILTER 1','SPECIFIC_ID crashes:abc','CLOSED false','NEEDS_FILTER 1','VISIBLE_NUMBER F-000042','INVESTIGATE_FILTER 0','ATTENTION_FILTER 1','COMBINED_NEEDS 2','PRIORITY_FIRST active','NEW_MONITOR 1 false','HIST_ACTIONABLE 1 true','UNAVAILABLE_UNVERIFIED unverified','INVESTIGATE_UNAVAILABLE 1','READBACK_VERSION 1.6.0','READBACK_OPENED false',"HEADLINE Let's look at 1 concern(s)."):
  assert expected in log,log
 print('PASS: hidden native pages load, specific signature selection, truthful filters/headline, no panel opened.')
