import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'history.sqlite3'
        self.h=doctor.History(self.path)
        self.row=doctor.result('services','system','Fixture services','bad','Fixture failed unit','Fixture exact evidence','fixture inspect')
        self.h.save('fixture','quick',[self.row])
    def tearDown(self):self.h.close();self.tmp.cleanup()
    def test_saved_repo_guard_failure_is_exact_and_never_retried(self):
        (self.path.parent/'handoffs').mkdir(exist_ok=True);fix,_=self.h.claim_fix(self.row,'codex');self.h.launch_state(fix,'launch_failed',None,1)
        self.h.db.execute('INSERT INTO handoff_progress VALUES (?,?,?,?,?,?)',(fix,'background','/fixture/Work','',time.time(),'Fixture'))
        self.h.db.commit();log=self.path.parent/'handoffs'/(fix+'-launch.log');log.write_text('Not inside a trusted directory and --skip-git-repo-check was not specified.\n')
        with patch.object(doctor.Probes,'services',side_effect=AssertionError('No diagnostic or retry permitted')):
            f=self.h.fixes()[0]
        self.assertEqual(f['id'],fix);self.assertEqual(f['status'],'launch_failed');self.assertFalse(f['verified'])
        self.assertIn('/fixture/Work',f['launch_error']);self.assertIn('No agent session started',f['launch_error']);self.assertIn('will not bypass',f['launch_error'])
        self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
    def test_unknown_launch_failure_does_not_expose_arbitrary_log(self):
        (self.path.parent/'handoffs').mkdir(exist_ok=True);fix,_=self.h.claim_fix(self.row,'fixture');self.h.launch_state(fix,'launch_failed',None,17)
        (self.path.parent/'handoffs'/(fix+'-launch.log')).write_text('arbitrary confidential fixture output')
        f=self.h.fixes()[0];self.assertIn('code 17',f['launch_error']);self.assertNotIn('confidential',f['launch_error'])
    def test_live_handoff_reused_even_after_failed_recheck(self):
        first,_=self.h.claim_fix(self.row,'fixture')
        self.h.launch_state(first,'running',os.getpid())
        self.h.settle([self.row],'recheck')
        second,reused=self.h.claim_fix(self.row,'different-choice')
        self.assertTrue(reused);self.assertEqual(first,second)
        f=self.h.fixes()[0]
        self.assertTrue(f['supervisor_alive']);self.assertEqual(f['agent'],'fixture')
        self.assertGreater(f['observed_at'],f['started'])
        self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM fixes').fetchone()[0],1)
    def test_stale_pid_token_is_not_activity(self):
        old,_=self.h.claim_fix(self.row,'fixture');self.h.launch_state(old,'running',os.getpid())
        self.h.db.execute("UPDATE handoffs SET token='wrong-start-time' WHERE fix_id=?",(old,));self.h.db.commit()
        self.assertFalse(self.h.fixes()[0]['supervisor_alive'])
        self.assertEqual(self.h.fixes()[0]['status'],'no_result')
        new,reused=self.h.claim_fix(self.row,'fixture');self.assertFalse(reused);self.assertNotEqual(old,new)
    def test_preparing_reservation_expires_without_fabricating_running(self):
        old,_=self.h.claim_fix(self.row,'fixture')
        self.assertEqual(self.h.claim_fix(self.row,'fixture'),(old,True))
        self.h.db.execute('UPDATE fixes SET started=? WHERE id=?',(time.time()-31,old));self.h.db.commit()
        new,reused=self.h.claim_fix(self.row,'fixture');self.assertFalse(reused);self.assertNotEqual(old,new)
    def test_simultaneous_claims_create_only_one_attempt(self):
        barrier=threading.Barrier(2)
        def claim():
            h=doctor.History(self.path);barrier.wait()
            try:return h.claim_fix(self.row,'fixture')
            finally:h.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(lambda _:claim(),range(2)))
        self.assertEqual(out[0][0],out[1][0]);self.assertEqual(sorted(x[1] for x in out),[False,True])
        self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM fixes').fetchone()[0],1)
    def test_cli_repeated_request_does_not_invoke_launcher(self):
        fix,_=self.h.claim_fix(self.row,'fixture');self.h.launch_state(fix,'running',os.getpid())
        p=subprocess.run([sys.executable,doctor.__file__,'fix','services','--agent','different-agent','--database',str(self.path)],env={**os.environ,'DOCTOR_AGENT_COMMAND':'/does/not/exist'},capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        e=json.loads(p.stdout);self.assertTrue(e['reused']);self.assertEqual(e['id'],fix);self.assertEqual(e['agent'],'fixture')
    def test_receipt_after_earlier_check_gets_fresh_independent_verification(self):
        fix,_=self.h.claim_fix(self.row,'fixture');self.h.settle([self.row],'recheck')
        self.h.record_report(fix,{'outcome':'completed','summary':'Fixture claim'})
        unknown=doctor.result('services','system','Fixture services','unknown','Evidence unavailable')
        with patch.object(doctor.Probes,'services',return_value=unknown):self.h.reconcile()
        f=self.h.fixes()[0]
        self.assertFalse(f['verified']);self.assertEqual(f['after_state'],'unknown')
        self.assertTrue(any(v['timestamp']>=f['report_received_at'] for v in f['verifications']))
        self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1)
    def test_saved_progress_survives_restart_without_new_attempt(self):
        fix,_=self.h.claim_fix(self.row,'fixture');self.h.launch_state(fix,'running',os.getpid())
        self.h.close();self.h=doctor.History(self.path)
        self.assertEqual(self.h.fixes()[0]['id'],fix);self.assertTrue(self.h.fixes()[0]['supervisor_alive'])
        self.assertEqual(self.h.claim_fix(self.row,'fixture'),(fix,True))
