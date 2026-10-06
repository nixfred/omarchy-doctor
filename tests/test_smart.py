"""SMART auth workflow: commands, inventory and reader are all fake; no elevation."""
import copy,json,os,signal,stat,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
import doctor
INV=[dict(path='/dev/nvme0n1',major_minor='259:0',node_inode=42,serial='fixture',wwn='fixture',size=1000)]
def response(passed=True,code=0,ok=True,stderr='',stdout=None):
 text=json.dumps({'smart_status':{'passed':passed}}) if stdout is None else stdout
 return dict(ok=ok,code=code,stdout=text,stderr=stderr,output=text+stderr)
class Smart(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'history.sqlite3';doctor.STOP.clear();self.inventory=patch.object(doctor,'smart_inventory',return_value=copy.deepcopy(INV));self.inventory.start();self.addCleanup(self.inventory.stop)
 def tearDown(self):doctor.STOP.clear();self.tmp.cleanup()
 def start(self,**kw):return doctor.start_smart_verification(self.db,expected=copy.deepcopy(INV),launch=kw.pop('launch',lambda a:None),**kw)
 def measure(self,probe=None):
  a=self.start();calls=[]
  def run(args,**kw):calls.append(args);return response() if probe is None else probe
  row,job=doctor.verify_smart(self.db,a['id'],run=run);return row,job,calls
 def test_review_plan_and_only_fixed_packaged_reader(self):
  plan=doctor.smart_plan();self.assertEqual(plan['commands'],['/usr/bin/sudo /usr/bin/smartctl -j -H /dev/nvme0n1']);launched=[];a=self.start(launch=launched.append);b=self.start(launch=launched.append);self.assertEqual(a['id'],b['id']);self.assertEqual(len(launched),1);self.assertEqual(launched[0][0],'omarchy-launch-tui');self.assertNotIn('/usr/bin/sudo',launched[0]);self.assertIn('verify-smart',launched[0])
 def test_measured_health_complete_command_scope_and_receipt(self):
  row,job,calls=self.measure();self.assertEqual(calls,[['/usr/bin/sudo','/usr/bin/smartctl','-j','-H','/dev/nvme0n1']]);self.assertEqual(row['state'],'ok');self.assertTrue(row['metrics']['smart_complete']);self.assertEqual(job['phase'],'complete');self.assertIn('smartctl',row['command'])
 def test_health_failure_remains_bad(self):
  row,job,calls=self.measure(response(False,8));self.assertEqual(row['state'],'bad');self.assertTrue(row['needs_fix']);self.assertTrue(row['metrics']['smart_complete']);self.assertEqual(job['phase'],'complete')
 def test_cancel_denied_timeout_unsupported_invalid_all_stay_gray(self):
  for probe,phase in [(response(code=130,ok=False,stdout=''), 'canceled'),(response(code=1,ok=False,stderr='sudo: authentication failed',stdout=''),'denied'),(response(code=124,ok=False,stdout=''),'timeout'),(response(stdout='{}'),'unsupported'),(response(stdout='not JSON'),'unsupported'),(response(stdout='{"smart_status": []}'),'unsupported'),(response(code=2),'blocked'),(response(ok=False),'blocked')]:
   with self.subTest(phase=phase):
    row,job,calls=self.measure(probe);self.assertEqual(row['state'],'unknown');self.assertFalse(row['metrics']['smart_complete']);self.assertTrue(row['coverage_incomplete']);self.assertEqual(job['phase'],phase);self.assertFalse(row['needs_fix'])
 def test_cancel_before_reader_retains_unknown_receipt(self):
  a=self.start();doctor.STOP.set();run=Mock();row,job=doctor.verify_smart(self.db,a['id'],run=run);run.assert_not_called();self.assertEqual(job['phase'],'canceled');self.assertEqual(row['state'],'unknown')
 def test_invalid_token_never_launches_reader(self):
  self.start();run=Mock()
  with self.assertRaises(ValueError):doctor.verify_smart(self.db,'wrong-token',run=run)
  run.assert_not_called()
 def test_changed_plan_blocks_terminal_launch(self):
  launched=[]
  with patch.object(doctor,'smart_inventory',return_value=[dict(INV[0],serial='changed')]):a=self.start(launch=launched.append)
  self.assertEqual(a['phase'],'blocked');self.assertFalse(launched)
 def test_inventory_change_before_reader_starts_blocks_auth(self):
  a=self.start();run=Mock()
  with patch.object(doctor,'smart_inventory',return_value=[dict(INV[0],node_inode=43)]):row,job=doctor.verify_smart(self.db,a['id'],run=run)
  run.assert_not_called();self.assertEqual(row['state'],'unknown');self.assertEqual(job['phase'],'blocked')
 def test_inventory_change_after_read_cannot_claim_green(self):
  a=self.start()
  with patch.object(doctor,'smart_inventory',side_effect=[INV,[dict(INV[0],serial='changed')]]):row,job=doctor.verify_smart(self.db,a['id'],run=lambda *a,**kw:response())
  self.assertEqual(row['state'],'unknown');self.assertIn('changed during',job['error']);self.assertIn('passed',row['evidence'])
 def test_fresh_receipt_preserves_timestamp_no_elevation(self):
  measured,_,_=self.measure();run=Mock(side_effect=AssertionError('no additional reader allowed'));row=doctor.Probes(run,database=self.db).drives();run.assert_not_called();self.assertEqual(row['timestamp'],measured['timestamp']);self.assertEqual(row['state'],'ok');self.assertIn('no new elevated',row['coverage_note'])
 def test_expired_or_changed_receipt_stays_gray_preserves_evidence(self):
  measured,_,_=self.measure();h=doctor.History(self.db);job=doctor.verification_job(self.db,'drives');job['row']['timestamp']=time.time()-601;doctor.put_job(h,job);h.close();run=Mock(side_effect=AssertionError('no reader allowed'));row=doctor.Probes(run,database=self.db).drives();self.assertEqual(row['state'],'unknown');self.assertTrue(row['verification_expired']);self.assertFalse(row['metrics']['smart_complete']);self.assertEqual(row['evidence'],measured['evidence']);run.assert_not_called()
 def test_canceled_receipt_cannot_be_renewed_by_ordinary_scan(self):
  measured,_,_=self.measure(response(code=130,ok=False,stdout='cancel fixture'));run=Mock(side_effect=AssertionError('no reader allowed'));row=doctor.Probes(run,database=self.db).drives();self.assertEqual(row['timestamp'],measured['timestamp']);self.assertEqual(row['state'],'unknown');self.assertEqual(row['evidence'],measured['evidence']);run.assert_not_called()
 def test_closed_terminal_is_interrupted(self):
  self.start();h=doctor.History(self.db);job=doctor.verification_job(self.db,'drives');job['updated']=time.time()-31;h.db.execute('UPDATE verification_jobs SET payload=? WHERE check_id=?',(json.dumps(job),'drives'));h.db.commit();jobs=doctor.verification_jobs(h);h.close();self.assertEqual(jobs[0]['phase'],'interrupted')
class Inventory(unittest.TestCase):
 def discover(self,devices,**kw):
  info=SimpleNamespace(st_mode=stat.S_IFBLK|0o660,st_rdev=os.makedev(259,0),st_ino=42)
  with patch.object(doctor.os,'stat',return_value=info),patch.object(doctor.Path,'resolve',lambda p:p):return doctor.smart_inventory(lambda *a,**k:response(stdout=json.dumps({'blockdevices':devices})))
 def test_canonical_real_block_identity_and_zram_excluded(self):
  found=self.discover([dict(name='/dev/zram0',type='disk'),dict(name='/dev/nvme0n1',type='disk',**{'maj:min':'259:0'})]);self.assertEqual(found[0]['path'],'/dev/nvme0n1');self.assertEqual(found[0]['node_inode'],42)
 def test_invalid_paths_identity_duplicates_empty_over_limit_rejected(self):
  d=dict(name='/dev/nvme0n1',type='disk',**{'maj:min':'259:0'})
  for devices in [[],[dict(d,name='/dev/../etc/passwd')],[dict(d,**{'maj:min':'8:0'})],[d,d],[dict(d,name='/dev/disk'+str(n)) for n in range(17)]]:
   with self.subTest(devices=devices):
    with self.assertRaises(ValueError):self.discover(devices)
 def test_regular_file_or_symlink_not_device(self):
  d=dict(name='/dev/nvme0n1',type='disk',**{'maj:min':'259:0'})
  with patch.object(doctor.os,'stat',return_value=SimpleNamespace(st_mode=stat.S_IFREG,st_rdev=os.makedev(259,0))),patch.object(doctor.Path,'resolve',lambda p:p):
   with self.assertRaises(ValueError):doctor.smart_inventory(lambda *a,**k:response(stdout=json.dumps({'blockdevices':[d]})))
class Reader(unittest.TestCase):
 def call(self,args=None,uid=1000,tty=True,mode=stat.S_IFREG|0o755,owner=0):
  with patch.object(doctor.os,'geteuid',return_value=uid),patch.object(doctor.os,'getuid',return_value=1000),patch.object(doctor.sys.stdin,'isatty',return_value=tty),patch.object(doctor.os,'stat',return_value=SimpleNamespace(st_mode=mode,st_uid=owner)),patch.object(doctor.subprocess,'Popen') as launch:
   launch.return_value.wait.return_value=0;row=doctor.AuthenticatedSmartReader()(args or doctor.smart_read_command('/dev/nvme0n1'));return row,launch
 def test_root_unsafe_binary_no_tty_and_arbitrary_flags_never_execute(self):
  for kw in [dict(uid=0),dict(tty=False),dict(mode=stat.S_IFREG|0o777),dict(owner=1000),dict(args=['/usr/bin/sudo','/usr/bin/smartctl','-t','long','/dev/nvme0n1'])]:
   with self.subTest(kw=kw):row,launch=self.call(**kw);self.assertFalse(row['ok']);launch.assert_not_called()
 def test_retains_terminal_does_not_elevate_python(self):
  row,launch=self.call();args,kw=launch.call_args;self.assertEqual(args[0],doctor.smart_read_command('/dev/nvme0n1'));self.assertIsNone(kw['stdin']);self.assertFalse(kw['start_new_session']);self.assertEqual(row['code'],0)
 def test_reader_timeout_terminates_fake_process_never_claims_success(self):
  with patch.object(doctor.os,'geteuid',return_value=1000),patch.object(doctor.os,'getuid',return_value=1000),patch.object(doctor.sys.stdin,'isatty',return_value=True),patch.object(doctor.os,'stat',return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o755,st_uid=0)),patch.object(doctor.subprocess,'Popen') as launch:
   launch.return_value.wait.side_effect=[doctor.subprocess.TimeoutExpired('fixture',120),0];row=doctor.AuthenticatedSmartReader()(doctor.smart_read_command('/dev/nvme0n1'));self.assertEqual(row['code'],124);self.assertFalse(row['ok']);launch.return_value.terminate.assert_called_once()
 def test_truncated_fake_reader_output_never_claims_success(self):
  def fake(args,**kw):kw['stdout'].write(b'x'*(1024*1024+1));return SimpleNamespace(wait=lambda **k:0)
  with patch.object(doctor.os,'geteuid',return_value=1000),patch.object(doctor.os,'getuid',return_value=1000),patch.object(doctor.sys.stdin,'isatty',return_value=True),patch.object(doctor.os,'stat',return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o755,st_uid=0)),patch.object(doctor.subprocess,'Popen',side_effect=fake):
   row=doctor.AuthenticatedSmartReader()(doctor.smart_read_command('/dev/nvme0n1'));self.assertFalse(row['ok']);self.assertTrue(row['truncated'])
if __name__=='__main__':unittest.main()
