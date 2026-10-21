"""Reversible user installation; preserve unrelated configuration byte for byte."""
import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from .config import PROJECT

BEGIN='-- BEGIN CLICKY MANAGED INTEGRATION\n'
END='-- END CLICKY MANAGED INTEGRATION\n'


def digest(data):return hashlib.sha256(data).hexdigest()


def atomic(path,data,mode=0o600):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_symlink():raise ValueError('Refusing symlink destination: '+str(path))
    fd,tmp=tempfile.mkstemp(prefix='.clicky-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,mode);os.replace(tmp,path)
    finally:Path(tmp).unlink(missing_ok=True)


def bind_parts(hotkey):
    parts=[p.strip().upper() for p in hotkey.split('+')];mods={'SUPER':64,'CTRL':4,'ALT':8,'SHIFT':1}
    if len(parts)<2 or len(set(parts))!=len(parts) or any(p not in mods for p in parts[:-1]) or not re.fullmatch(r'[A-Z0-9_]+',parts[-1]):
        raise ValueError('Use modifier names plus one key, for example SUPER + CTRL + SEMICOLON')
    return sum(mods[p] for p in parts[:-1]),parts[-1].lower()


def install(home,hotkey='SUPER + CTRL + SEMICOLON',activate=True,autostart=True):
    home=Path(home).resolve();state=home/'.local/state/clicky';manifest=state/'install.json';bindings=home/'.config/hypr/bindings.lua'
    if manifest.exists():raise ValueError('Already installed. Uninstall the integration before changing its hotkey or paths; history is retained.')
    mod,key=bind_parts(hotkey)
    if activate:
        live=json.loads(subprocess.run(['hyprctl','binds','-j'],check=True,capture_output=True,text=True,timeout=5).stdout)
        if any(b.get('modmask')==mod and b.get('key','').lower()==key for b in live):raise ValueError('Hotkey is already bound; choose another --hotkey')
    if bindings.is_symlink():raise ValueError('Refusing to alter a symlink bindings file')
    before=bindings.read_bytes() if bindings.exists() else b''
    if BEGIN.encode() in before or END.encode() in before:raise ValueError('An unmanaged Clicky block already exists')
    launcher=home/'.local/bin/clicky';integration=home/'.config/clicky/hyprland.lua'
    command=shlex.quote(str(launcher))+' toggle'
    lua='-- Clicky only: no packaged Omarchy files are modified.\n'
    lua+='o.bind('+json.dumps(hotkey)+', "Clicky assistant", '+json.dumps(command)+')\n'
    lua+='o.window("^clicky$", { float = true, pin = true, border_size = 0, center = true })\n'
    block=(BEGIN+'dofile('+json.dumps(str(integration))+')\n'+END).encode()
    separator=b'' if not before or before.endswith(b'\n') else b'\n'
    # Include the separator in the owned block so uninstall restores exact bytes.
    block=separator+block
    desktop='[Desktop Entry]\nType=Application\nName=Clicky\nName[hi]=क्लिकी\nComment=Your Omarchy pointer buddy — ask, talk, and point\nComment[hi]=संदर्भ और अनुमति के साथ डेस्कटॉप सहायक\n'
    desktop+='Exec="'+str(launcher).replace('\\','\\\\').replace('"','\\"')+'" open\nIcon=clicky\nTerminal=false\nCategories=Utility;\nStartupWMClass=clicky\n'
    service='[Unit]\nDescription=Clicky desktop assistant\nPartOf=graphical-session.target\nAfter=graphical-session.target\n\n[Service]\nType=simple\n'
    service+='ExecStart="'+str(launcher).replace('%','%%').replace('"','\\"')+'" open --background\nEnvironment=QT_QPA_PLATFORM=wayland\nRestart=on-failure\nRestartSec=3\nKillMode=mixed\nTimeoutStopSec=8\nUMask=0077\n\n[Install]\nWantedBy=graphical-session.target\n'
    files={launcher:('#!/bin/sh\nexec '+shlex.quote(str(PROJECT/'bin/clicky'))+' "$@"\n').encode(),
        integration:lua.encode(),home/'.local/share/applications/clicky.desktop':desktop.encode(),
        home/'.config/systemd/user/clicky.service':service.encode(),home/'.local/share/icons/hicolor/scalable/apps/clicky.svg':(PROJECT/'pkgbuild/clicky.svg').read_bytes()}
    for path in files:
        if path.exists() or path.is_symlink():raise ValueError('Refusing to overwrite existing file: '+str(path))
        if any(p.is_symlink() for p in path.parents if p!=home and p.is_relative_to(home)):raise ValueError('Refusing symlink parent: '+str(path))
    backup=state/'backups'/('bindings-'+str(time.time_ns())+'.lua');atomic(backup,before)
    written=[]
    try:
        for path,data in files.items():atomic(path,data,0o755 if path==launcher else 0o600 if path==integration else 0o644);written.append(path)
        atomic(bindings,before+block,bindings.stat().st_mode&0o777 if bindings.exists() else 0o600)
        data={'version':1,'files':{str(p):digest(b) for p,b in files.items()},'bindings':str(bindings),'block':block.decode(),'before_hash':digest(before),'backup':str(backup),'autostart':autostart}
        atomic(manifest,json.dumps(data,indent=2).encode())
        if activate:
            subprocess.run(['hyprctl','reload'],check=True,capture_output=True,timeout=10)
            errors=subprocess.run(['hyprctl','configerrors'],check=True,capture_output=True,text=True,timeout=5).stdout.strip()
            if errors:raise ValueError('Hyprland rejected the integration; rolling it back')
            subprocess.run(['systemctl','--user','daemon-reload'],check=True,timeout=10)
            if autostart:subprocess.run(['systemctl','--user','enable','--now','clicky.service'],check=True,timeout=15)
        return {'installed':True,'hotkey':hotkey,'manifest':str(manifest)}
    except BaseException:
        atomic(bindings,before)
        for path in written:path.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        if activate:subprocess.run(['hyprctl','reload'],capture_output=True,timeout=10)
        raise


def uninstall(home,activate=True):
    home=Path(home).resolve();manifest=home/'.local/state/clicky/install.json'
    if not manifest.exists():return {'installed':False,'message':'No managed installation found; no files removed'}
    data=json.loads(manifest.read_text());bindings=Path(data['bindings']);block=data['block'].encode()
    current=bindings.read_bytes()
    if current.count(block)!=1:raise ValueError('Managed Hyprland block changed; refusing automatic removal')
    for name,expected in data['files'].items():
        path=Path(name)
        if not path.is_relative_to(home) or path.is_symlink() or (path.exists() and digest(path.read_bytes())!=expected):raise ValueError('Owned file changed; preserve/review it before uninstall: '+name)
    if activate:
        subprocess.run(['systemctl','--user','disable','--now','clicky.service'],check=False,capture_output=True,timeout=15)
        subprocess.run([str(PROJECT/'bin/clicky'),'stop'],check=False,capture_output=True,timeout=8)
    atomic(bindings,current.replace(block,b'',1),bindings.stat().st_mode&0o777)
    for name in data['files']:Path(name).unlink(missing_ok=True)
    manifest.unlink()
    if activate:
        subprocess.run(['systemctl','--user','daemon-reload'],check=True,timeout=10)
        subprocess.run(['hyprctl','reload'],check=True,capture_output=True,timeout=10)
        errors=subprocess.run(['hyprctl','configerrors'],check=True,capture_output=True,text=True,timeout=5).stdout.strip()
        if errors:raise ValueError('Existing Hyprland configuration reports errors after uninstall')
    return {'uninstalled':True,'history_retained':True,'backup_retained':data['backup']}


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['install','uninstall']);p.add_argument('--hotkey',default='SUPER + CTRL + SEMICOLON');p.add_argument('--no-autostart',action='store_true')
    a=p.parse_args()
    try:result=install(Path.home(),a.hotkey,autostart=not a.no_autostart) if a.action=='install' else uninstall(Path.home())
    except (ValueError,OSError,subprocess.SubprocessError) as e:p.exit(1,str(e)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
