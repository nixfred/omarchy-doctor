"""Package summaries describe lstat failures; errno evidence establishes absence."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

def response(stdout='',stderr='',code=0,**extra):
    return dict(ok=code in (0,1),code=code,stdout=stdout,stderr=stderr,
        output=stdout+'\n'+stderr if stderr else stdout,command='pacman -Qk',**extra)

def check(stdout,stderr='',code=0,orphans=None,**extra):
    calls=[]
    def run(args,**kw):
        calls.append(args)
        return orphans or response(code=1) if '-Qtdq' in args else response(stdout,stderr,code,**extra)
    row=doctor.Probes(run).packages(True)
    assert calls==[['pacman','-Qtdq'],['pacman','-Qk']],calls
    return row

class PackageCoverageTests(unittest.TestCase):
    def test_permission_denied_is_unknown_not_missing(self):
        row=check('example: 10 total files, 1 missing file',
            'warning: example: /protected/example (Permission denied)',1)
        self.assertEqual(row['state'],'unknown')
        self.assertEqual(row['metrics']['missing_files'],0)
        self.assertEqual(row['metrics']['reported_missing_files'],1)
        self.assertEqual(row['metrics']['permission_denied_paths'],1)
        self.assertIn('Permission denied',row['evidence'])
        self.assertIn('not fully verified',row['coverage_note'])
    def test_mixed_real_missing_and_denied_paths(self):
        row=check('example: 10 total files, 2 missing files',
            'warning: example: /absent (No such file or directory)\nwarning: example: /protected (Permission denied)',1)
        self.assertEqual(row['state'],'warn')
        self.assertEqual(row['metrics']['missing_files'],1)
        self.assertEqual(row['metrics']['unreadable_paths'],1)
        self.assertFalse(row['metrics']['integrity_complete'])
    def test_singular_confirmed_missing_is_counted(self):
        row=check('example: 10 total files, 1 missing file',
            'warning: example: /absent (No such file or directory)',1)
        self.assertEqual((row['state'],row['metrics']['missing_files']),('warn',1))
    def test_other_lstat_errors_are_unavailable(self):
        for reason in ('Operation not permitted','Input/output error','Too many levels of symbolic links'):
            with self.subTest(reason=reason):
                row=check('example: 10 total files, 1 missing file',f'warning: example: /path ({reason})',1)
                self.assertEqual((row['state'],row['metrics']['missing_files']),('unknown',0))
    def test_summary_without_per_path_errors_cannot_prove_missing(self):
        row=check('example: 10 total files, 2 missing files',code=1)
        self.assertEqual((row['state'],row['metrics']['missing_files']),('unknown',0))
        self.assertEqual(row['metrics']['unclassified_missing_files'],2)
    def test_complete_current_collector_measurement_is_healthy(self):
        began=time.time()
        row=check('one: 10 total files, 0 missing files\ntwo: 4 total files, 0 missing files')
        self.assertEqual(row['state'],'ok')
        self.assertEqual(row['metrics']['packages_checked'],2)
        self.assertTrue(row['metrics']['integrity_complete'])
        self.assertGreaterEqual(row['timestamp'],began)
    def test_nonzero_exit_error_and_truncation_are_not_healthy(self):
        for stderr,code,extra in [('',1,{}),('error: cannot open database',1,{}),('',0,{'stderr_truncated':True})]:
            with self.subTest(stderr=stderr,code=code,extra=extra):
                self.assertEqual(check('one: 10 total files, 0 missing files',stderr,code,**extra)['state'],'unknown')
    def test_failed_tool_and_malformed_or_duplicate_summaries(self):
        p=response('broken',code=2);p['ok']=False
        self.assertEqual(doctor.Probes(lambda *a,**kw:p).packages(True)['state'],'unknown')
        self.assertEqual(check('unparseable output')['state'],'unknown')
        self.assertEqual(check('one: 10 total files, 0 missing files\none: 10 total files, 0 missing files')['state'],'unknown')
    def test_incomplete_orphan_query_cannot_establish_all_healthy(self):
        orphans=response('', 'error: database locked',1)
        self.assertEqual(check('one: 10 total files, 0 missing files',orphans=orphans)['state'],'unknown')
    def test_warning_package_counts_must_match_summaries(self):
        row=check('one: 10 total files, 0 missing files',
            'warning: other: /protected (Permission denied)')
        self.assertEqual(row['state'],'unknown')
    def test_runner_retains_stderr_for_errno_classification(self):
        p=doctor.Runner()([sys.executable,'-c','import sys;print("summary");print("diagnostic",file=sys.stderr)'])
        self.assertEqual(p['stdout'],'summary')
        self.assertEqual(p['stderr'],'diagnostic')
        self.assertFalse(p['stderr_truncated'])

class PackageHistoryTests(unittest.TestCase):
    def test_fresh_or_old_privileged_agent_claims_do_not_override_unknown(self):
        for age in (0,86400):
            with self.subTest(age=age),tempfile.TemporaryDirectory() as folder:
                h=doctor.History(Path(folder)/'db')
                old=doctor.result('packages','system','Package integrity','warn','Legacy summary count','Old warning')
                h.save('old','deep',[old]);fix=h.open_fix(old,'fixture')
                h.record_report(fix,{'outcome':'completed','summary':'Privileged check found no missing files',
                    'validation':f'Claimed sudo check at {time.time()-age}', 'needs_fix':False})
                h.db.execute("UPDATE fixes SET status='still_failing' WHERE id=?",(fix,));h.db.commit()
                unknown=check('example: 10 total files, 1 missing file',
                    'warning: example: /protected (Permission denied)',1)
                with patch.object(doctor.Probes,'packages',return_value=unknown):h.verify_report(fix)
                self.assertEqual(h.latest()[0]['state'],'unknown')
                self.assertFalse(h.latest()[0]['needs_fix'])
                record=h.fixes()[0]
                self.assertFalse(record['verified'])
                self.assertEqual(record['status'],'reviewed_unproven')
                self.assertEqual(record['verifications'][0]['outcome'],'unproven')
                self.assertEqual(h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1)
                self.assertEqual(record['before_evidence'],'Old warning')
                h.save('quick','quick',[doctor.result('packages','system','Package integrity','skipped','Skipped')])
                retained=h.handoff_row('packages')
                self.assertEqual(retained['state'],'unknown')
                self.assertFalse(retained['needs_fix'])
                h.close()
    def test_only_new_measured_full_coverage_can_verify_healthy(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'db')
            unknown=check('example: 10 total files, 1 missing file',
                'warning: example: /protected (Permission denied)',1)
            h.save('unknown','deep',[unknown]);fix=h.open_fix(unknown,'fixture')
            h.record_report(fix,{'outcome':'completed','summary':'Prior privileged check claims healthy'})
            healthy=check('example: 10 total files, 0 missing files')
            with patch.object(doctor.Probes,'packages',return_value=healthy):h.verify_report(fix)
            record=h.fixes()[0]
            self.assertTrue(record['verified'])
            self.assertEqual(record['status'],'fixed')
            self.assertEqual(record['verifications'][0]['outcome'],'healthy')
            self.assertEqual(h.latest()[0]['timestamp'],healthy['timestamp'])
            h.close()
