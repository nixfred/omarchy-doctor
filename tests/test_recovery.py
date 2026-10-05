import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.h=doctor.History(Path(self.tmp.name)/'db')
    def tearDown(self):self.h.close();self.tmp.cleanup()
    def row(self,state,ready=None):
        r=doctor.result('temperature','cpu','Thermal sensors',state,'Measured '+state,'Exact fixture thermal output','fixture inspect',{'thermal_raw_state':state})
        if ready is not None:r['metrics']['thermal_recovery_ready']=ready
        return r
    def test_margin_prevents_flapping_but_critical_is_immediate(self):
        r=self.row('warn');self.h.save('hot','quick',[r]);number=r['finding_number']
        r=self.row('ok',False);self.h.save('near','quick',[r]);self.assertEqual(r['state'],'warn');self.assertIn('Cooling',r['summary'])
        r=self.row('bad',False);self.h.save('critical','quick',[r]);self.assertEqual(r['state'],'bad')
        r=self.row('ok',True);self.h.save('cool','quick',[r]);self.assertEqual(r['state'],'ok');self.assertEqual(r['finding_number'],number)
        self.assertEqual(r['change'],'recovered without handoff');self.assertEqual(r['recovery']['kind'],'without_handoff')
        self.assertEqual(r['recovery']['previous_state'],'bad');self.assertTrue(r['recovery']['evidence'])
        self.assertFalse(r['needs_fix']);self.assertEqual(self.h.db.execute('SELECT COUNT(*) FROM fixes').fetchone()[0],0)
        r=self.row('warn');self.h.save('again','quick',[r]);self.assertTrue(r['needs_fix']);self.assertEqual(r['finding_number'],number)
    def test_unknown_and_skipped_never_establish_recovery(self):
        self.h.save('hot','quick',[self.row('warn')])
        for state in ['unknown','skipped']:
            r=self.row(state);self.h.save(state,'quick',[r]);self.assertNotIn('recovery',r)
        r=self.row('ok',False);self.h.save('near','quick',[r]);self.assertEqual(r['state'],'warn')
        r=self.row('unknown');self.h.save('gap','quick',[r])
        r=self.row('ok',True);self.h.save('measured','quick',[r]);self.assertEqual(r['recovery']['kind'],'without_handoff');self.assertEqual(r['recovery']['previous_state'],'warn')
    def test_recovery_after_handoff_does_not_claim_spontaneous_or_agent_cause(self):
        r=self.row('warn');self.h.save('hot','quick',[r]);self.h.open_fix(r,'fixture')
        r=self.row('ok',True);self.h.save('cool','quick',[r]);self.assertEqual(r['change'],'measured recovery');self.assertEqual(r['recovery']['kind'],'measured_recovery')
