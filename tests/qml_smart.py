"""Closed native SMART checklist: synthetic data, no terminals or authentication."""
import os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
with tempfile.TemporaryDirectory(prefix='doctor-smart-ui-') as folder:
 w=Path(folder)
 for n in ('Commons','Ui','services'):(w/n).symlink_to(SHELL/n,target_is_directory=True)
 for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,w/p.name)
 (w/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 property int step:0
 function ok(v,m){if(!v)throw new Error(m);console.log("PASS "+m)}
 function find(i,n){if(i.objectName===n)return i;for(var x=0;x<i.children.length;x++){var r=find(i.children[x],n);if(r)return r}return null}
 function row(state){return {id:"drives",title:"Physical drive health",domain:"disk",state:state,summary:"Fixture "+state,timestamp:Date.now()/1000,metrics:{smart_complete:state!=="unknown"},needs_fix:state==="bad",resolution:state==="unknown"?"unverified":state==="bad"?"unresolved":"verified_healthy"}}
 function apply(r){doctor.scans=[];doctor.applyFixture([r],[]);doctor.now=Date.now()/1000;doctor.routeConcern()}
 Timer{interval:200;repeat:true;running:true;onTriggered:{step++
 if(step===1){apply(row("unknown"));ok(doctor.overallState==="unknown"&&doctor.page==="verification","inaccessible drive routes gray to checklist");ok(Model.nextAction(row("unknown")).indexOf("Read SMART health")>=0,"evidence explains the concrete SMART path")}
 if(step===2){var pane=doctor.verificationTestItem();var b=find(pane,"doctor-verify-smart");ok(b&&b.enabled,"dedicated SMART action enabled");b.clicked();ok(doctor.smartConfirmation,"explicit preflight before authentication");var c=find(pane,"doctor-confirm-smart-verification");ok(c&&!c.enabled,"no device plan cannot start terminal");doctor.smartPlan={inventory:[{path:"/dev/nvme0n1"}],commands:["/usr/bin/sudo /usr/bin/smartctl -j -H /dev/nvme0n1"],error:""}}
 if(step===3){var p=doctor.verificationTestItem();ok(find(p,"doctor-smart-commands").text==="/usr/bin/sudo /usr/bin/smartctl -j -H /dev/nvme0n1","exact read-only command shown");var c=find(p,"doctor-confirm-smart-verification");ok(c.enabled,"confirmed valid device plan enables explicit terminal action");c.clicked();ok(!doctor.verifying,"test mode never starts authentication");find(p,"doctor-cancel-smart-verification").clicked();ok(!doctor.smartConfirmation,"cancel launches no terminal");doctor.verificationJobs=[{check:"drives",phase:"canceled",error:"User canceled",updated:Date.now()/1000}];apply(row("unknown"))}
 if(step===4){ok(doctor.overallState==="unknown","canceled remains gray");ok(find(doctor.verificationTestItem(),"doctor-smart-progress").text.indexOf("canceled")>=0,"canceled evidence visible");var r=row("ok");r.timestamp-=601;r.verification_expired=true;apply(r);ok(doctor.overallState==="unknown","expired SMART cannot claim green")}
 if(step===5){apply(row("bad"));ok(doctor.overallState==="bad"&&doctor.page==="issues","real SMART failure remains red actionable evidence");doctor.navigate("verification")}
 if(step===6){ok(find(doctor.verificationTestItem(),"doctor-smart-explanation").text.indexOf("does not repair")>=0,"health fault explanation does not promise authentication repair");apply(row("ok"));ok(doctor.overallState==="ok","fresh complete healthy receipt permits green");ok(!doctor.opened&&!doctor.fixingId&&!doctor.workId,"closed native fixture launches no live panel, agent or privileged command");console.log("SMART_UI_PASS");Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland','QT_QPA_PLATFORMTHEME':'','QT_QUICK_CONTROLS_STYLE':'Basic'},capture_output=True,text=True,timeout=9)
 log=p.stdout+p.stderr
 assert p.returncode==0 and 'SMART_UI_PASS' in log,log
 for bad in ('TypeError','ReferenceError','Unable to assign','Binding loop','Error:'):assert bad not in log,log
 print(log)
