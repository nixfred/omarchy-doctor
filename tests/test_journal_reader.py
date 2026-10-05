"""Journal decoder and stable history fixtures; no live journal or repair."""
import json,sys,time,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

def entry(message,cursor='fixture',ts=None):
 return {'_COMM':'quickshell','SYSLOG_IDENTIFIER':'quickshell','PRIORITY':'6','MESSAGE':message,'__CURSOR':cursor,'__REALTIME_TIMESTAMP':str(int((ts if ts is not None else time.time()-5)*1e6))}
def probe(rows):
 text='\n'.join(json.dumps(r) for r in rows)
 return {'ok':True,'code':0,'stdout':text,'output':text,'command':'fixture journal query'}
class JournalReader(unittest.TestCase):
 def test_actual_audio_warning_octets_and_ansi_are_decoded(self):
  text='\x1b[33m WARN\x1b[0m scene: file:///home/example/.config/omarchy/plugins/pi.audio/Panel.qml[1380:-1]: TypeError: Cannot read property \'foreground\' of null'
  r=doctor.Probes(lambda *a,**k:probe([entry(list(text.encode()))])).shell()
  self.assertEqual(len(r['findings']),1);f=r['findings'][0]
  self.assertIn('pi.audio',f['evidence']);self.assertIn('TypeError',f['evidence']);self.assertNotIn('\x1b',f['evidence']);self.assertEqual(f['evidence_kind'],'log_warning');self.assertEqual(f['log_level'],'error')
 def test_unicode_arrays_and_multivalue_strings(self):
  for value in ['WARN café ☃',list('WARN café ☃'.encode()),'WARN café ☃'.encode(),bytearray('WARN café ☃'.encode()),['WARN café','☃']]:
   text,valid,lossy=doctor.journal_message(value);self.assertTrue(valid);self.assertFalse(lossy);self.assertIn('café',text);self.assertIn('☃',text)
 def test_invalid_types_never_invent_or_hide_healthy_coverage(self):
  for value in [None,17,True,{},[300],[-1],[True],[3.5],['WARN',1],[[65]]]:
   self.assertEqual(doctor.journal_message(value),('',False,False))
   r=doctor.Probes(lambda *a,**k:probe([entry(value)])).shell();self.assertEqual(r['state'],'unknown');self.assertTrue(r['coverage_incomplete']);self.assertEqual(r['coverage']['invalid_messages'],1)
 def test_invalid_unicode_is_retained_with_honest_incompleteness(self):
  for value in [list(b'WARN \xff bad'), 'WARN \ud800 bad']:
   r=doctor.Probes(lambda *a,**k:probe([entry(value)])).shell();self.assertEqual(r['state'],'unknown');self.assertEqual(len(r['findings']),1);self.assertEqual(r['coverage']['lossy_messages'],1)
 def test_bad_record_keeps_valid_warning_evidence(self):
  r=doctor.Probes(lambda *a,**k:probe([entry(None,'bad'),entry('WARN binding loop','good')])).shell();self.assertEqual(len(r['findings']),1);self.assertEqual(r['state'],'unknown')
 def test_info_is_quiet_but_raw_cap_is_not_proof_of_health(self):
  rows=[entry('DEBUG normal progress',str(i)) for i in range(500)]
  r=doctor.Probes(lambda *a,**k:probe(rows)).shell();self.assertEqual(r['state'],'unknown');self.assertEqual(r['metrics']['shell_warnings'],0);self.assertEqual(r['coverage']['raw_entries'],500)
 def test_shell_and_boot_share_normalized_signatures(self):
  a=entry('WARN binding loop','same');b=entry(list(b'\x1b[33mWARN\x1b[0m binding loop'),'same')
  r=doctor.Probes(lambda *a,**k:probe([a,b])).shell();self.assertEqual(len(r['findings']),1);self.assertEqual(r['findings'][0]['event_count'],1)
  r=doctor.Probes(lambda *a,**k:probe([b])).journal();self.assertIn('binding loop',r['findings'][0]['evidence'])
 def test_empty_valid_and_control_osc_sequences(self):
  self.assertEqual(doctor.journal_message([]),('',True,False))
  text,valid,lossy=doctor.journal_message('\x1b]8;;https://example.invalid\x07WARN café\x1b]8;;\x07\r\nline\x00');self.assertEqual(text,'WARN café\nline');self.assertTrue(valid)
 def test_qa_context_changes_label_without_changing_signature_id(self):
  for cmd in ['qs --path /tmp/mycelium-page-test-abcd/shell.qml','qs --path /tmp/doctor-fit-abcd/shell.qml','Hyprland --help']:
   exe='/usr/bin/Hyprland' if cmd.startswith('Hyprland') else '/usr/bin/quickshell'
   e={'COREDUMP_EXE':exe,'COREDUMP_SIGNAL':'6','COREDUMP_CMDLINE':cmd,'COREDUMP_USER_UNIT':'app-org.chromium.scope','__CURSOR':'qa','__REALTIME_TIMESTAMP':str(int(time.time()*1e6))}
   r=doctor.event_row('crashes','Crashes',[e],'fixture');f=r['findings'][0]
   import hashlib
   expected='crashes:'+hashlib.sha256((exe+'|signal=6|desktop session').encode()).hexdigest()[:20]
   self.assertEqual(f['id'],expected);self.assertEqual(f['contexts'],['test session']);self.assertEqual(f['evidence_kind'],'test_event')
 def test_real_shell_and_unknown_invocation_not_blanket_suppressed(self):
  self.assertEqual(doctor.crash_context('/usr/bin/quickshell','quickshell -n -p /home/example/real/shell','wayland-wm@hyprland.desktop.service'),'desktop session')
  self.assertEqual(doctor.crash_context('/usr/bin/quickshell','/usr/bin/quickshell','app-org.chromium.scope'),'unclassified instance')
 def test_recurrence_warning_not_repair_and_assessment_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   h=doctor.History(Path(folder)/'db');r=doctor.Probes(lambda *a,**k:probe([entry('WARN binding loop','old',time.time()-60)])).shell();h.save('first','quick',[r]);fid=r['findings'][0]['id']
   r=doctor.Probes(lambda *a,**k:probe([entry(list(b'WARN binding loop'),'new',time.time()+1)])).shell();h.save('second','quick',[r]);f=r['findings'][0]
   self.assertEqual(f['id'],fid);self.assertEqual(f['activity'],'recurring');self.assertFalse(f['needs_fix']);self.assertEqual(f['disposition'],'monitor');self.assertEqual(f['event_count'],2)
   h.assess(fid,'needs_fix','Confirmed ongoing functional break in fixture');h.annotate([r]);self.assertTrue(f['needs_fix'])
   h.assess(fid,'monitor','Fixture has recovered; no repair established');h.annotate([r]);self.assertFalse(f['needs_fix']);self.assertEqual(f['event_count'],2);h.close()
 def test_normalization_reuses_old_cursor_identity_and_receipt(self):
  with tempfile.TemporaryDirectory() as folder:
   h=doctor.History(Path(folder)/'db');old=doctor.event_row('shell','Shell',[entry('WARN binding loop','cursor')],'fixture');f=old['findings'][0];f['id']='shell:old-ansi-id';f['signature']='quickshell|old ANSI signature';h.save('old','quick',[old]);number=f['finding_number']
   new=doctor.event_row('shell','Shell',[entry(list(b'\x1b[33mWARN\x1b[0m binding loop'),'cursor')],'fixture');h.save('new','quick',[new]);f=new['findings'][0]
   self.assertEqual(f['id'],'shell:old-ansi-id');self.assertEqual(f['finding_number'],number);self.assertEqual(f['event_count'],1);self.assertEqual(f['new_count'],0);self.assertEqual(h.db.execute('SELECT COUNT(*) FROM event_observations').fetchone()[0],1);h.close()

 def test_missing_time_retains_warning_text_and_valid_other_event(self):
  bad=entry('WARN untimed fixture','bad');bad.pop('__REALTIME_TIMESTAMP')
  r=doctor.Probes(lambda *a,**k:probe([bad,entry('WARN timed fixture','good')])).shell()
  self.assertEqual(r['state'],'unknown');self.assertIn('untimed fixture',r['evidence']);self.assertEqual(len(r['findings']),1);self.assertEqual(r['coverage']['untimed_events'],1)
 def test_normalization_merges_prior_aliases_without_erasing_ids_or_receipt(self):
  with tempfile.TemporaryDirectory() as folder:
   h=doctor.History(Path(folder)/'db')
   old=doctor.event_row('shell','Shell',[entry('WARN fixture','one')],'fixture');one=old['findings'][0];one['id']='shell:old-one';one['signature']='old colored one'
   two=doctor.event_row('shell','Shell',[entry('WARN fixture','two')],'fixture')['findings'][0];two['id']='shell:old-two';two['signature']='old colored two';old['findings'].append(two);h.save('old','quick',[old])
   fix=h.open_fix(two,'fixture');h.record_report(fix,{'outcome':'completed','summary':'Historical fixture claim'});receipt=h.db.execute('SELECT receipt_id,payload FROM receipts').fetchall();identities=h.db.execute('SELECT number,kind,key FROM identities').fetchall()
   new=doctor.event_row('shell','Shell',[entry('WARN fixture','one'),entry(list(b'WARN fixture'),'two')],'fixture');h.save('new','quick',[new]);f=new['findings'][0]
   self.assertEqual(f['id'],'shell:old-one');self.assertEqual(f['related_prior_ids'],['shell:old-two']);self.assertEqual(f['event_count'],2);self.assertEqual(f['new_count'],0)
   self.assertEqual(h.db.execute('SELECT receipt_id,payload FROM receipts').fetchall(),receipt);self.assertTrue(all(i in h.db.execute('SELECT number,kind,key FROM identities').fetchall() for i in identities));self.assertEqual(h.db.execute('SELECT COUNT(*) FROM event_observations').fetchone()[0],2);h.close()
