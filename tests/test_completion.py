import contextlib,io,json,os,shlex,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor
from test_events import event
class CompletionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'history.sqlite3';self.h=doctor.History(self.path)
  self.row=doctor.result('services','system','Services','bad','Broken unit','test.service failed','systemctl --failed')
  self.h.save('initial','quick',[self.row])
 def tearDown(self):self.h.close();self.tmp.cleanup()
 def report(self,**kw):return {'outcome':'completed','summary':'Repaired fixture unit','changes':'Fixture change','validation':'Fixture test','rollback':'Restore saved fixture value',**kw}
 def test_claim_never_fixes_and_verified_after_restart_preserves_number(self):
  number=self.row['finding_number'];fix=self.h.open_fix(self.row,'fixture');self.h.record_report(fix,self.report())
  self.assertEqual(self.h.db.execute('SELECT status FROM fixes WHERE id=?',(fix,)).fetchone()[0],'reviewed_unproven')
  healthy=doctor.result('services','system','Services','ok','Healthy','No failed units')
  with patch.object(doctor.Probes,'services',return_value=healthy):self.h.verify_report(fix)
  f=self.h.fixes()[0];self.assertTrue(f['verified']);self.assertIn('No failed',f['after_evidence']);self.assertEqual(f['report']['rollback'],'Restore saved fixture value')
  self.h.close();self.h=doctor.History(self.path);self.assertEqual(self.h.latest()[0]['finding_number'],number)
  self.assertEqual(self.h.fixes()[0]['finding_number'],number)
 def test_duplicates_conflicts_late_result_and_newer_attempt(self):
  old=self.h.open_fix(self.row,'fixture');new=self.h.open_fix(self.row,'fixture')
  self.assertTrue(self.h.record_report(old,self.report()));self.assertFalse(self.h.record_report(old,self.report()))
  with self.assertRaises(ValueError):self.h.record_report(old,self.report(summary='Contradiction'))
  rows={f['id']:f for f in self.h.fixes()};self.assertEqual(rows[old]['status'],'superseded');self.assertEqual(rows[new]['status'],'pending')
  self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1)
 def test_agent_report_file_reconciles_without_callback(self):
  fix=self.h.open_fix(self.row,'any-agent');folder=self.path.parent/'handoffs';folder.mkdir()
  (folder/(fix+'-result.json')).write_text(json.dumps(self.report(outcome='blocked',summary='Needs approval')))
  with patch.object(doctor.Probes,'services',return_value=self.row):self.h.reconcile()
  self.assertEqual(self.h.fixes()[0]['report']['outcome'],'blocked');self.assertFalse(self.h.fixes()[0]['verified'])
 def test_missing_interrupted_and_failed_launch_are_not_fixed(self):
  fix=self.h.open_fix(self.row,'fixture');self.h.launch_state(fix,'running',999999999)
  self.h.reconcile();self.assertEqual(self.h.fixes()[0]['status'],'no_result')
  self.h.record_report(fix,self.report(outcome='interrupted'));self.h.launch_state(fix,'no_result',code=0)
  with patch.object(doctor.Probes,'services',return_value=self.row):
   self.assertEqual(self.h.fixes()[0]['status'],'interrupted');self.assertEqual(self.h.fixes()[0]['phase'],'reported')
  other=self.h.open_fix(self.row,'fixture');self.h.launch_state(other,'launch_failed',code=127)
  self.assertEqual(self.h.fixes()[0]['status'],'launch_failed')
 def test_unavailable_recheck_cannot_be_healthy(self):
  fix=self.h.open_fix(self.row,'fixture');self.h.record_report(fix,self.report())
  with patch.object(doctor.Probes,'services',return_value=doctor.result('services','system','Services','unknown','Permission denied')):self.h.verify_report(fix)
  self.assertFalse(self.h.fixes()[0]['verified']);self.assertFalse(self.h.latest()[0]['needs_fix']);self.assertEqual(self.h.latest()[0]['resolution'],'unverified')
 def test_historical_actionable_stays_needs_fix_and_no_new_is_not_fixed(self):
  r=doctor.event_row('crashes','Crashes',[{'__CURSOR':'x','__REALTIME_TIMESTAMP':str(int((time.time()-100)*1e6)),'COREDUMP_EXE':'/app','COREDUMP_SIGNAL':'11','COREDUMP_PID':'42'}],'inspect')
  self.h.save('events','quick',[r]);f=r['findings'][0];n=f['finding_number'];self.assertFalse(f['needs_fix'])
  self.h.assess(f['id'],'needs_fix','Actual desktop crash remains unexplained');self.h.annotate([r]);self.assertTrue(f['needs_fix']);self.assertEqual(f['activity'],'historical')
  fix=self.h.open_fix(f,'fixture');self.h.record_report(fix,self.report())
  with patch.object(doctor.Probes,'crashes',return_value=doctor.result('crashes','system','Crashes','ok','No matching records',metrics={})) :self.h.verify_report(fix)
  self.assertEqual(self.h.db.execute('SELECT status FROM fixes WHERE id=?',(fix,)).fetchone()[0],'reviewed_unproven');self.assertFalse(self.h.fixes()[0]['verified'])
  self.h.close();self.h=doctor.History(self.path);self.assertEqual(self.h.identity(f['id']),n)
 def test_recurrence_reopens_state_issue_without_losing_report(self):
  fix=self.h.open_fix(self.row,'fixture');self.h.record_report(fix,self.report())
  healthy=doctor.result('services','system','Services','ok','Healthy','No failed units');self.h.settle([healthy],'recheck')
  self.h.db.execute('UPDATE fixes SET resolved=? WHERE id=?',(time.time()-86400*3,fix));self.h.db.commit()
  self.h.save('regression','quick',[self.row]);self.assertEqual(self.h.fixes()[0]['status'],'regressed');self.assertTrue(self.h.latest()[0]['needs_fix']);self.assertEqual(self.h.fixes()[0]['report']['changes'],'Fixture change');self.assertTrue(any(v['outcome']=='healthy' for v in self.h.fixes()[0]['verifications']))
 def test_new_does_not_imply_needs_fix_and_assessment_persists(self):
  r=doctor.event_row('journal','Journal',[event('event',time.time()+1)],'inspect');self.h.save('new','quick',[r]);f=r['findings'][0]
  self.assertEqual(f['activity'],'new');self.assertFalse(f['needs_fix'])
  self.h.assess(f['id'],'monitor','Known historical symptom');self.h.annotate([r]);self.assertFalse(f['needs_fix'])
  self.assertEqual(f['severity'],'info');self.assertTrue(f['evidence_source']);self.assertTrue(f['rationale'])
 def test_invalid_receipt_does_not_change_state(self):
  fix=self.h.open_fix(self.row,'fixture')
  for data in ({},{'outcome':'fixed','summary':'Trust me'},self.report(validation=42)):
   with self.assertRaises(ValueError):self.h.record_report(fix,data)
  self.assertEqual(self.h.fixes()[0]['status'],'pending')
 def test_agent_independent_end_to_end_handoff_callback_and_restart(self):
  # A fake terminal/agent obeys the same receipt contract; all diagnostics use an isolated systemctl fixture.
  base=Path(self.tmp.name);binpath=base/'bin';binpath.mkdir();ctl=binpath/'systemctl';ctl.write_text('#!/bin/sh\nexit 0\n');ctl.chmod(0o755)
  agent=base/'agent.py';agent.write_text('''import json,shlex,sys,subprocess
prompt=sys.argv[1]
line=next(x.strip() for x in prompt.splitlines() if ' report ' in x and '--result-file' in x)
cmd=shlex.split(line);path=cmd[cmd.index('--result-file')+1]
with open(path,'w') as f:json.dump({'outcome':'completed','summary':'Fixture done','changes':'No host changes','validation':'Isolated systemctl','rollback':'No changes to undo'},f)
subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
''')
  env={**os.environ,'PATH':str(binpath)+':'+os.environ['PATH'],'DOCTOR_AGENT_COMMAND':shlex.join([sys.executable,str(agent)])}
  p=subprocess.run([sys.executable,doctor.__file__,'fix','services','--agent','fixture','--database',str(self.path)],env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(p.returncode,0,p.stderr+p.stdout);start=json.loads(p.stdout);self.assertTrue(start['launched'])
  deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   status=self.h.db.execute('SELECT status FROM fixes ORDER BY started DESC LIMIT 1').fetchone()[0]
   if status=='fixed':break
   time.sleep(.05)
  f=self.h.fixes()[0]
  self.assertTrue(f['verified'],f);self.assertEqual(f['report']['rollback'],'No changes to undo')
  self.h.close();self.h=doctor.History(self.path);self.assertTrue(self.h.fixes()[0]['verified'])

class RecoveryTests(unittest.TestCase):
 def test_grok_correlates_exact_completed_single_prompt_and_partial_log(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);session=root/'sessions'/'%2Fwork'/'session-one';session.mkdir(parents=True)
   (root/'active_sessions.json').write_text(json.dumps([{'cwd':'/work','session_id':'session-one'}]))
   (session/'chat_history.jsonl').write_text(json.dumps({'type':'user','prompt_index':'0','content':'Doctor fix abc'})+'\n'+json.dumps({'type':'assistant','content':'No machine changes; old event remains unproven'})+'\n')
   (root/'logs').mkdir();(root/'logs/unified.jsonl').write_text(json.dumps({'ts':'2026-10-05T03:16:00Z','sid':'session-one','msg':'turn.complete','ctx':{'ok':True}})+'\n'+ '{partial')
   with patch.dict(os.environ,{'GROK_HOME':folder}):
    self.assertTrue(doctor.grok_report('abc',1));self.assertIsNone(doctor.grok_report('wrong',1))
    with (session/'chat_history.jsonl').open('a') as f:f.write(json.dumps({'type':'user','prompt_index':'1','content':'Another unfinished task'})+'\n')
    self.assertIsNone(doctor.grok_report('abc',1))
 def test_concurrent_duplicate_receipts_are_atomic(self):
  import concurrent.futures,threading
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'db';h=doctor.History(path);fix=h.open_fix(doctor.result('services','system','Services','bad','Fixture'),'fixture');h.close()
   barrier=threading.Barrier(2)
   def send():
    h=doctor.History(path);barrier.wait()
    try:return h.record_report(fix,{'outcome':'completed','summary':'One identical receipt'})
    finally:h.close()
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:send(),range(2)))
   self.assertEqual(sorted(results),[False,True])
   h=doctor.History(path);self.assertEqual(h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1);h.close()
