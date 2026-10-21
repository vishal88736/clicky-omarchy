"""Read-only acceptance check. Never moves the pointer, injects input or enables guides."""
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def run(argv):
    return subprocess.run(argv,cwd=ROOT,check=True,capture_output=True,text=True,timeout=5).stdout


def main():
    state=json.loads(run(['bin/clicky','info']))
    assert state['following'] is False,'Unexpected cursor-following mode'
    assert not state['guides'] and not state['guiding'],'Disable optional hints before this idle check'
    layers=json.loads(run(['hyprctl','layers','-j']))
    names=[layer['namespace'] for output in layers.values() for level in output['levels'].values() for layer in level]
    assert not {'clicky-buddy','clicky-guidance'}&set(names),'Unexpected idle overlay'
    assert not run(['hyprctl','configerrors']).strip(),'Hyprland configuration errors'
    clients=[c for c in json.loads(run(['hyprctl','clients','-j'])) if c['class']=='clicky']
    for c in clients:
        assert not c['xwayland'] and c['floating'] and c['pinned'],'Unexpected prompt window behavior'
    print('PASS: no cursor follower; no idle overlay; guides disabled; Hyprland configuration clean')
    print('Prompt visible:',state['visible'],'native prompt checked:',bool(clients))


if __name__=='__main__':main()
