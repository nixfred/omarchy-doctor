"""Offscreen native layout fixtures; no live panel, probes, or agent."""
import json,os,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path(os.environ.get('DOCTOR_RUNTIME_ROOT',str(Path(__file__).resolve().parents[1])))
SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
rows=[dict(id=k,finding_number='F-'+k,title=k,state='unknown' if k!='services' else 'ok',summary='Invented measurement',metrics={},timestamp=1791202000,needs_fix=False,disposition='investigate' if k!='services' else 'monitor',resolution='unverified' if k!='services' else 'verified_healthy',command='fixture inspect',evidence='Invented evidence',diagnosis='Not established') for k in ['services','packages','shell']]
source=(ROOT/'Doctor.qml').read_text();bindings=source[source.index('    property string version:'):source.index('    function args(')]
bindings='\n'.join(line for line in bindings.splitlines() if 'property int preferredWidth:' not in line and 'property real readingHeight:' not in line and 'verifier.running' not in line)
methods='\n'.join(line for line in source.splitlines() if line.strip().startswith(('function openFix(', 'function fixable(', 'function applyFixture(')))
host='import QtQuick\nimport qs.Commons\nimport "Model.js" as Model\nQtObject {id:root;property var settings:({});property bool opened:true;property real readingHeight:560\n'+bindings+'\n'+methods+'''
 function setting(name,fallback){return settings[name]===undefined?fallback:settings[name]}
 function routeConcern(){filter="investigate";selectedId="shell";page="verification"}
 function navigate(a){} function showFindings(a){} function fixIssue(a){} function recheck(a){} function assessFinding(a,b,c){} function loadHistory(){} function exportReport(){} function saveSetting(a,b){} function chooseAgent(){} function openUrl(a){} function copyCommand(a){}
}'''
qml='''import QtQuick
import QtQuick.Window
import Quickshell
import "Model.js" as Model
ShellRoot {
 FixtureHost{id:host;testMode:true;readingHeight:reader.viewportHeight;settings:({motion:false,refreshSeconds:300})}
 property int step:0
 property var sizes:[640,900,1280,1440,1800]
 function ok(v,m){if(!v)throw new Error(m);console.log("PASS "+m)}
 function find(item,name){if(item.objectName===name)return item;for(var i=0;i<item.children.length;i++){var x=find(item.children[i],name);if(x)return x}return null}
 Window{id:win;visible:true;width:640;height:480;color:host.surface
  Rectangle{anchors.fill:parent;color:host.surface}
  ReadPages{id:reader;x:16;y:16;width:win.width-32;height:win.height-32;ink:host.ink;accent:host.good;IssuesPane{id:issues;width:reader.width;host:host}}
  OverviewPane{id:overview;visible:false;width:win.width-32;host:host}
 }
 Timer{interval:140;running:true;repeat:true;onTriggered:{
  step++
  if(step===1){host.now=1791202000;host.applyFixture(ROWS,[]);host.hostname="Invented fixture";host.filter="needs_fix"
   ok(Model.disposition({activity:"historical",needs_fix:false,disposition:"investigate",resolution:"unresolved"})==="PAST EVENT · NOT REVIEWED","history not a repair claim")
   ok(Model.disposition({activity:"historical",needs_fix:true})==="STILL NEEDS ACTION","explicit action preserved")
   ok(Model.disposition({state:"unknown",resolution:"unverified"}).indexOf("NEEDS VERIFICATION")===0,"unknown preserved")
   ok(Model.disposition({state:"ok",resolution:"verified_healthy",recovery:{kind:"without_handoff"}}).indexOf("WITHOUT A DOCTOR HANDOFF")>=0,"recovery credit honest")
   ok(Model.issueSummary(ROWS,true,false).indexOf("No known actionable problems in checked scope. 2 checks need verification.")===0,"two gaps explained")
   ok(Model.issueSummary(ROWS,true,false,1791203000).indexOf("Measurements are old")===0,"old measurements explicitly scoped to saved checkup");ok(Model.disposition({needs_fix:true,state:"warn",timestamp:1791202000},1791203000)==="SAVED WARNING · RECHECK CURRENT STATE","old warning is not claimed current");ok(Model.issueSummary(ROWS,false,false).indexOf("unfinished")>=0,"unfinished cannot claim health")
  }
  if(step>=3&&step<=7){var e=find(issues,"doctor-empty-findings");ok(e&&e.visible&&e.width>0&&e.x>=0&&e.x+e.width<=e.parent.width+1,"empty message inside card "+win.width);ok(e.paintedWidth<=e.width+1&&e.wrapMode===Text.WordWrap,"empty message wraps");ok(reader.height===win.height-32&&reader.viewportHeight>0,"viewport fits scene");ok(reader.contentHeight<=reader.viewportHeight||reader.pageCount>1,"overflow has explicit pages")}
  if(step>=2&&step<=6){win.width=sizes[step-2];win.height=step===2?480:step===3?600:step===4?720:step===5?900:1050;reader.reset()}
  if(step===8){win.width=900;win.height=600;host.filter="investigate";host.selectedId="shell";issues.evidenceOpen=true}
  if(step===9){var b=find(overview,"doctor-overview-review");ok(b&&b.text.indexOf("Finish verification")===0,"gray action visible");host.filter="needs_fix";b.clicked();ok(host.filter==="investigate"&&host.selectedId==="shell","gray routes exact finding");var fp=find(issues,"doctor-findings-pane");ok(fp.findingPage===Math.floor(host.filtered.map(function(r){return r.id}).indexOf(host.selected.id)/fp.perPage),"selected finding remains on its identity page");var a=reader.offsets;for(var i=1;i<a.length;i++)ok(a[i]>a[i-1]&&a[i]-a[i-1]<=reader.viewportHeight,"pages have no gaps");ok(a[a.length-1]+reader.viewportHeight>=reader.contentHeight,"final page includes content end");if(OUTPUT)win.contentItem.grabToImage(function(image){ok(image.saveToFile(OUTPUT),"screenshot saved")})}
  if(step===10){console.log("FIT_UI_PASS");Qt.quit()}
 }}
}'''.replace('ROWS',json.dumps(rows)).replace('OUTPUT',json.dumps(os.environ.get('DOCTOR_FIT_IMAGE','')))
for scale in ('1','1.25','1.5'):
 with tempfile.TemporaryDirectory(prefix='dq-') as folder:
  w=Path(folder);(w/'runtime').mkdir(mode=0o700)
  for name in ('Commons','Ui','services'):(w/name).symlink_to(SHELL/name,target_is_directory=True)
  for p in [*ROOT.glob('*.qml'),ROOT/'Model.js']:shutil.copy2(p,w/p.name)
  (w/'FixtureHost.qml').write_text(host);(w/'shell.qml').write_text(qml)
  env={**os.environ,'XDG_RUNTIME_DIR':str(w/'runtime'),'QT_QPA_PLATFORM':'offscreen','QT_QPA_PLATFORMTHEME':'','QT_STYLE_OVERRIDE':'Fusion','QT_QUICK_CONTROLS_STYLE':'Basic','QT_SCALE_FACTOR':scale,'DISPLAY':'','WAYLAND_DISPLAY':''}
  p=subprocess.run(['qs','--no-color','--path',str(w/'shell.qml')],env=env,capture_output=True,text=True,timeout=8);log=p.stdout+p.stderr
  assert p.returncode==0 and 'FIT_UI_PASS' in log,log
  for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','Binding loop','Flow will not function','Error:'):assert bad not in log,log
  print('PASS native wrapping/pagination/gray-route: scale '+scale+'; 640x480 through 1800x1050 logical scenes')
