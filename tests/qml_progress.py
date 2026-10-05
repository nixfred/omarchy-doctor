"""Native closed-panel lifecycle fixtures; no real history, agent, probes or focus changes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
if not os.environ.get('XDG_RUNTIME_DIR') or not os.environ.get('WAYLAND_DISPLAY'):
    raise SystemExit('Native tests require the observed desktop Wayland environment.')
with tempfile.TemporaryDirectory(prefix='doctor-progress-qa-') as folder:
    work=Path(folder)
    for name in ('Commons','Ui','services'):(work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
    for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,work/p.name)
    (work/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 property int step:0
 property real started:Date.now()/1000-90
 function ok(value,message){if(!value)throw new Error(message);console.log("PASS "+message)}
 function find(item,name){if(item.objectName===name)return item;for(var i=0;i<item.children.length;i++){var x=find(item.children[i],name);if(x)return x}return null}
 function caption(item,text){if(item.text!==undefined&&String(item.text).indexOf(text)>=0)return true;for(var i=0;i<item.children.length;i++)if(caption(item.children[i],text))return true;return false}
 function record(){return {id:"fixture-handoff",check:"services",title:"Fixture services",finding_number:"F-fixture-57",handoff_number:"H-fixture",agent:"fixture-agent",started:started,last_update:started,observed_at:doctor.now,phase:"running",status:"pending",supervisor_alive:true,verified:false,report:{},verifications:[],before_summary:"Fixture warning",before_evidence:"Exact fixture evidence",before_command:"fixture inspect",before_timestamp:started-60}}
 function show(f){f=JSON.parse(JSON.stringify(f));doctor.fixes=[f];doctor.viewWork(f)}
 Timer{interval:180;repeat:true;running:true;onTriggered:{
  step++;doctor.now=Date.now()/1000
  if(step===1){show(record());ok(doctor.showWork&&doctor.workProgress.key==="running","prominent working view uses actual launcher observation")}
  if(step===2){ok(doctor.workTestItem()!==null,"real native Working pane loaded");var b=find(doctor.workTestItem(),"doctor-work-back");ok(b&&b.enabled,"working pane has an enabled back action");b.clicked();ok(!doctor.showWork&&doctor.workId==="fixture-handoff","back preserves attempt and returns to Doctor")}
  if(step===3){var b=doctor.workResumeTestItem();ok(b&&b.enabled,"ongoing attempt remains discoverable in Doctor");b.clicked();ok(doctor.showWork,"return to handoff never launches another agent")}
  if(step===4){var f=record();f.started=doctor.now-601;f.last_update=f.started;show(f);ok(doctor.workProgress.key==="waiting"&&doctor.workProgress.title.indexOf("unknown")>=0,"long wait is activity unknown, not invented progress")}
  if(step===5){var f=record();f.observed_at=doctor.now-21;show(f);ok(doctor.workProgress.key==="unknown","stale observation stops claiming launcher is currently running")}
  if(step===6){var f=record();f.phase="launch_failed";f.status="launch_failed";f.supervisor_alive=false;show(f);ok(doctor.workProgress.key==="launch_failed"&&!f.verified,"launcher failure is explicit and unproven")}
  if(step===7){ok(caption(doctor.workTestItem(),"2 · No agent report")&&caption(doctor.workTestItem(),"3 · No verification"),"launch failure stages never imply healthy verification");var f=record();f.phase="no_result";f.status="no_result";f.supervisor_alive=false;show(f);ok(doctor.workProgress.key==="no_result","missing receipt is explicit")}
  if(step===8){var f=record();f.phase="reported";f.report={outcome:"completed",summary:"Fixture claim",changes:"None",validation:"Fixture",rollback:"No changes"};f.report_received_at=doctor.now;f.status="reviewed_unproven";show(f);ok(doctor.workProgress.key==="verifying"&&!f.verified,"report received waits for independent evidence")}
  if(step===9){var f=doctor.workRecord;f.verifications=[{timestamp:doctor.now,outcome:"unproven",row:{state:"unknown",summary:"Unavailable",command:"fixture inspect",evidence:"Fixture denial"}}];show(f);ok(doctor.workProgress.key==="reviewed_unproven"&&!f.verified,"unavailable verification never becomes repair success")}
  if(step===10){var f=doctor.workRecord;f.status="fixed";f.verified=true;f.verifications=[{timestamp:doctor.now,outcome:"healthy",row:{state:"ok",summary:"Healthy fixture",command:"fixture inspect",evidence:"Actual fixture result"}}];show(f);ok(doctor.workProgress.key==="fixed","independent healthy evidence is explicit completion")}
  if(step===11){doctor.workId="";doctor.workDraft=null;doctor.showWork=false;doctor.fixes=[record()];doctor.recoverWork();ok(doctor.showWork&&doctor.workId==="fixture-handoff","reopening or a new instance recovers the saved active handoff")}
  if(step===12){var f=record();f.phase="interrupted";f.status="interrupted";f.supervisor_alive=false;show(f);ok(doctor.workProgress.key==="interrupted","interrupted launch is explicit");doctor.leaveWork();doctor.navigate("settings");ok(doctor.page==="settings"&&!doctor.showWork,"normal navigation never traps the user");ok(!doctor.opened,"fixtures never open the live panel");console.log("PROGRESS_UI_PASS");Qt.quit()}
 }}
}''')
    p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=8)
    log=p.stdout+p.stderr
    assert p.returncode==0 and 'PROGRESS_UI_PASS' in log,log
    for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Binding loop','Error:'):assert bad not in log,log
    print(log)
