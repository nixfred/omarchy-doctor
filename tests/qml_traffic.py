"""Closed native fixtures for bar colors, direct routing, recovery and no automatic repair."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
if not os.environ.get('XDG_RUNTIME_DIR') or not os.environ.get('WAYLAND_DISPLAY'):raise SystemExit('Native tests require observed Wayland environment.')
with tempfile.TemporaryDirectory(prefix='doctor-traffic-qa-') as folder:
 w=Path(folder)
 for name in ('Commons','Ui','services'):(w/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
 for p in [*ROOT.glob('*.qml'),ROOT/'Model.js',ROOT/'doctor.py']:shutil.copy2(p,w/p.name)
 (w/'shell.qml').write_text('''import QtQuick
import Quickshell
import "Model.js" as Model
ShellRoot {
 Doctor{id:doctor;testMode:true}
 MedicalCross{id:icon;state:doctor.overallState;count:doctor.issueCount}
 property int step:0
 function ok(value,message){if(!value)throw new Error(message);console.log("PASS "+message)}
 function row(id,state){return {id:id,title:id,domain:"system",finding_number:"F-fixture-"+id,state:state,summary:"Fixture "+state,command:"fixture inspect",evidence:"Fixture exact output",timestamp:Date.now()/1000,metrics:{},needs_fix:state==="warn"||state==="bad",resolution:state==="unknown"?"unverified":state==="ok"?"verified_healthy":"unresolved",disposition:state==="unknown"?"investigate":state==="ok"?"monitor":"needs_fix"}}
 function apply(rows){doctor.scans=[];doctor.applyFixture(rows,[]);doctor.now=Date.now()/1000;doctor.routeConcern()}
 Timer{interval:160;repeat:true;running:true;onTriggered:{
  step++
  if(step===1){apply([row("services","ok")]);ok(doctor.overallState==="ok"&&doctor.page==="overview"&&doctor.issueCount===0,"fresh supported healthy opens green Overview");ok(icon.fill.toString()==="#2fa84f","healthy icon is green")}
  if(step===2){var major=row("services","bad"),minor=row("temperature","warn");major.priority=0;major.severity="critical";apply([minor,major]);ok(doctor.overallState==="bad"&&doctor.page==="issues"&&doctor.filter==="needs_fix"&&doctor.selected.id==="services","red click routes highest-priority major concern");ok(icon.fill.toString()==="#e5484d","major icon is red")}
  if(step===3){apply([row("services","ok"),row("temperature","warn")]);ok(doctor.overallState==="warn"&&doctor.selected.id==="temperature","recovered F57 is not reused; yellow routes current thermal warning");ok(icon.fill.toString()==="#d4a017"&&icon.symbol.toString()==="#191b20","yellow has high-contrast dark cross")}
  if(step===4){apply([row("services","ok"),row("packages","unknown")]);ok(doctor.overallState==="unknown"&&doctor.page==="verification"&&doctor.indicator.target.id==="packages","gray click opens actual uncertainty without claiming broken");ok(doctor.verificationTestItem()!==null,"gray explains exact coverage reason")}
  if(step===5){var f=row("crashes:old","warn");f.activity="historical";f.new_count=0;f.needs_fix=false;var events=row("crashes","warn");events.findings=[f];apply([row("services","ok"),events]);ok(doctor.overallState==="ok"&&doctor.issueCount===0&&doctor.page==="overview","historical noise changes neither healthy color nor badge")}
  if(step===6){apply([]);doctor.complete=false;doctor.routeConcern();ok(doctor.overallState==="unknown"&&doctor.page==="verification"&&!doctor.selected&&doctor.notice.indexOf("Finish")>=0,"gray no-finding fallback explains how to measure")}
  if(step===7){apply([row("services","ok")]);doctor.now=doctor.lastScan+700;doctor.routeConcern();ok(doctor.overallState==="unknown"&&doctor.page==="verification","stale healthy stays gray and routes recheck guidance")}
  if(step===8){var oldEvent=row("crashes:old-new","warn");oldEvent.needs_fix=false;oldEvent.activity="recurring";oldEvent.new_count=4;oldEvent.last_seen=Date.now()/1000-700;oldEvent.timestamp=Date.now()/1000-700;var group=row("crashes","warn");group.findings=[oldEvent];apply([row("services","ok"),row("packages","unknown"),group]);ok(doctor.issueCount===0&&doctor.indicator.coverage===1&&doctor.indicator.target.id==="packages","stale new flags do not count or select as current review items");apply([row("services","ok"),group]);ok(doctor.overallState==="ok"&&doctor.issueCount===0,"fresh healthy plus aged unreviewed event remains green without deleting history")}
  if(step===9){var event=row("crashes:current","warn");event.needs_fix=false;event.activity="new";event.new_count=1;event.last_seen=Date.now()/1000;event.priority=1;var group=row("crashes","warn");group.findings=[event];apply([row("services","ok"),row("packages","unknown"),group]);ok(doctor.issueCount===0&&doctor.indicator.coverage===1&&doctor.indicator.review===1&&doctor.indicator.target.id==="packages","current event review stays separate from repair badge and coverage")}
  if(step===10){var old=row("temperature","warn");old.timestamp=Date.now()/1000-700;apply([old,row("services","ok")]);ok(doctor.overallState==="unknown","old thermal warning never masquerades as current yellow");apply([row("temperature","ok")]);ok(!doctor.fixingId&&!doctor.workId&&!doctor.opened,"all icon routes launch no agent and never open live panel");console.log("TRAFFIC_UI_PASS");Qt.quit()}
 }}
}''')
 p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'wayland'},capture_output=True,text=True,timeout=8)
 log=p.stdout+p.stderr
 assert p.returncode==0 and 'TRAFFIC_UI_PASS' in log,log
 for bad in ['ERROR:','TypeError','ReferenceError','Unable to assign','Binding loop','Error:']:assert bad not in log,log
 print(log)
