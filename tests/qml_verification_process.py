"""Actual native verification buttons -> real Doctor CLI -> temporary history/fake tools."""
import os,json,sqlite3,subprocess,tempfile,shutil,sys,time
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])));sys.path.insert(0,str(ROOT));import doctor
with tempfile.TemporaryDirectory(prefix='doctor-verify-process-') as folder:
 w=Path(folder);b=w/'bin';b.mkdir();db=w/'history.sqlite3';marker=w/'terminal.json';slow=w/'slow-once';slow.touch()
 for n in ('Commons','Ui','services'):(w/n).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/n,target_is_directory=True)
 for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,w/p.name)
 journal=b/'journalctl';journal.write_text('''#!/usr/bin/python3
import sys,json,time
from pathlib import Path
args=sys.argv[1:];boot=next(a.split('=',1)[1] for a in args if a.startswith('--boot='));end=float(next(a.split('@')[1] for a in args if a.startswith('--until=')));cursor=next((a.split('=',1)[1] for a in args if a.startswith('--cursor=')),None);size=int(next(a.split('+')[1] for a in args if a.startswith('--lines=')));start=int(cursor[1:]) if cursor else 0
flag=Path(SLOW)
if cursor and flag.exists():flag.unlink();time.sleep(2)
for n in range(start,min(145,start+size)):print(json.dumps(dict(__CURSOR='c'+str(n),__REALTIME_TIMESTAMP=str(int((end-20+n/1000)*1e6)),_BOOT_ID=boot,_COMM='quickshell',PRIORITY='3' if '--priority=3' in args else '6',MESSAGE='WARN fixture: TypeError exact retained evidence')))
'''.replace('SLOW',repr(str(slow))));journal.chmod(0o755)
 terminal=b/'omarchy-launch-tui';terminal.write_text("#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\nPath("+repr(str(marker))+").write_text(json.dumps(sys.argv[1:]))\n");terminal.chmod(0o755)
 h=doctor.History(db);rows=[doctor.result(k,'system',title,'unknown' if k in ('shell','packages') else 'ok','Fixture evidence',metrics={}) for k,title in doctor.CHECKS];h.save('fixture','quick',rows);h.close()
 qml='''import QtQuick
import Quickshell
ShellRoot{
 Doctor{id:doctor;testMode:true;databasePath:DATABASE;settings:({refreshSeconds:0});Component.onCompleted:doctor.suppressFixtureWindow()}
 property int step:0
 property var checklist:null
 function ok(v,m){if(!v)throw new Error(m);console.log("PASS "+m)}
 function find(i,n){if(i.objectName===n)return i;for(var x=0;x<i.children.length;x++){var r=find(i.children[x],n);if(r)return r}return null}
 Timer{interval:200;repeat:true;running:true;onTriggered:{step++
 if(step===1){doctor.applyFixture(ROWS,[]);doctor.barTestItem().triggerPress(Qt.LeftButton);ok(doctor.page==="verification","actual icon reaches checklist before measurement")}
 if(step===2){checklist=doctor.verificationTestItem();var b=find(checklist,"doctor-verify-shell");doctor.testMode=false;b.clicked();ok(doctor.notice.indexOf("snapshot")>=0,"actual shell button requests only verification CLI")}
 if(step===3){ok(doctor.verifying,"second page is intentionally waiting");doctor.cancelVerification()}
 if(step===7){var j=doctor.verificationJob("shell");ok(j&&j.phase==="paused"&&j.raw_entries===100,"cancel retains one committed page without false completion");doctor.verifyShell(false)}
 if(step===13){var j=doctor.verificationJob("shell");ok(j&&j.phase==="complete"&&j.raw_entries===145,"resume reaches real CLI EOF without replaying first page");var r=doctor.results.find(function(r){return r.id==="shell"});ok(r&&r.coverage.complete&&r.findings[0].evidence.indexOf("exact retained evidence")>=0,"actual CLI preserves warning evidence and clears only completed coverage");doctor.requestPackageVerification();ok(doctor.packageConfirmation,"explicit confirmation still gates terminal")}
 if(step===14){doctor.startPackageVerification()}
 if(step===18){var j=doctor.verificationJob("packages");ok(j&&j.phase==="awaiting_auth","actual start CLI requests visible authentication terminal and never claims healthy");find(checklist,"doctor-verify-journal").clicked()}
 if(step===24){var j=doctor.verificationJob("journal");ok(j&&j.phase==="complete"&&j.command.indexOf("--priority=3")>=0,"actual boot-log button/backend completes the existing priority 0–3 scope");var r=doctor.results.find(function(r){return r.id==="journal"});ok(r&&r.coverage.complete,"boot-log coverage is complete only after actual CLI EOF");doctor.testMode=true;doctor.close();ok(!doctor.fixingId&&!doctor.workId,"no repair handoff or agent exists");console.log("VERIFICATION_PROCESS_PASS");Qt.quit()}
 }}
}'''.replace('DATABASE',json.dumps(str(db))).replace('ROWS',json.dumps(rows))
 (w/'shell.qml').write_text(qml)
 env={**os.environ,'PATH':str(b)+':'+os.environ['PATH'],'QT_QPA_PLATFORM':'wayland'}
 p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env=env,capture_output=True,text=True,timeout=10);log=p.stdout+p.stderr
 assert p.returncode==0 and 'VERIFICATION_PROCESS_PASS' in log,log
 for bad in ('TypeError:','ReferenceError','Unable to assign','Binding loop','Error:'):assert bad not in log,log
 args=json.loads(marker.read_text());assert args[0]=='--app-id=org.omarchy.doctor-verification' and 'verify-packages' in args and 'sudo' not in args,args
 c=sqlite3.connect(db);assert c.execute('select count(*) from fixes').fetchone()[0]==0;assert c.execute('select count(*) from receipts').fetchone()[0]==0;assert c.execute('select count(*) from event_observations where check_id="shell"').fetchone()[0]==145;c.close()
 print(log);print('PASS fake dispatcher captured only normal user terminal request; no sudo/authentication or real diagnostics executed.')
