#!/usr/bin/env python3
"""Render current native Doctor panes offscreen with invented documentation fixtures."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,default=ROOT)
parser.add_argument('--shell-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
# Fixed illustrative timestamps and invented identities; never read the live database.
now=1785585900
specs=[('services','system','System & user services'),('journal','system','Boot journal'),('cpu','cpu','Processor activity'),('memory','ram','Memory headroom'),('temperature','devices','Temperature'),('storage','disk','Root filesystem'),('drives','disk','Physical drive health'),('gpu','gpu','Graphics & driver'),('battery','devices','Battery'),('network','network','Route & DNS'),('packages','system','Package integrity'),('audio','devices','Audio'),('bluetooth','devices','Bluetooth'),('wifi','network','Wi-Fi'),('crashes','system','Application crashes'),('shell','system','Omarchy shell')]
rows=[]
for i,(key,domain,title) in enumerate(specs):
    warning=key=='storage'
    rows.append(dict(id=key,domain=domain,title=title,finding_number=f'F-{i+1:06d}',state='warn' if warning else 'ok',summary='Example root filesystem is 87% full.' if warning else 'Example check completed with no concern.',metrics={},timestamp=now,duration_ms=125,needs_fix=warning,disposition='needs_fix' if warning else 'monitor',resolution='unresolved' if warning else 'verified_healthy',diagnosis='Storage use exceeds the attention threshold. Review files before changing anything.' if warning else 'Example healthy result.',evidence_source='df (illustrative fixture)',evidence_timestamp=now,rationale='Used root filesystem space exceeds the attention threshold.',command='df -h /' if warning else 'uptime',evidence='ILLUSTRATIVE FIXTURE — not a real diagnosis.\nFilesystem  Size  Used  Avail  Use%  Mounted on\n/dev/example  100G   87G    13G   87%  /'))
samples=[dict(timestamp=now-177+i*3,metrics={'cpu_pct':25+(i%7)*5,'ram_available_gib':18+(i%4)/5,'ram_used_pct':60,'disk_used_pct':87,'gpu_pct':6+i%5}) for i in range(60)]
fix=dict(id='example-attempt',check='storage',finding_number='F-000006',handoff_number='H-000001',title='Example storage investigation',status='still_failing',started=now-120,agent='example-agent',verified=False,before_summary='Example filesystem is 87% full.',after_summary='Example recheck still shows 87% used.',before_timestamp=now-120,verified_at=now,before_command='df -h /',after_command='df -h /',before_evidence='Example reading: 87% used.',after_evidence='Example reading: 87% used.',report={'summary':'Illustrative report: reviewed storage usage; no files were removed.','changes':'None. Inspection only.','validation':'Reviewed the supplied example disk reading.','rollback':'No changes to undo.'},verifications=[{'timestamp':now,'outcome':'failing','row':{'command':'df -h /','summary':'Example storage warning remains.','evidence':'Illustrative reading: 87% used.'}}])
qml='''import QtQuick
import QtQuick.Window
import Quickshell
import qs.Commons
import "Model.js" as Model
ShellRoot {
 FixtureHost{id:doctor;testMode:true;settings:({motion:false,refreshSeconds:300});configuredAgent:"example-agent"}
 property int step:0
 property var shots:[{name:"overview",pane:"overview",height:780},{name:"issues",pane:"issues",height:710},{name:"evidence",pane:"evidence",height:575},{name:"inspect",pane:"inspect",height:575},{name:"repair",pane:"repair",height:560},{name:"repair-proof",pane:"repair-proof",height:560},{name:"history",pane:"history",height:725},{name:"settings",pane:"settings",height:740},{name:"about",pane:"about",height:615}]
 Window{id:win;visible:true;width:1120;height:790;color:doctor.surface
  Rectangle{anchors.fill:parent;color:doctor.surface}
  Column{id:content;x:28;y:26;width:win.width-56;spacing:16
   Loader{id:pane;width:parent.width;sourceComponent:overview;onLoaded:if(item)item.width=Qt.binding(function(){return pane.width})}
  }
 }
 Component{id:overview;OverviewPane{host:doctor}}
 Component{id:issues;IssuesPane{host:doctor}}
 Component{id:evidence;FindingsPane{host:doctor;evidenceOpen:true}}
 Component{id:repair;FixesPane{host:doctor}}
 Component{id:history;HistoryPane{host:doctor}}
 Component{id:settings;SettingsPane{host:doctor}}
 Component{id:about;AboutPane{host:doctor}}
 function next(){
  if(step>=shots.length){console.log("DOCS_RENDER_PASS");Qt.quit();return}
  var shot=shots[step];win.height=shot.height
  pane.sourceComponent=shot.pane==="overview"?overview:shot.pane==="issues"?issues:(shot.pane==="evidence"||shot.pane==="inspect")?evidence:(shot.pane==="repair"||shot.pane==="repair-proof")?repair:shot.pane==="history"?history:shot.pane==="settings"?settings:about
  ready.restart()
 }
 function scrollEvidence(item,offset){
  if(item.contentHeight!==undefined&&item.contentWidth!==undefined&&item.contentHeight>item.height+100&&item.width>450)item.contentY=offset
  for(var i=0;i<item.children.length;i++)scrollEvidence(item.children[i],offset)
 }
 Timer{id:ready;interval:350;onTriggered:{
  if(shots[step].pane==="repair"||shots[step].pane==="repair-proof"){doctor.fixes=[FIX];pane.item.showFirstWork()}
  if(shots[step].pane==="evidence"){pane.item.evidenceOpen=true;scrollEvidence(pane.item,160)}
  if(shots[step].pane==="inspect"){pane.item.evidenceOpen=true;scrollEvidence(pane.item,465)}
  capture.restart()
 }}
 Timer{id:capture;interval:300;onTriggered:{if(shots[step].pane==="repair-proof")scrollRepair(pane.item);settled.restart()}}
 function scrollRepair(item){if(item.contentHeight!==undefined&&item.contentWidth!==undefined&&item.contentHeight>item.height+100&&item.width>900)item.contentY=220;for(var i=0;i<item.children.length;i++)scrollRepair(item.children[i])}
 Timer{id:settled;interval:150;onTriggered:win.contentItem.grabToImage(function(result){
  var name=shots[step].name,path=OUTPUT+"/"+name+".png"
  if(!result.saveToFile(path))throw new Error("Could not save "+name)
  console.log("DOCS_CAPTURE "+name+" "+win.width+"x"+win.height);step++;next()
 })}
 Component.onCompleted:{
  Color.popups.background="#111914";Color.popups.text="#eef5ed"
  doctor.applyFixture(ROWS,SAMPLES);doctor.now=NOW;doctor.lastScan=NOW;doctor.vitalsAt=NOW;doctor.hostname="Example desktop";doctor.duration=1350;doctor.selectedId="storage";doctor.historyMetric="cpu_pct";doctor.historySeconds=3600
  doctor.fixes=[];doctor.scans=[{timestamp:NOW,mode:"quick",state:"warn",rows:ROWS},{timestamp:NOW-300,mode:"quick",state:"ok",rows:[]}]
  next()
 }
}'''
for key,value in [('FIX',fix),('ROWS',rows),('SAMPLES',samples),('NOW',now),('OUTPUT',str(args.output.resolve()))]:qml=qml.replace(key,json.dumps(value))
with tempfile.TemporaryDirectory(prefix='doctor-docs-') as folder:
    work=Path(folder)
    for name in ('Commons','Ui','services'):(work/name).symlink_to(args.shell_root.resolve()/name,target_is_directory=True)
    for src in [*args.source_root.glob('*.qml'),args.source_root/'Model.js',args.source_root/'doctor.py']:shutil.copy2(src,work/src.name)
    # Reuse the actual application's presentation bindings without its Wayland-only panel.
    source=(args.source_root/'Doctor.qml').read_text()
    bindings=source[source.index('    property string version:'):source.index('    function args(')]
    bindings='\n'.join(line for line in bindings.splitlines() if 'property int preferredWidth:' not in line)
    methods='\n'.join(line for line in source.splitlines() if line.strip().startswith(('function openFix(', 'function fixable(', 'function applyFixture(')))
    fixture_host='import QtQuick\nimport qs.Commons\nimport "Model.js" as Model\nQtObject { id:root; property var settings:({}); property bool opened:true\n'+bindings+'\n'+methods+\
        '\n function setting(name,fallback){return settings[name]===undefined?fallback:settings[name]}\n'+\
        'function navigate(page){} function showFindings(check){} function fixIssue(check){} function recheck(check){} function assessFinding(check,disposition,reason){} function loadHistory(){} function exportReport(){} function saveSetting(key,value){} function chooseAgent(){} function openUrl(url){} function copyCommand(text){}\n}'
    (work/'FixtureHost.qml').write_text(fixture_host)
    (work/'shell.qml').write_text(qml)
    env={**os.environ,'QT_QPA_PLATFORM':'offscreen','QT_QPA_PLATFORMTHEME':'','QT_STYLE_OVERRIDE':'Fusion','QT_QUICK_CONTROLS_STYLE':'Basic','DISPLAY':'','WAYLAND_DISPLAY':'','TZ':'UTC'}
    p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env=env,capture_output=True,text=True,timeout=20)
    log=p.stdout+p.stderr
    assert p.returncode==0 and 'DOCS_RENDER_PASS' in log,log
    for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Binding loop','Flow will not function'):assert bad not in log,log
    for name in ('overview','issues','evidence','inspect','repair','repair-proof','history','settings','about'):assert (args.output/f'{name}.png').stat().st_size>10000,name
    print('\n'.join(line for line in log.splitlines() if 'DOCS_' in line))
