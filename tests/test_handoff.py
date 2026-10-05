"""Regression coverage for handoffs of warnings retained across skipped quick scans."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

class RetainedHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'history.sqlite3'
        self.h=doctor.History(self.path)
        self.warning=doctor.result('packages','system','Package integrity','warn',
            'Fixture package warning','Exact original fixture evidence','fixture inspect')
        self.warning['timestamp']=time.time()-300
        self.h.save('deep','deep',[self.warning])
        self.skipped=doctor.result('packages','system','Package integrity','skipped','Not checked')
    def tearDown(self):
        self.h.close();self.tmp.cleanup()
    def test_skipped_quick_scan_retains_warning_identity_time_and_evidence(self):
        self.h.save('quick','quick',[self.skipped])
        row=self.h.handoff_row('packages')
        self.assertEqual(row['state'],'warn')
        for key in ('id','finding_number','timestamp','evidence','command'):
            self.assertEqual(row[key],self.warning[key])
        self.assertIn('Not checked',row['coverage_note'])
        self.assertEqual(self.h.latest()[0]['state'],'skipped')
    def test_latest_healthy_or_unknown_measurement_blocks_older_warning(self):
        for state in ('ok','unknown'):
            with self.subTest(state=state):
                self.h.save('measured-'+state,'deep',[
                    doctor.result('packages','system','Package integrity',state,'New measurement')])
                self.h.save('skipped-'+state,'quick',[self.skipped])
                self.assertEqual(self.h.handoff_row('packages')['state'],'unknown' if state=='unknown' else 'skipped')
    def test_fallback_matches_the_panel_history_window(self):
        for i in range(40):self.h.save('quick-'+str(i),'quick',[self.skipped])
        self.assertEqual(self.h.handoff_row('packages')['state'],'skipped')
    def test_cli_handoff_uses_retained_warning_instead_of_rejecting_skip(self):
        self.h.save('quick','quick',[self.skipped])
        p=subprocess.run([sys.executable,doctor.__file__,'fix','packages','--no-launch',
            '--agent','fixture','--database',str(self.path)],capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        result=json.loads(p.stdout)
        self.assertEqual(result['type'],'fix_start')
        self.assertFalse(result['launched'])
        self.assertIn('Coverage:  Not checked',result['prompt'])
        self.assertIn(self.warning['evidence'],result['prompt'])
        before=json.loads(self.h.db.execute('SELECT before FROM fixes WHERE id=?',(result['id'],)).fetchone()[0])
        self.assertEqual(before['timestamp'],self.warning['timestamp'])
        self.assertEqual(before['finding_number'],self.warning['finding_number'])
        self.assertEqual(self.h.latest()[0]['state'],'skipped')
    def test_skip_without_previous_warning_creates_no_handoff(self):
        self.h.save('healthy','deep',[
            doctor.result('packages','system','Package integrity','ok','Healthy fixture')])
        self.h.save('quick','quick',[self.skipped])
        p=subprocess.run([sys.executable,doctor.__file__,'fix','packages','--no-launch',
            '--agent','fixture','--database',str(self.path)],capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,3)
        self.assertEqual(json.loads(p.stdout)['type'],'error')
        self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM fixes').fetchone()[0],0)
