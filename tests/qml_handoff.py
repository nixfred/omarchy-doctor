"""Exercise the actual native handoff button with a closed panel and harmless launcher."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
sys.path.insert(0,str(ROOT))
import doctor

if not os.environ.get('XDG_RUNTIME_DIR') or not os.environ.get('WAYLAND_DISPLAY'):
    raise SystemExit('A Wayland desktop environment is required: export its XDG_RUNTIME_DIR and WAYLAND_DISPLAY before native tests.')

with tempfile.TemporaryDirectory(prefix='doctor-handoff-qa-') as folder:
    work=Path(folder);database=work/'history.sqlite3';marker=work/'launched.txt'
    for name in ('Commons','Ui','services'):
        (work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
    for source in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:
        shutil.copy2(source,work/source.name)
    binpath=work/'bin';binpath.mkdir()
    chooser=binpath/'omarchy-default-agent'
    chooser.write_text("#!/bin/sh\nprintf '%s\\n' fixture\n");chooser.chmod(0o755)
    adapter=work/'safe_launcher.py'
    adapter.write_text("import sys\nfrom pathlib import Path\nPath(sys.argv[1]).write_text(sys.argv[2])\n")
    h=doctor.History(database)
    warning=doctor.result('packages','system','Package integrity','warn',
        'Native fixture package warning','Original native fixture evidence','fixture inspect')
    warning['timestamp']=time.time()-300
    h.save('deep','deep',[warning])
    old=h.open_fix(warning,'fixture');h.launch_state(old,'launch_failed',code=127)
    skipped=doctor.result('packages','system','Package integrity','skipped','Quick scan skipped integrity')
    h.save('quick','quick',[skipped])
    saved=h.read()['scans'];fixes=h.fixes();h.close()
    qml='''import QtQuick
import Quickshell
ShellRoot {
 Doctor{id:doctor;testMode:true;databasePath:DATABASE}
 property int step:0
 function assertThat(value,message){if(!value)throw new Error(message);console.log("PASS "+message)}
 function handoffButton(item){
  if(item.text!==undefined&&item.text==="Hand to agent again")return item
  for(var i=0;i<item.children.length;i++){var found=handoffButton(item.children[i]);if(found)return found}
  return null
 }
 Timer{interval:200;repeat:true;running:true;onTriggered:{
  step++
  if(step===1){doctor.applyFixture(ROWS,[]);doctor.scans=SCANS;doctor.fixes=FIXES;doctor.selectedId="packages";doctor.navigate("issues")}
  if(step===2){
   assertThat(doctor.selected.state==="warn"&&doctor.selected.coverage_note.indexOf("Not checked")>=0,"native selection retains the last measured warning")
   var button=handoffButton(doctor.issueTestItem())
   assertThat(button&&button.enabled,"actual Hand to agent again button exists and is enabled")
   doctor.testMode=false;button.clicked()
   assertThat(doctor.fixingId==="packages"&&doctor.showWork&&doctor.workProgress.key==="preparing","native button immediately opens prominent working state before backend responds")
  }
  if(step===15){
   assertThat(doctor.notice.indexOf("handed to fixture")>=0,"backend accepts retained warning and reports fixture handoff")
   assertThat(doctor.showWork&&doctor.workRecord.agent==="fixture"&&doctor.workId!=="","actual launcher acknowledges saved identity and agent in Working view");doctor.fixIssue("packages");assertThat(doctor.workId!=="","repeated handoff click keeps the saved attempt");assertThat(!doctor.opened,"native launch test never opens the panel")
   console.log("HANDOFF_UI_PASS");Qt.quit()
  }
 }}
}'''
    for key,value in [('DATABASE',str(database)),('ROWS',[skipped]),('SCANS',saved),('FIXES',fixes)]:
        qml=qml.replace(key,json.dumps(value))
    (work/'shell.qml').write_text(qml)
    import shlex
    env={**os.environ,'PATH':str(binpath)+':'+os.environ['PATH'],
        'QT_QPA_PLATFORM':'wayland','DOCTOR_AGENT_COMMAND':shlex.join([sys.executable,str(adapter),str(marker)])}
    p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env=env,capture_output=True,text=True,timeout=10)
    log=p.stdout+p.stderr
    assert p.returncode==0 and 'HANDOFF_UI_PASS' in log,log
    for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Binding loop'):assert bad not in log,log
    assert marker.exists(),'Native click never reached the launcher adapter'
    prompt=marker.read_text()
    assert warning['evidence'] in prompt and 'Coverage:  Not checked' in prompt,prompt
    c=sqlite3.connect(database);c.row_factory=sqlite3.Row
    deadline=time.monotonic()+7
    while time.monotonic()<deadline:
        rows=c.execute('SELECT * FROM fixes ORDER BY started DESC').fetchall()
        if rows and rows[0]['status']=='no_result':break
        time.sleep(.05)
    assert len(rows)==2 and rows[0]['id']!=old
    before=json.loads(rows[0]['before'])
    assert before['finding_number']==warning['finding_number']
    assert before['timestamp']==warning['timestamp']
    assert rows[0]['status']=='no_result',dict(rows[0])
    assert rows[1]['status']=='superseded'
    assert c.execute('SELECT COUNT(*) FROM receipts').fetchone()[0]==0
    c.close()
    print('PASS: actual native Hand to agent again handler -> retained-warning backend -> detached supervisor -> harmless launcher; original evidence/ID/time preserved; no real agent or repair, no false success, panel stayed closed.')
