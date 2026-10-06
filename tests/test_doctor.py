import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

def probe(text="",code=0):
    # Journal fixtures include genuine event metadata, unlike sensor JSON.
    try:
        lines=[]
        for line in text.splitlines():
            item=json.loads(line)
            if isinstance(item,dict) and ('MESSAGE' in item or '_COMM' in item):
                item.setdefault('__REALTIME_TIMESTAMP',str(int((time.time()-60)*1000000)))
            lines.append(json.dumps(item))
        if lines:text='\n'.join(lines)
    except (ValueError,TypeError):pass
    return {"ok":code==0,"code":code,"stdout":text,"output":text,"command":"fake diagnostic"}

class Diagnostics(unittest.TestCase):
    def test_sensor_limits_are_not_current_temperature(self):
        data={"coretemp":{"Package":{"temp1_input":48,"temp1_max":85,"temp1_crit":100}}}
        p=doctor.Probes(lambda *a,**kw:probe(json.dumps(data)))
        row=p.temperature()
        self.assertEqual(row['state'],'ok')
        self.assertEqual(row['metrics']['temperature_c'],48)

    def test_invalid_temperature_values_ignored(self):
        self.assertEqual(doctor.sensor_inputs({'x':{'temp1_input':'N/A','temp2_input':float('nan'),'temp3_crit':100}}),[])

    def test_failed_services_are_unknown(self):
        p=doctor.Probes(lambda *a,**kw:probe('Failed to connect to bus',1))
        self.assertEqual(p.services()['state'],'unknown')

    def test_system_and_user_scopes_both_checked(self):
        calls=[]
        def run(args,**kw):
            calls.append(args)
            return probe('bad.service loaded failed failed Broken' if '--user' in args else '')
        row=doctor.Probes(run).services()
        self.assertEqual(row['state'],'bad')
        self.assertEqual(row['metrics']['failed_units'],1)
        self.assertEqual(len(calls),2)

    def test_journal_failure_is_unknown(self):
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe('',1)).journal()['state'],'unknown')

    def test_failed_package_query_is_unknown(self):
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe('',1)).packages(True)['state'],'unknown')

    def test_package_integrity_validates_summary(self):
        p=doctor.Probes(lambda *a,**kw:(probe('bash: 10 total files, 0 missing files\nlinux: 4 total files, 1 missing file\nwarning: linux: /fixture/absent (No such file or directory)',1) | {'ok':True}))
        self.assertEqual(p.packages(True)['state'],'warn')
        self.assertEqual(p.packages()['state'],'skipped')

    def test_failed_crash_query_is_unknown(self):
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe('Permission denied',1)).crashes()['state'],'unknown')

    def test_explicit_no_coredumps_state(self):
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe('')).crashes()['state'],'ok')

    def test_benign_qml_log_is_not_warning(self):
        entry={'_COMM':'quickshell','PRIORITY':'6','MESSAGE':'loaded Main.qml successfully'}
        p=doctor.Probes(lambda *a,**kw:probe(json.dumps(entry)))
        self.assertEqual(p.shell()['state'],'ok')

    def test_real_shell_warning_is_preserved(self):
        entry={'_COMM':'quickshell','PRIORITY':'4','MESSAGE':'QML binding failed'}
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe(json.dumps(entry))).shell()['state'],'warn')

    def test_nvidia_na_cannot_be_healthy(self):
        row=doctor.Probes(lambda *a,**kw:probe('RTX 4050, N/A, N/A, N/A, N/A, 580')).gpu()
        self.assertEqual(row['state'],'unknown')

    def test_all_nvidia_devices_checked(self):
        row=doctor.Probes(lambda *a,**kw:probe('GPU A, 42, 2, 10, 6000, 580\nGPU B, 94, 80, 5000, 6000, 580')).gpu()
        self.assertEqual(row['state'],'bad')
        self.assertEqual(row['metrics']['gpu_temperature_c'],94)

    def test_drives_named_and_all_inspected(self):
        calls=[]
        def run(args,**kw):
            calls.append(args)
            if args[0]=='lsblk':return probe(json.dumps({'blockdevices':[{'name':'/dev/sda','type':'disk'},{'name':'/dev/nvme0n1','type':'disk'}]}))
            return probe(json.dumps({'smart_status':{'passed':args[-1]=='/dev/sda'}}))
        row=doctor.Probes(run).drives()
        self.assertEqual(row['state'],'bad')
        self.assertIn('/dev/nvme0n1',row['summary'])
        self.assertEqual(len(calls),3)

    def test_smart_permission_error_is_unknown(self):
        def run(args,**kw):
            if args[0]=='lsblk':return probe(json.dumps({'blockdevices':[{'name':'/dev/sda','type':'disk'}]}))
            return probe('Permission denied',2)
        self.assertEqual(doctor.Probes(run).drives()['state'],'unknown')

    def test_smart_permission_error_requires_explicit_action_without_elevation(self):
        calls=[]
        def run(args,**kw):
            calls.append(args)
            if args[0]=='lsblk':return probe(json.dumps({'blockdevices':[{'name':'/dev/nvme0n1','type':'disk'}]}))
            return probe('Smartctl open device: /dev/nvme0n1 failed: Permission denied',2)
        row=doctor.Probes(run).drives()
        self.assertEqual(row['state'],'unknown')
        self.assertTrue(row['requires_smart_verification'])
        self.assertIn('Read SMART health',row['summary'])
        self.assertEqual(len(calls),2)
        self.assertFalse(any('sudo' in a[0] for a in calls))

    def test_ipv6_only_route_works(self):
        def run(args,**kw):
            if args[0]=='getent':return probe('2001:db8::1 example.com')
            return probe(json.dumps([{'dev':'eth0'}] if '-6' in args else []))
        self.assertEqual(doctor.Probes(run).network()['state'],'ok')

    def test_malformed_memory_is_unknown_not_abort(self):
        with patch.object(doctor,'read_values',return_value={'MemTotal':100}):
            self.assertEqual(doctor.Probes().memory()['state'],'unknown')

    def test_unknown_partial_and_skipped_never_all_clear(self):
        row=doctor.result('test','system','Test','unknown','No evidence')
        self.assertEqual(doctor.verdict([row])[0],'unknown')
        row['state']='ok'
        self.assertEqual(doctor.verdict([row],False)[0],'unknown')
        row['state']='skipped'
        self.assertEqual(doctor.verdict([row])[0],'unknown')

    def test_runner_timeout_is_bounded(self):
        start=time.monotonic()
        p=doctor.Runner()([sys.executable,'-c','import time;time.sleep(10)'],timeout=.1)
        self.assertEqual(p['code'],124)
        self.assertLess(time.monotonic()-start,2)

    def test_missing_command_is_unknown(self):
        p=doctor.Runner()(['doctor_nonexistent_test_binary'])
        self.assertEqual(p['code'],127)

    def test_stream_has_start_results_and_end_data(self):
        class Fake:
            def __getattr__(self,name):
                return lambda *args:doctor.result(name,'system',name,'ok','Fixture')
        out=io.StringIO()
        with contextlib.redirect_stdout(out):scan_id,rows,duration=doctor.run_scan(Fake())
        events=[json.loads(s) for s in out.getvalue().splitlines()]
        self.assertEqual(events[0]['type'],'scan_start')
        self.assertEqual(len(rows),len(doctor.CHECKS))
        self.assertEqual([e['completed'] for e in events[1:]],list(range(1,len(doctor.CHECKS)+1)))
        self.assertTrue(all('duration_ms' in r for r in rows))

class HistoryTests(unittest.TestCase):
    def test_skipped_check_is_not_a_resolved_or_new_finding(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            row=doctor.result('packages','system','Packages','warn','Missing files')
            h.save('deep','deep',[row])
            row['state']='skipped'
            self.assertEqual(h.save('quick','quick',[row]),[])
            self.assertEqual(row['change'],'not measured')
            row['state']='warn'
            self.assertEqual(h.save('deep-again','deep',[row]),[])
            self.assertEqual(row['change'],'measured')
            self.assertFalse(h.read()['scans'][0]['complete'])
            h.close()

    def test_history_persistence_changes_retention_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.sqlite3'
            h=doctor.History(path)
            row=doctor.result('cpu','cpu','CPU','warn','Busy',metrics={'cpu_pct':95})
            self.assertEqual(h.save('one','quick',[row]),[])
            row['state']='ok';row['metrics']['cpu_pct']=20
            changes=h.save('two','quick',[row])
            self.assertEqual(changes[0]['from'],'warn')
            self.assertEqual(changes[0]['to'],'ok')
            h.db.execute('INSERT INTO samples VALUES (?,?)',(time.time()-doctor.RETENTION-1,'{}'));h.db.commit()
            h.sample({'cpu_pct':22})
            self.assertEqual(h.db.execute('SELECT count(*) FROM samples WHERE ts < ?',(time.time()-doctor.RETENTION,)).fetchone()[0],0)
            self.assertEqual(os.stat(path).st_mode&0o777,0o600)
            h.close();h=doctor.History(path)
            data=h.read()
            self.assertEqual(len(data['scans']),2)
            self.assertEqual(data['scans'][0]['id'],'two')
            self.assertGreaterEqual(len(data['samples']),2)
            h.close()

    def test_fix_lifecycle_pending_still_failing_then_fixed(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            row=doctor.result('services','system','Services','bad','1 failed unit(s).')
            h.save('one','quick',[row])
            fix=h.open_fix(row,'grok')
            self.assertEqual(h.fixes()[0]['status'],'pending')
            h.save('two','quick',[row])
            self.assertEqual(h.fixes()[0]['status'],'pending')
            self.assertEqual(h.settle([row],'recheck')[0]['status'],'still_failing')
            self.assertEqual(h.fixes()[0]['attempts'],1)
            healthy=doctor.result('services','system','Services','ok','No failed units.')
            h.save('three','quick',[healthy])
            done=h.fixes()[0]
            self.assertEqual((done['id'],done['status'],done['before_state'],done['after_state']),(fix,'fixed','bad','ok'))
            self.assertIsNotNone(done['resolved'])
            self.assertEqual(h.read()['fixes'][0]['status'],'fixed')
            h.close()

    def test_new_fix_supersedes_open_attempt_and_skips_do_not_resolve(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            row=doctor.result('packages','system','Packages','warn','Missing files')
            first=h.open_fix(row,'');second=h.open_fix(row,'')
            states={f['id']:f['status'] for f in h.fixes()}
            self.assertEqual((states[first],states[second]),('superseded','pending'))
            row['state']='skipped'
            self.assertEqual(h.settle([row],'quick'),[])
            h.close()

    def test_fix_prompt_carries_evidence_and_recheck(self):
        row=doctor.result('services','system','Services','bad','1 failed unit(s).','btrfs-scrub@-.service failed','systemctl --failed')
        text=doctor.fix_prompt(row,'host','abc')
        for part in ('btrfs-scrub@-.service failed','systemctl --failed','recheck services','fix abc','Ask me before anything destructive'):
            self.assertIn(part,text)

    def test_event_queries_do_not_reset_at_hand_off(self):
        calls=[]
        def run(args,**kw):
            calls.append(args)
            return probe('')
        p=doctor.Probes(run,since={'crashes':1790985613,'journal':1790985613})
        self.assertEqual(p.crashes()['state'],'ok')
        self.assertEqual(p.journal()['state'],'ok')
        self.assertTrue(all('@1790985613' not in args for args in calls))

    def test_event_silence_does_not_mark_fix_fixed(self):
        with tempfile.TemporaryDirectory() as folder:
            h=doctor.History(Path(folder)/'history.sqlite3')
            for check in ('crashes','journal','shell','crashes:abc'):
                row=doctor.result(check,'system','Event','warn','Old evidence')
                fix=h.open_fix(row,'fixture')
                ok=doctor.result(check,'system','Event','ok','No new events')
                self.assertEqual(h.settle([ok],'recheck'),[])
                self.assertEqual(next(f for f in h.fixes() if f['id']==fix)['status'],'pending')
            h.close()

    def test_prompt_forbids_hiding_evidence(self):
        text=doctor.fix_prompt(doctor.result('crashes','system','Crashes','warn','2 core dumps'),'host','abc')
        self.assertIn('Fix the cause, never the measurement',text)
        self.assertIn('diagnose-crash',text)

    def test_known_hardware_notices_are_ignored_but_visible(self):
        lines='\n'.join(json.dumps(x) for x in [{"SYSLOG_IDENTIFIER":"kernel","MESSAGE":"virt/tdx: TDX not supported by the host platform"},{"SYSLOG_IDENTIFIER":"app","MESSAGE":"real failure"}])
        row=doctor.Probes(lambda *a,**kw:probe(lines)).journal()
        self.assertEqual((row['state'],row['metrics']['journal_entries'],row['metrics']['journal_ignored']),('warn',1,1))
        self.assertIn('[ignored:',row['evidence'])
        for m in ('profiles/audio/avdtp.c:avdtp_connect_cb() connect to 74:3F:8E:A5:5C:A1: Host is down (112)','ucsi_acpi USBC000:00: GET_CURRENT_CAM command failed'):
            self.assertEqual(doctor.Probes(lambda *a,**kw:probe(json.dumps({"MESSAGE":m}))).journal()['state'],'ok',m)
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe(json.dumps({"MESSAGE":"connect to 74:3F:8E:A5:5C:A1: Permission denied"}))).journal()['state'],'warn')
        only=json.dumps({"SYSLOG_IDENTIFIER":"kernel","MESSAGE":"virt/tdx: TDX not supported by the host platform"})
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe(only)).journal()['state'],'ok')

    def test_temperature_uses_hardware_limits(self):
        tree={"k10temp-pci-00c3":{"Tctl":{"temp1_input":88}},"nvme-pci-0500":{"Composite":{"temp1_input":82,"temp1_max":84.85,"temp1_crit":84.85}}}
        row=doctor.Probes(lambda *a,**kw:probe(json.dumps(tree))).temperature()
        self.assertEqual(row['state'],'warn')
        self.assertIn('nvme',row['summary'])
        tree["nvme-pci-0500"]["Composite"]["temp1_input"]=50
        self.assertEqual(doctor.Probes(lambda *a,**kw:probe(json.dumps(tree))).temperature()['state'],'ok')

if __name__=='__main__':unittest.main()
