"""Headless diagnostics; never invokes desktop actions or an LLM."""
import argparse
import asyncio
import importlib.metadata
import json
import shutil
from .config import Config
from .mcp_manager import MCPManager
from .security import Secrets


async def check():
    config=Config();manager=MCPManager(config,Secrets(),lambda *a,**k:None)
    try:
        await manager.start()
        rows=manager.status()
        result={'application':'clicky','sdk':importlib.metadata.version('mcp'),
            'provider':{k:config.data['provider'][k] for k in ['base_url','model','verified']},
            'servers':[{k:r[k] for k in ['id','enabled','state','protocol']} for r in rows],
            'tools':{name:bool(shutil.which(name)) for name in ['grim','slurp','hyprctl','pw-record','voxtype','tesseract','secret-tool']}}
        result['ok']=all(not s['enabled'] or s['state']=='connected' for s in rows)
        return result
    finally:await manager.stop()


def main():
    p=argparse.ArgumentParser();p.add_argument('--json',action='store_true');p.parse_args()
    try:result=asyncio.run(check())
    except Exception as e:result={'ok':False,'error':type(e).__name__}
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)


if __name__=='__main__':main()
