"""Actual native bar/button handlers; fixture popup forcibly unmapped, no live focus or commands."""
import os,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
with tempfile.TemporaryDirectory(prefix='doctor-verification-ui-') as folder:
 w=Path(folder)
 for n in ('Commons','Ui','services'):(w/n).symlink_to(SHELL/n,target_is_directory=True)
 for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,w/p.name)
 (w/'shell.qml').write_text('''import QtQuick
import Quickshell
ShellRoot {
 Doctor{id:doctor;testMode:true;Component.onCompleted:doctor.suppressFixtureWindow()}
 property int step:0
 function ok(v,m){if(!v)throw new Error(m);console.log("PASS "+m)}
 function find(i,n){if(i.objectName===n)return i;for(var x=0;x<i.children.length;x++){var r=find(i.children[x],n);if(r)return r}return null}
 function row(id,state){return {id:id,title:id,domain:"system",state:state,summary:"Fixture "+state,timestamp:Date.now()/1000,metrics:{},needs_fix:false,resolution:state==="unknown"?"unverified":"verified_healthy"}}
 Timer{interval:200;repeat:true;running:true;onTriggered:{
 step++
 if(step===1){doctor.applyFixture([row("services","ok"),row("shell","unknown"),row("packages","unknown")],[]);var button=doctor.barTestItem();ok(button!==null,"actual bar button available");button.triggerPress(Qt.LeftButton);ok(doctor.opened&&doctor.page==="verification","actual gray icon press opens Finish verification checklist rather than generic Investigate")}
 if(step===2){var pane=doctor.verificationTestItem();ok(pane!==null&&pane.objectName==="doctor-verification-pane","actual checklist pane loaded");ok(find(pane,"doctor-verify-journal")!==null,"newly discovered boot-journal gap has a complete-read action");var b=find(pane,"doctor-verify-packages");ok(b&&b.enabled,"protected-file action available");b.clicked();ok(doctor.packageConfirmation,"package click requires explicit terminal confirmation before launch")}
 if(step===3){var b=find(doctor.verificationTestItem(),"doctor-cancel-package-verification");ok(b&&b.visible,"cancel confirmation is visible");b.clicked();ok(!doctor.packageConfirmation&&!doctor.fixingId&&!doctor.workId,"cancel launches no authentication, repair or agent")}
 if(step===4){doctor.verificationJobs=[{check:"shell",phase:"collecting",raw_entries:200,pages:2,until:Date.now()/1000,updated:Date.now()/1000}];var b=find(doctor.verificationTestItem(),"doctor-verify-shell");ok(b&&b.text==="Continue collection","unfinished bounded work resumes its cursor instead of same latest 500");doctor.verificationJobs=[{check:"shell",phase:"blocked",requires_restart:true,error:"Saved cursor unavailable",raw_entries:200,pages:2,updated:Date.now()/1000}];ok(b.text==="Restart collection","lost cursor offers a fresh complete snapshot without implying success")}
 if(step===5){var shell=row("shell","ok");shell.coverage={complete:true};var packages=row("packages","ok");packages.metrics={integrity_complete:true};doctor.applyFixture([row("services","ok"),shell,packages],[]);ok(doctor.overallState==="ok"&&doctor.issueCount===0,"genuinely completed fresh fixture coverage permits green");doctor.close();doctor.barTestItem().triggerPress(Qt.LeftButton);ok(doctor.page==="overview","actual green press opens healthy overview");doctor.close();ok(!doctor.fixingId&&!doctor.workId,"fixture never launches agent or privileged command");console.log("VERIFICATION_UI_PASS");Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland','QT_QPA_PLATFORMTHEME':'','QT_QUICK_CONTROLS_STYLE':'Basic'},capture_output=True,text=True,timeout=9)
 log=p.stdout+p.stderr
 assert p.returncode==0 and 'VERIFICATION_UI_PASS' in log,log
 for bad in ('TypeError','ReferenceError','Unable to assign','Binding loop','Error:'):assert bad not in log,log
 print(log)
