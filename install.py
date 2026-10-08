#!/usr/bin/env python3
"""Install the native Doctor plugin without resetting shell settings or order."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent
RUNTIME=['Doctor.qml','StatusPane.qml','AboutPane.qml','DoctorAction.qml','MedicalCross.qml',
         'doctor.py','manifest.json','README.md','LICENSE']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,default=Path.home()/'.config/omarchy/plugins/nixfred.doctor')
    parser.add_argument('--enable',action='store_true',help='Enable beside Pulse using the public Omarchy API')
    args=parser.parse_args()
    dest=args.destination.expanduser().absolute()
    if dest==ROOT or dest.is_symlink():
        parser.error('Use a separate installation directory, not the source or a symlink.')
    if dest.exists() and any(dest.iterdir()):
        try:
            existing=json.loads((dest/'manifest.json').read_text())
        except (OSError,ValueError):
            parser.error('Refusing to replace a nonempty directory that is not an existing Doctor installation.')
        if existing.get('id')!='nixfred.doctor':
            parser.error('Destination belongs to a different plugin; it will not be replaced.')
    if not shutil.which('python3') or not shutil.which('omarchy'):
        parser.error('Python 3 and the Omarchy plugin CLI are required.')
    subprocess.run(['omarchy','plugin','validate',str(ROOT)],check=True)
    dest.parent.mkdir(parents=True,exist_ok=True)
    state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'omarchy-doctor'
    backup=state/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True,mode=0o700)
    config=Path.home()/'.config/omarchy/shell.json'
    if config.exists():shutil.copy2(config,backup/'shell.json')
    if dest.exists():shutil.copytree(dest,backup/'plugin')
    stage=Path(tempfile.mkdtemp(prefix='.doctor-install-',dir=dest.parent))
    try:
        for name in RUNTIME:shutil.copy2(ROOT/name,stage/name)
        (stage/'doctor.py').chmod(0o755)
        subprocess.run(['omarchy','plugin','validate',str(stage)],check=True)
        # Existing installation remains recoverable from the explicit backup.
        displaced=dest.parent/(stage.name+'-previous')
        if dest.exists():dest.rename(displaced)
        try:
            stage.rename(dest)
        except OSError:
            if displaced.exists():displaced.rename(dest)
            raise
        if displaced.exists():shutil.rmtree(displaced)
    finally:
        if stage.exists():shutil.rmtree(stage)
    receipt={'installed':str(dest),'backup':str(backup),'enabled':False,'enable_requested':args.enable,'version':json.loads((ROOT/'manifest.json').read_text())['version']}
    receipt_path=state/'installation.json'
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    if args.enable:
        try:
            subprocess.run(['omarchy-shell','shell','rescanPlugins'],check=True)
            # Beside Pulse when this host has it on the bar; otherwise the manifest's default section.
            # Existing widgets keep their order either way.
            placement=['--section','center','--after','nixfred.pulse'] if '"nixfred.pulse"' in (config.read_text() if config.exists() else '') else ['--section','right','--index','0']
            subprocess.run(['omarchy','bar','put','nixfred.doctor',*placement],check=True)
            receipt['enabled']=True
        except (subprocess.CalledProcessError,OSError) as exc:
            receipt['activation_error']=str(exc)
        receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    return 1 if receipt.get('activation_error') else 0

if __name__=='__main__':raise SystemExit(main())
