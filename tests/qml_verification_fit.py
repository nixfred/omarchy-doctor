"""Visible offscreen checklist at five sizes/three scales; no tools or authentication."""
import os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])));SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
host='''import QtQuick
import qs.Commons
QtObject{
 property var shownRows:[{id:"shell",finding_number:"F-fixture-shell",state:"unknown",metrics:{},timestamp:Date.now()/1000},{id:"packages",finding_number:"F-fixture-packages",state:"unknown",metrics:{},timestamp:Date.now()/1000}]
 property real now:Date.now()/1000
 property var verificationJobs:[{check:"shell",phase:"collecting",raw_entries:1900,pages:19,until:Date.now()/1000,error:"",updated:Date.now()/1000}]
 property bool packageConfirmation:true
 property bool stale:true
 property bool complete:true
 property bool verifying:false
 property bool scanning:false
 property color ink:Color.popups.text
 property color dim:Qt.alpha(ink,.65)
 property color surface:Color.popups.background
 property color card:Qt.alpha(ink,.035)
 property color edge:Qt.alpha(ink,.14)
 property color good:"#a9d98b"
 property color warning:"#e8b572"
 function verificationJob(k){return verificationJobs.find(function(j){return j.check===k})||null}
 function verifyJournal(a){} function verifyShell(a){} function cancelVerification(){} function requestPackageVerification(){} function startPackageVerification(){} function showFindings(a){} function refresh(a){}
}'''
qml='''import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot{
 FixtureHost{id:host}
 property int step:0
 property var sizes:[[640,480],[900,600],[1280,720],[1440,900],[1800,1050]]
 function ok(v,m){if(!v)throw new Error(m)}
 function check(i){if(i.text!==undefined&&i.wrapMode!==undefined&&i.visible&&i.wrapMode===Text.WordWrap){ok(i.width>0&&i.paintedWidth<=i.width+1,"text wraps within width")}for(var n=0;n<i.children.length;n++)check(i.children[n])}
 function find(i,n){if(i.objectName===n)return i;for(var x=0;x<i.children.length;x++){var r=find(i.children[x],n);if(r)return r}return null}
 Window{id:win;visible:true;width:640;height:480
 Rectangle{anchors.fill:parent;color:host.surface}
 ReadPages{id:reader;x:16;y:16;width:win.width-32;height:win.height-32;ink:host.ink;accent:host.good;VerificationPane{id:pane;host:host;width:reader.width}}
 }
 Timer{interval:180;repeat:true;running:true;onTriggered:{step++
 if(step>=2&&step<=6){check(pane);ok(reader.viewportHeight>0&&reader.height===win.height-32,"fitted viewport");ok(reader.contentHeight<=reader.viewportHeight||reader.pageCount>1,"overflow reachable by explicit pages");var a=reader.offsets;for(var i=1;i<a.length;i++)ok(a[i]>a[i-1]&&a[i]-a[i-1]<=reader.viewportHeight,"reading pages have no gaps");ok(a[a.length-1]+reader.viewportHeight>=reader.contentHeight,"final page reaches confirmation and refresh");var b=find(pane,"doctor-confirm-package-verification");ok(b&&b.x>=0&&b.x+b.width<=b.parent.width+1,"approval action fits its flow");var c=find(pane,"doctor-verify-shell");ok(c&&c.text==="Continue collection"&&c.width<=c.parent.width,"finite collection action fits")}
 if(step<=5){win.width=sizes[step-1][0];win.height=sizes[step-1][1];reader.reset()}
 if(step===7){console.log("VERIFICATION_FIT_PASS");Qt.quit()}
 }}
}'''
for scale in ('1','1.25','1.5'):
 with tempfile.TemporaryDirectory(prefix='doctor-verification-fit-') as folder:
  w=Path(folder);(w/'runtime').mkdir(mode=0o700)
  for n in ('Commons','Ui','services'):(w/n).symlink_to(SHELL/n,target_is_directory=True)
  for p in [*ROOT.glob('*.qml'),ROOT/'Model.js']:shutil.copy2(p,w/p.name)
  (w/'FixtureHost.qml').write_text(host);(w/'shell.qml').write_text(qml)
  p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env={**os.environ,'QT_QPA_PLATFORM':'offscreen','XDG_RUNTIME_DIR':str(w/'runtime'),'DISPLAY':'','WAYLAND_DISPLAY':'','QT_QPA_PLATFORMTHEME':'','QT_QUICK_CONTROLS_STYLE':'Basic','QT_SCALE_FACTOR':scale},capture_output=True,text=True,timeout=8);log=p.stdout+p.stderr
  assert p.returncode==0 and 'VERIFICATION_FIT_PASS' in log,log
  for bad in ('TypeError','ReferenceError','Unable to assign','Binding loop','Error:'):assert bad not in log,log
  print('PASS visible native Finish verification wrap/pagination/actions at five sizes, scale '+scale)
