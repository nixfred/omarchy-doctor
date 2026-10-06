"""Closed native gray-state regression using synthetic findings and actual UI handlers."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(os.environ.get('DOCTOR_RUNTIME_ROOT', str(Path(__file__).resolve().parents[1])))
with tempfile.TemporaryDirectory(prefix='doctor-gray-qa-') as folder:
    work = Path(folder)
    for name in ('Commons', 'Ui', 'services'):
        (work / name).symlink_to(Path(os.environ['OMARCHY_PATH']) / 'shell' / name, target_is_directory=True)
    for source in [*ROOT.glob('*.qml'), ROOT / 'Model.js', ROOT / 'doctor.py']:
        shutil.copy2(source, work / source.name)
    (work / 'shell.qml').write_text('''import QtQuick
import Quickshell
ShellRoot {
 Doctor { id: doctor; testMode: true; Component.onCompleted: doctor.suppressFixtureWindow() }
 property int step: 0
 function ok(value, message) { if (!value) throw new Error(message); console.log("PASS " + message) }
 function find(item, name) { if (item.objectName === name) return item; for (var i=0;i<item.children.length;i++) { var found=find(item.children[i],name); if(found)return found } return null }
 function row(id,state) { return {id:id,title:id,domain:"system",finding_number:"F-fixture-"+id,state:state,summary:"Synthetic "+state,timestamp:Date.now()/1000,metrics:{},needs_fix:state==="warn",resolution:state==="unknown"?"unverified":"verified_healthy"} }
 function apply(rows) { doctor.scans=[]; doctor.now=Date.now()/1000; doctor.applyFixture(rows,[]); doctor.routeConcern() }
 Timer { interval:200; repeat:true; running:true; onTriggered: {
  step++
  if(step===1) { apply([row("journal","unknown"),row("shell","unknown"),row("packages","skipped")]); ok(doctor.overallState==="unknown"&&doctor.headline==="2 checks still need verification.","gray headline names actual incomplete checks"); ok(doctor.indicator.reason.indexOf("Health is not verified yet.")===0,"gray reason leads with incomplete health") }
  if(step===2) { var pane=doctor.verificationTestItem(); ok(pane!==null,"gray routes to verification"); ok(find(pane,"doctor-journal-heading").text.indexOf("F-fixture-journal")===0,"boot heading uses measured finding identity"); ok(find(pane,"doctor-verify-packages")===null,"optional skipped packages do not solicit authentication"); var journal=row("journal","ok"); journal.coverage={complete:true}; apply([journal,row("shell","unknown"),row("packages","skipped")]); ok(doctor.headline==="1 check still needs verification.","one gap has singular headline") }
  if(step===3) { ok(doctor.verificationTestItem().done("journal"),"complete fresh boot journal uses log coverage predicate"); var journal=row("journal","ok"),shell=row("shell","ok"); journal.coverage={complete:true}; shell.coverage={complete:true}; apply([journal,shell,row("packages","skipped")]); ok(doctor.overallState==="ok"&&doctor.headline==="Checked scope is healthy.","fresh complete supported coverage permits healthy copy"); doctor.now=doctor.lastScan+700; doctor.routeConcern(); ok(doctor.overallState==="unknown"&&doctor.headline!=="Checked scope is healthy.","stale evidence cannot retain all-clear headline") }
  if(step===4) { apply([row("services","warn")]); ok(doctor.overallState==="warn"&&doctor.headline.indexOf("1 actionable concern")>=0,"actionable fault copy remains distinct"); apply([row("journal","unknown"),row("shell","unknown")]); doctor.showFindings(""); doctor.filter="needs_fix" }
  if(step===5) { var pane=doctor.issueTestItem(); var empty=find(pane,"doctor-empty-findings"); ok(empty&&empty.text.indexOf("Health is not verified: 2 checks need verification.")===0,"empty repairs view names coverage gaps"); var action=find(pane,"doctor-empty-verification"); ok(action&&action.visible,"empty repairs view offers Finish verification"); action.clicked(); ok(doctor.page==="verification","Finish verification routes through actual handler"); ok(!doctor.fixingId&&!doctor.workId&&!doctor.packageConfirmation,"fixture launches no repair, agent or authentication"); doctor.close(); console.log("GRAY_UI_PASS"); Qt.quit() }
 } }
}''')
    result = subprocess.run(['qs', '--no-color', '--path', str(work / 'shell.qml')],
                            env={**os.environ, 'QT_QPA_PLATFORM': 'wayland', 'QT_QPA_PLATFORMTHEME': '',
                                 'QT_QUICK_CONTROLS_STYLE': 'Basic'}, capture_output=True, text=True, timeout=9)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and 'GRAY_UI_PASS' in log, log
    for error in ('TypeError', 'ReferenceError', 'Unable to assign', 'Binding loop', 'Error:'):
        assert error not in log, log
    print(log)
