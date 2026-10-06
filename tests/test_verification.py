"""Finite collection/privileged-read workflows; every external command is a fixture."""
import copy,json,sqlite3,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import doctor
BOOT='f'*32
class Journal:
 def __init__(self,count=205):
  self.rows=[dict(__CURSOR='c%d'%n,__REALTIME_TIMESTAMP=str(int((time.time()-20+n/1000)*1e6)),_BOOT_ID=BOOT,_COMM='quickshell',PRIORITY='6',MESSAGE=list(('\x1b[33mWARN pi.audio: TypeError: fixture\x1b[0m').encode())) for n in range(count)];self.calls=[];self.failure=None;self.drop=False
 def __call__(self,args,**kw):
  self.calls.append((args,kw))
  if any(x.startswith("--cursor=") for x in args) and any(x.startswith("--since=") for x in args):
   return dict(ok=False,code=1,stdout="",stderr="Please specify only one of --since= and --cursor=.",output="Please specify only one of --since= and --cursor=.",command="fixture journal")
  if self.failure:return self.failure
  cursor=next((x.split('=',1)[1] for x in args if x.startswith('--cursor=')),None)
  start=next((n for n,e in enumerate(self.rows) if e['__CURSOR']==cursor),0) if cursor else 0
  if cursor and self.drop:start+=1
  size=int(next(x.split('+')[1] for x in args if x.startswith('--lines=')))
  raw=self.rows[start:start+size]
  return dict(ok=True,code=0,stdout='\n'.join(json.dumps(e) for e in raw),stderr='',output='',command='fixture journal')
class Verification(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'history.sqlite3';doctor.STOP.clear()
  inventory=patch.object(doctor,'package_inventory',return_value='fixture-inventory')
  inventory.start();self.addCleanup(inventory.stop)
 def tearDown(self):doctor.STOP.clear();self.tmp.cleanup()
 def step(self,j,**kw):return doctor.complete_shell(self.db,run=j,boot=BOOT,**kw)
 def test_pages_resume_eof_and_stable_identity(self):
  j=Journal();r,a=self.step(j,max_pages=1);self.assertEqual(a['phase'],'collecting');self.assertEqual(a['raw_entries'],100);self.assertEqual(r['state'],'unknown');ident=r['findings'][0]['finding_number']
  r,b=self.step(j);self.assertEqual(b['phase'],'complete');self.assertEqual(b['raw_entries'],205);self.assertEqual(b['pages'],3);self.assertEqual(r['findings'][0]['event_count'],205);self.assertEqual(r['findings'][0]['finding_number'],ident);self.assertFalse(r['needs_fix']);self.assertTrue(r['coverage']['complete'])
  self.assertIn('--cursor=c99',j.calls[1][0]);self.assertIn('--lines=+101',j.calls[1][0]);self.assertTrue(all('--until=' in ' '.join(c[0]) for c in j.calls));self.assertFalse(any('-n 500' in ' '.join(c[0]) for c in j.calls))
 def test_cursor_pages_keep_fixed_scope_without_conflicting_since(self):
  j=Journal();r,first=self.step(j,max_pages=1);r,last=self.step(j)
  self.assertEqual(last['phase'],'complete');self.assertEqual(last['raw_entries'],205)
  self.assertTrue(any(x.startswith('--since=') for x in j.calls[0][0]))
  for args,kw in j.calls[1:]:
   self.assertTrue(any(x.startswith('--cursor=') for x in args));self.assertFalse(any(x.startswith('--since=') for x in args))
   self.assertIn('--boot='+BOOT,args);self.assertIn('--until=@%.6f'%first['until'],args)
  before=len(j.calls);r,last=self.step(j);self.assertEqual(last['phase'],'complete')
  self.assertIn('--cursor=c204',j.calls[before][0]);self.assertFalse(any(x.startswith('--since=') for x in j.calls[before][0]))
 def test_cursor_resume_still_rejects_records_outside_fixed_snapshot(self):
  j=Journal(150);r,first=self.step(j,max_pages=1)
  j.rows[100]['__REALTIME_TIMESTAMP']=str(int((first['until']+1)*1e6))
  r,last=self.step(j);self.assertEqual(last['phase'],'blocked');self.assertTrue(last['requires_restart']);self.assertEqual(r['state'],'unknown')
  self.assertIn('Entry outside the requested snapshot',last['error'])
 def test_exact_page_requires_confirmed_next_page(self):
  j=Journal(100);r,a=self.step(j,max_pages=1);self.assertEqual(a['phase'],'collecting');r,a=self.step(j);self.assertEqual(a['phase'],'complete');self.assertEqual(a['raw_entries'],100)
 def test_incremental_never_replays_complete_baseline(self):
  j=Journal();self.step(j);oldcalls=len(j.calls);r,a=self.step(j);self.assertEqual(a['raw_entries'],205);self.assertEqual(j.calls[oldcalls][0][-4:],doctor.SHELL_MATCHES[-4:]);self.assertIn('--cursor=c204',j.calls[oldcalls][0]);self.assertTrue(all(f['new_count']==0 for f in r['findings']))
 def test_timeout_keeps_cursor_and_resumes(self):
  j=Journal();self.step(j,max_pages=1);j.failure=dict(ok=False,code=124,output='Timed out');r,a=self.step(j);self.assertEqual(r['state'],'unknown');self.assertEqual(doctor.verification_job(self.db,'shell')['cursor'],'c99');j.failure=None;r,a=self.step(j);self.assertEqual(a['phase'],'complete');self.assertEqual(a['raw_entries'],205)
 def test_cursor_loss_requires_restart_no_false_eof(self):
  j=Journal();self.step(j,max_pages=1);j.drop=True;r,a=self.step(j);self.assertEqual(a['phase'],'blocked');self.assertTrue(a['requires_restart']);self.assertEqual(r['state'],'unknown');j.drop=False;r,a=self.step(j,restart=True);self.assertEqual(a['phase'],'complete');self.assertEqual(r['findings'][0]['event_count'],205)
 def test_bad_message_keeps_adjacent_valid_warning(self):
  j=Journal(3);j.rows[1]['MESSAGE']={'bad':True};r,a=self.step(j);self.assertEqual(a['phase'],'blocked');self.assertEqual(r['findings'][0]['event_count'],2);self.assertTrue(a['requires_restart']);n=len(j.calls);self.step(j);self.assertEqual(len(j.calls),n)
 def test_cancel_is_resumable(self):
  j=Journal();doctor.STOP.set();r,a=self.step(j);self.assertEqual(a['phase'],'paused');self.assertEqual(a['raw_entries'],0);doctor.STOP.clear();r,a=self.step(j);self.assertEqual(a['phase'],'complete')
 def test_progress_and_empty_valid_snapshot(self):
  progress=[];r,a=self.step(Journal(0),progress=progress.append);self.assertEqual(a['phase'],'complete');self.assertEqual(r['state'],'ok');self.assertEqual(len(progress),1)
 def test_boot_change_restarts_snapshot_and_keeps_old_ids(self):
  j=Journal(3);r,a=self.step(j);number=r['findings'][0]['finding_number'];j.rows=[dict(e,_BOOT_ID='a'*32) for e in j.rows];r,b=doctor.complete_shell(self.db,run=j,boot='a'*32);self.assertNotEqual(a['id'],b['id']);self.assertEqual(r['findings'][0]['finding_number'],number)
 def test_package_launcher_exact_safe_terminal_no_root_doctor(self):
  launched=[];a=doctor.start_package_verification(self.db,launch=launched.append);b=doctor.start_package_verification(self.db,launch=launched.append);self.assertEqual(a['id'],b['id']);self.assertEqual(len(launched),1);self.assertEqual(launched[0][0],'omarchy-launch-tui');self.assertIn('verify-packages',launched[0]);self.assertNotIn('sudo',launched[0])
 def package_run(self,out='fixture: 1 total files, 0 missing files',err='',code=0):
  calls=[]
  def run(args,**kw):
   calls.append((args,kw));text='' if args==['pacman','-Qtdq'] else out
   return dict(ok=True,code=1 if args==['pacman','-Qtdq'] else code,stdout=text,stderr=err,output=text+err,command='fixture')
  return run,calls
 def test_package_only_fixed_pacman_elevated_and_complete_measured(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None);run,calls=self.package_run();r,j=doctor.verify_packages(self.db,a['id'],run=run);self.assertEqual(r['state'],'ok');self.assertTrue(r['metrics']['integrity_complete']);self.assertEqual(j['phase'],'complete');self.assertEqual(calls[1][0],['/usr/bin/sudo','/usr/bin/pacman','-Qk']);self.assertEqual(calls[1][1]['timeout'],120);self.assertEqual(calls[0][0],['pacman','-Qtdq'])
 def test_package_cancel_or_timeout_stays_unknown(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None)
  def run(args,**kw):return dict(ok=False,code=124,output='Authentication cancelled')
  r,j=doctor.verify_packages(self.db,a['id'],run=run);self.assertEqual(r['state'],'unknown');self.assertEqual(j['phase'],'blocked')
 def test_package_actual_missing_is_fault_not_gap(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None);run,calls=self.package_run('fixture: 1 total files, 1 missing file','warning: fixture: /fixture/missing (No such file or directory)',1);r,j=doctor.verify_packages(self.db,a['id'],run=run);self.assertEqual(r['state'],'warn');self.assertTrue(r['needs_fix']);self.assertEqual(j['phase'],'complete')
 def test_fresh_privileged_evidence_reused_without_elevation_or_retimestamp(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None);run,calls=self.package_run();measured,j=doctor.verify_packages(self.db,a['id'],run=run);calls.clear();row=doctor.Probes(run,database=self.db).packages(False);self.assertEqual(row['state'],'ok');self.assertEqual(row['timestamp'],measured['timestamp']);self.assertEqual([c[0] for c in calls],[['pacman','-Qtdq']]);self.assertIn('no new elevated',row['coverage_note'])
 def test_expired_privileged_evidence_stays_unknown_not_optional_skipped(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None);run,calls=self.package_run();doctor.verify_packages(self.db,a['id'],run=run);h=doctor.History(self.db);job=doctor.verification_job(self.db,'packages');job['row']['timestamp']=time.time()-601;doctor.put_job(h,job);h.close();row=doctor.Probes(run,database=self.db).packages(False);self.assertEqual(row['state'],'unknown');self.assertTrue(row['verification_expired'])
 def test_large_pages_shrink_and_still_read_through_eof(self):
  j=Journal(150)
  def run(args,**kw):
   size=int(next(x.split('+')[1] for x in args if x.startswith('--lines=')))
   if size>51:return dict(ok=True,code=0,stdout='x'*(1024*1024),stderr='',output='')
   return j(args,**kw)
  r,a=doctor.complete_shell(self.db,run=run,boot=BOOT);self.assertEqual(a['phase'],'complete');self.assertEqual(a['raw_entries'],150);self.assertEqual(a['page_size'],50)
 def test_closed_unstarted_terminal_is_explicit_interrupted(self):
  a=doctor.start_package_verification(self.db,launch=lambda a:None);h=doctor.History(self.db);job=doctor.verification_job(self.db,'packages');job['updated']=time.time()-31;h.db.execute('update verification_jobs set payload=? where check_id=?',(json.dumps(job),'packages'));h.db.commit();items=doctor.verification_jobs(h);h.close();self.assertEqual(items[0]['phase'],'interrupted');self.assertIn('no completed measurement',items[0]['error'])
 def test_boot_journal_same_scope_benign_and_core_policy(self):
  j=Journal(3);j.rows[0]['MESSAGE']='virt/tdx: TDX not supported by the host platform';j.rows[1]['SYSLOG_IDENTIFIER']='systemd-coredump';j.rows[2]['PRIORITY']='3';r,a=doctor.complete_shell(self.db,run=j,boot=BOOT,check='journal');self.assertEqual(r['id'],'journal');self.assertEqual(a['phase'],'complete');self.assertEqual(r['metrics']['journal_ignored'],2);self.assertEqual(len(r['findings']),1);self.assertIn('--priority=3',j.calls[0][0]);self.assertNotIn('--user',j.calls[0][0]);self.assertIn('--all',j.calls[0][0]);self.assertEqual(r['findings'][0]['evidence_kind'],'log_warning');self.assertFalse(r['needs_fix'])
 def test_boot_journal_invalid_fields_do_not_earn_green(self):
  j=Journal(3);j.rows[1]['MESSAGE']=None;r,a=doctor.complete_shell(self.db,run=j,boot=BOOT,check='journal');self.assertEqual(r['state'],'unknown');self.assertTrue(a['requires_restart']);self.assertEqual(r['findings'][0]['event_count'],2)
 def test_package_needs_matching_user_trigger(self):
  with self.assertRaises(ValueError):doctor.verify_packages(self.db,'not-user-triggered',run=lambda *a:None)
if __name__=='__main__':unittest.main()
