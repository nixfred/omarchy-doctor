import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import doctor

def event(cursor, ts, message="ACPI Error: region 0x12345 unavailable", **extra):
    return {"__CURSOR":cursor, "__REALTIME_TIMESTAMP":str(int(ts*1000000)),
        "SYSLOG_IDENTIFIER":"kernel", "MESSAGE":message, **extra}

def crash(cursor, ts, exe="/usr/bin/quickshell", sig="11", unit="wayland-wm@hyprland.desktop.service"):
    return event(cursor, ts, COREDUMP_EXE=exe, COREDUMP_SIGNAL=sig, COREDUMP_PID="42",
        COREDUMP_USER_UNIT=unit, COREDUMP_CMDLINE=exe)

class EventTests(unittest.TestCase):
    def make_row(self, entries, key="journal"):
        return doctor.event_row(key, "Events", entries, "inspect")

    def test_unrelated_processes_signals_and_contexts_stay_separate(self):
        t=time.time()-30
        row=self.make_row([crash('a',t),crash('b',t,exe='/usr/bin/Hyprland'),
            crash('c',t,sig='6'),crash('d',t,unit='no-mistakes-daemon-abc.service')], 'crashes')
        self.assertEqual(len(row['findings']),4)
        self.assertEqual(len({f['id'] for f in row['findings']}),4)
        self.assertTrue(any('test session' in f['title'] for f in row['findings']))

    def test_journal_signature_normalizes_only_volatile_addresses(self):
        t=time.time()-30
        row=self.make_row([event('a',t),event('b',t,'ACPI Error: region 0xabcde unavailable'),
            event('c',t,'CIFS: Inode number collision'),event('d',t,'ACPI Error: other method failed')])
        self.assertEqual(len(row['findings']),3)
        self.assertEqual(sorted(f['event_count'] for f in row['findings']),[1,1,2])

    def test_duplicate_cursors_and_missing_timestamps(self):
        e=event('a',time.time()-30)
        self.assertEqual(self.make_row([e,e])['findings'][0]['event_count'],1)
        del e['__REALTIME_TIMESTAMP']
        self.assertEqual(self.make_row([e])['state'],'unknown')

    def test_same_journal_event_can_be_observed_by_two_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            entry=event('same-cursor',time.time()-10)
            rows=[self.make_row([entry],'journal'),self.make_row([entry],'shell')]
            h.save('a','quick',rows)
            self.assertEqual([r['findings'][0]['event_count'] for r in rows],[1,1])
            h.close()

    def test_historical_rescans_do_not_recur_and_new_events_do(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            t=time.time()-100
            old=event('old',t)
            row=self.make_row([old]);h.save('one','quick',[row]);f=row['findings'][0]
            stable=f['id']
            self.assertEqual((f['activity'],f['new_count'],f['event_count']),('historical',0,1))
            row=self.make_row([old]);h.save('two','quick',[row]);f=row['findings'][0]
            self.assertEqual((f['activity'],f['new_count'],f['event_count']),('historical',0,1))
            new=event('new',time.time()+1,'ACPI Error: region 0x6789 unavailable')
            unrelated=event('other',time.time()+1,'CIFS: Inode number collision')
            row=self.make_row([old,new,unrelated]);h.save('three','quick',[row])
            f=next(f for f in row['findings'] if f['id']==stable)
            other=next(f for f in row['findings'] if f['id']!=stable)
            self.assertEqual((f['activity'],f['new_count'],f['event_count']),('recurring',1,2))
            self.assertEqual(other['activity'],'new')
            self.assertAlmostEqual(f['first_seen'],t,places=5)
            self.assertAlmostEqual(f['last_seen'],new['__REALTIME_TIMESTAMP'] and int(new['__REALTIME_TIMESTAMP'])/1e6)
            # The same records remain historical after restart, with the stable identity.
            h.close();h=doctor.History(Path(folder)/'history.sqlite3')
            row=self.make_row([old,new,unrelated]);h.save('four','quick',[row])
            self.assertTrue(all(f['activity']=='historical' and f['new_count']==0 for f in row['findings']))
            self.assertEqual(next(f for f in row['findings'] if f['id']==stable)['event_count'],2)
            h.close()

    def test_late_old_events_are_historical_not_recurring(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            t=time.time()-100
            row=self.make_row([event('a',t)]);h.save('a','quick',[row])
            row=self.make_row([event('a',t),event('b',t+1)]);h.save('b','quick',[row])
            self.assertEqual((row['findings'][0]['activity'],row['findings'][0]['event_count']),('historical',2))
            h.close()

    def test_coverage_limit_is_unknown_when_nothing_actionable_is_visible(self):
        self.assertEqual(doctor.event_row('journal','Journal',[],'inspect',limited=True)['state'],'unknown')

    def test_event_absence_never_settles_a_specific_fix(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            row=self.make_row([event('a',time.time()-10)])
            h.save('a','quick',[row]);finding=row['findings'][0]
            fix=h.open_fix(finding,'fixture')
            healthy=doctor.result(finding['id'],'system','Event','ok','No new event')
            self.assertEqual(h.settle([healthy],'recheck'),[])
            self.assertEqual(h.fixes()[0]['status'],'pending')
            h.close()

    def test_package_recheck_runs_integrity_and_cannot_refresh_other_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.sqlite3';h=doctor.History(path)
            rows=[doctor.result(k,'system',t,'ok','Fixture') for k,t in doctor.CHECKS]
            for row in rows:row['timestamp']=time.time()-7200
            h.save('old','deep',rows);h.close()
            modes=[]
            def packages(deep=False):
                modes.append(deep)
                return doctor.result('packages','system','Packages','ok','Zero missing files')
            with patch.object(sys,'argv',['doctor.py','recheck','packages','--database',str(path)]),patch.object(doctor.Probes,'packages',side_effect=packages),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(doctor.main(),0)
            h=doctor.History(path)
            self.assertEqual(modes,[True])
            self.assertGreater(time.time()-h.read()['scans'][0]['coverage_timestamp'],7100)
            h.close()

if __name__=='__main__':unittest.main()
