"""Native package coverage semantics; isolated fixture, closed panel, no probes."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
if not os.environ.get('XDG_RUNTIME_DIR') or not os.environ.get('WAYLAND_DISPLAY'):
    raise SystemExit('A Wayland desktop environment is required: export its XDG_RUNTIME_DIR and WAYLAND_DISPLAY before native tests.')

with tempfile.TemporaryDirectory(prefix='doctor-package-ui-') as folder:
    work=Path(folder)
    for name in ('Commons','Ui','services'):
        (work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
    for source in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:
        shutil.copy2(source,work/source.name)
    (work/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 property int step:0
 property real measured:Date.now()/1000-30
 function assertThat(value,message){if(!value)throw new Error(message);console.log("PASS "+message)}
 function row(id,state){return {id:id,finding_number:"F-fixture-"+id,domain:"system",title:id,state:state,summary:"Fixture "+state,metrics:{},timestamp:measured,needs_fix:state==="warn",disposition:state==="warn"?"needs_fix":state==="unknown"?"investigate":"monitor",resolution:state==="ok"?"verified_healthy":state==="unknown"?"unverified":"unresolved",command:"fixture inspect",evidence:"Fixture output",diagnosis:"Fixture diagnosis",coverage_note:state==="unknown"?"Package integrity was not fully verified.":""}}
 function rows(state){return ["services","journal","cpu","memory","temperature","storage","drives","gpu","battery","network","packages","audio","bluetooth","wifi","crashes","shell"].map(function(id){return row(id,id==="packages"?state:"ok")})}
 Timer{interval:200;running:true;repeat:true;onTriggered:{
  step++
  if(step===1){doctor.applyFixture(rows("unknown"),[]);doctor.scans=[{timestamp:measured,rows:rows("unknown")},{timestamp:measured-300,rows:rows("warn")}];doctor.filter="needs_fix";assertThat(doctor.filtered.length===0&&doctor.actionableCount===0,"denied coverage leaves Needs fixing");assertThat(doctor.issueCount===0&&doctor.indicator.coverage===1&&doctor.overallState==="unknown","denied coverage stays unknown and counted")}
  if(step===2){doctor.filter="investigate";doctor.selectedId="packages";doctor.fixes=[{id:"fixture",check:"packages",finding_number:"F-fixture-packages",handoff_number:"H-fixture",title:"Package integrity",status:"reviewed_unproven",started:measured-300,agent:"fixture",verified:false,before_summary:"Old false warning",before_timestamp:measured-300,before_command:"fixture inspect",before_evidence:"Original warning",after_summary:"Current coverage incomplete",verified_at:measured,after_command:"fixture inspect",after_evidence:"Permission denied",report:{summary:"Prior privileged claim",changes:"None",validation:"Historical claim",rollback:"No changes"},verifications:[{timestamp:measured,outcome:"unproven",row:{summary:"Incomplete coverage",command:"fixture inspect",evidence:"Permission denied"}}]}];doctor.navigate("issues");assertThat(doctor.filtered.length===1&&doctor.selected.state==="unknown","current uncertainty appears in Investigate");assertThat(Model.fixLabel(doctor.fixes[0].status).indexOf("unproven")>=0&&!doctor.fixes[0].verified,"agent claim never displays verified repair")}
  if(step===3){doctor.applyFixture(rows("skipped"),[]);assertThat(doctor.selected.state==="unknown"&&doctor.selected.timestamp===measured,"quick skip retains latest unavailable measurement and time");assertThat(doctor.selected.coverage_note.indexOf("Not checked")>=0&&doctor.selected.coverage_note.indexOf("not fully verified")>=0,"skipped coverage and diagnostic explanation both stay visible");assertThat(doctor.actionableCount===0&&doctor.issueCount===0&&doctor.indicator.coverage===1&&doctor.overallState==="unknown","quick scan cannot revive warning or fabricate healthy coverage")}
  if(step===4){doctor.scans=[];doctor.applyFixture(rows("ok"),[]);assertThat(doctor.overallState==="ok","fresh measured complete coverage can be healthy")}
  if(step===5){doctor.lastScan=Date.now()/1000-601;assertThat(doctor.overallState==="unknown","stale healthy measurement is not current healthy proof")}
  if(step===6){doctor.applyFixture(rows("warn"),[]);doctor.filter="needs_fix";assertThat(doctor.filtered.length===1&&doctor.actionableCount===1&&doctor.overallState==="warn","confirmed missing files remain actionable");assertThat(!doctor.opened,"native coverage QA never opens panel");console.log("PACKAGE_UI_PASS");Qt.quit()}
 }}
}''')
    p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=8)
    log=p.stdout+p.stderr
    assert p.returncode==0 and 'PACKAGE_UI_PASS' in log,log
    for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Binding loop'):assert bad not in log,log
    print('PASS: native permission-only unknown/Investigate, quick-skip uncertainty retention, durable unproven report, fresh/stale health distinction, and genuine missing-file actionability; panel stayed closed.')
