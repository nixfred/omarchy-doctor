import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import doctor

class BackgroundTests(unittest.TestCase):
    def test_unverified_agent_or_trust_falls_back_visibly(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(doctor.launch_plan('other')[1],'interactive')
            self.assertEqual(doctor.launch_plan('codex',True)[1],'interactive')
            with patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,'--json --approve-for-me','')),patch.object(Path,'read_text',return_value='[projects]'):
                self.assertEqual(doctor.launch_plan('codex')[1],'interactive')
    def test_exact_trusted_scope_keeps_existing_policy(self):
        cwd=str(Path.cwd().resolve())
        config='[projects.'+json.dumps(cwd)+']\ntrust_level="trusted"\n'
        with patch.dict(os.environ,{},clear=True),patch.object(subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'--json --approve-for-me',''),subprocess.CompletedProcess([],0,cwd+'\n','')]),patch.object(Path,'read_text',return_value=config):
            command,mode,directory,_=doctor.launch_plan('codex')
        self.assertEqual(mode,'background');self.assertEqual(directory,cwd)
        self.assertIn('--approve-for-me',command)
        for unsafe in ('--dangerously-bypass-approvals-and-sandbox','--ignore-rules','--ignore-user-config','--dangerously-bypass-hook-trust','--ask-for-approval','--skip-git-repo-check'):
            self.assertNotIn(unsafe,command)
    def test_real_discovery_failure_keeps_repo_guard(self):
        cwd=str(Path.cwd().resolve())
        config='[projects.'+json.dumps(cwd)+']\ntrust_level="trusted"\n'
        with patch.dict(os.environ,{},clear=True),patch.object(Path,'read_text',return_value=config),patch.object(subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'--json --approve-for-me',''),subprocess.CompletedProcess([],128,'','Stopping at filesystem boundary')]) as run:
            command,mode,directory,note=doctor.launch_plan('codex')
        self.assertEqual(command,['omarchy-agent-prompt']);self.assertEqual(mode,'interactive');self.assertEqual(directory,cwd)
        self.assertIn('guard remains in force',note)
        self.assertEqual(run.call_args.args[0],['git','-C',cwd,'rev-parse','--show-toplevel'])
    def test_home_repository_does_not_expand_background_scope(self):
        cwd=str(Path.cwd().resolve());config='[projects.'+json.dumps(cwd)+']\ntrust_level="trusted"\n'
        with patch.dict(os.environ,{},clear=True),patch.object(Path,'read_text',return_value=config),patch.object(subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'--json --approve-for-me',''),subprocess.CompletedProcess([],0,str(Path.home())+'\n','')]):
            self.assertEqual(doctor.launch_plan('codex')[1],'interactive')
    def test_background_protocol_with_fake_codex_no_real_agent(self):
        with tempfile.TemporaryDirectory() as folder:
            w=Path(folder);db=w/'db';binpath=w/'bin';binpath.mkdir();config=w/'config';config.mkdir();subprocess.run(['git','init','-q',str(w)],check=True)
            (config/'config.toml').write_text('[projects.'+json.dumps(str(w))+']\ntrust_level="trusted"\n')
            executable=binpath/'codex'
            executable.write_text('#!'+sys.executable+'''\nimport sys,json,time
if '--help' in sys.argv:print('--json --approve-for-me');sys.exit()
assert '--approve-for-me' in sys.argv and '--json' in sys.argv
for e in [{'type':'thread.started','thread_id':'11111111-2222-3333-4444-555555555555'},{'type':'turn.started'},{'type':'item.completed','item':{'type':'agent_message','text':'Harmless fixture only'}},{'type':'turn.completed'}]:
 print(json.dumps(e),flush=True)
time.sleep(.1)
''');executable.chmod(0o755)
            h=doctor.History(db);row=doctor.result('services','system','Fixture','bad','Fixture','Fixture evidence','fixture inspect');h.save('fixture','quick',[row]);h.close()
            env={**os.environ,'PATH':str(binpath)+':'+os.environ['PATH'],'CODEX_HOME':str(config)};env.pop('DOCTOR_AGENT_COMMAND',None)
            p=subprocess.run([sys.executable,doctor.__file__,'fix','services','--agent','codex','--database',str(db)],cwd=w,env=env,capture_output=True,text=True,timeout=6)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            fix=json.loads(p.stdout)['id'];h=doctor.History(db)
            deadline=time.monotonic()+7
            while time.monotonic()<deadline:
                f=h.fixes()[0]
                if f['status']=='no_result':break
                time.sleep(.05)
            self.assertEqual(f['id'],fix);self.assertEqual(f['launch_mode'],'background');self.assertEqual(f['session_id'],'11111111-2222-3333-4444-555555555555')
            self.assertIn('turn completed',f['agent_update']);self.assertFalse(f['verified']);self.assertEqual(f['status'],'no_result');self.assertTrue(Path(f['log_path']).exists())
            self.assertEqual(h.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0);h.close()
    def test_untrusted_json_cannot_invent_session_or_activity(self):
        self.assertEqual(doctor.progress_event({'type':'thread.started','thread_id':'--evil'}),('', 'Agent session started'))
        self.assertEqual(doctor.progress_event({'type':'invented.percent','percent':100}),('',''))
