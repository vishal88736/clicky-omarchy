"""Private atomic configuration contains secret references, never credentials."""
import copy
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parent.parent


def private_dir(path):
    path=Path(path)
    if path.is_symlink(): raise ValueError("Application directory cannot be a symlink")
    path.mkdir(mode=0o700,parents=True,exist_ok=True)
    path.chmod(0o700)
    return path


def endpoint(value):
    p=urlsplit(value)
    if p.username or p.password or p.query or p.fragment or not p.hostname:
        raise ValueError("Endpoint needs a host and cannot contain credentials, query or fragment")
    if p.scheme!="https" and not (p.scheme=="http" and p.hostname in {"localhost","127.0.0.1","::1"}):
        raise ValueError("Remote endpoints require HTTPS; HTTP is permitted only on loopback")
    return value.rstrip("/")


def provider_key_reference(url):
    return 'provider-'+hashlib.sha256(endpoint(url).encode()).hexdigest()[:24]


def defaults():
    return {"version":1,"provider":{"base_url":"http://127.0.0.1:8080/v1","model":"","key_ref":"",
        "context_tokens":8192,"response_tokens":1024,"stream":False,"verified":{},"timeout":90},
        "roots":[str(PROJECT/"docs")],
        "commands":{"date":["/usr/bin/date","--iso-8601=seconds"],"uptime":["/usr/bin/uptime"]},
        "servers":[{"id":kind,"transport":"stdio","command":str(PROJECT/".venv/bin/python"),
        "args":["-m","clicky.safe_server","--kind",kind],"enabled":True,"env_refs":{},"disabled_tools":[]}
        for kind in ["workspace","desktop"]]}


class Config:
    def __init__(self,directory=None):
        self.directory=private_dir(directory or os.environ.get("CLICKY_CONFIG_HOME",Path.home()/".config/clicky"))
        self.path=self.directory/"config.json"
        if self.path.is_symlink(): raise ValueError("Refusing symlink configuration")
        self.data=json.loads(self.path.read_text()) if self.path.exists() else defaults()
        self.validate(self.data)
        if self.data['provider'].get('key_ref')=='provider':
            # Legacy unscoped references must never follow a user to another endpoint.
            self.data['provider']['key_ref']='';self.save()
        if not self.path.exists(): self.save()

    @staticmethod
    def validate(data):
        if data.get("version")!=1: raise ValueError("Unsupported configuration version")
        p=data["provider"];endpoint(p["base_url"])
        if not 2048<=int(p["context_tokens"])<=2000000 or not 128<=int(p["response_tokens"])<int(p["context_tokens"]):
            raise ValueError("Invalid context or response budget")
        ids=set()
        for s in data["servers"]:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}",s["id"]) or s["id"] in ids: raise ValueError("Invalid or duplicate server ID")
            ids.add(s["id"])
            if s["transport"] not in {"stdio","streamable_http","sse"}: raise ValueError("Unsupported transport")
            if s["transport"]!="stdio": endpoint(s["url"])
            if any(k in s for k in ("env","headers","api_key","token","password")): raise ValueError("Use env_refs/header_refs for secrets")
            if re.search(r"(?i)(api.?key|password|authorization|bearer|--token|secret=)"," ".join(s.get("args",[]))):
                raise ValueError("Never put credentials in process arguments")
        for root in data["roots"]:
            p=Path(root).expanduser()
            if not p.is_absolute() or not p.is_dir() or p.resolve()==Path("/"): raise ValueError("Roots must be existing absolute directories, never /")

    def save(self):
        self.validate(self.data)
        fd,name=tempfile.mkstemp(prefix=".config-",dir=self.directory)
        try:
            with os.fdopen(fd,"w") as f:
                json.dump(self.data,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally: Path(name).unlink(missing_ok=True)

    def provider(self,values):
        updated=copy.deepcopy(self.data);p=updated["provider"]
        for key in ("base_url","model","context_tokens","response_tokens"):
            if key in values: p[key]=values[key]
        p["base_url"]=endpoint(p["base_url"]);p["model"]=p["model"].strip()
        if p['base_url']!=self.data['provider']['base_url']: p['key_ref']=''
        if p!=self.data["provider"]: p.update(verified={},stream=False)
        self.validate(updated);self.data=updated;self.save()
