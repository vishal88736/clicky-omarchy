"""One-use approvals and Secret Service access."""
import asyncio
import os
import re
import subprocess
import time
import uuid


def redacted(value):
    if isinstance(value,dict):
        return {k:"[redacted]" if re.search(r"(?i)(token|password|secret|api.?key|authorization|cookie)",k) else redacted(v) for k,v in value.items()}
    if isinstance(value,list): return [redacted(v) for v in value]
    if isinstance(value,str):
        value=re.sub(r"(?i)(Bearer\s+)\S+",r"\1[redacted]",value)
        value=re.sub(r"\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{12,}","[redacted]",value)
        return re.sub(r"(?im)((?:api[_-]?key|password|access[_-]?token)\s*[:=]\s*)[^\s,]+",r"\1[redacted]",value)
    return value


class Secrets:
    def get(self,ref):
        if ref.startswith("env:"): return os.environ.get(ref[4:],"")
        p=subprocess.run(["secret-tool","lookup","application","clicky","entry",ref],capture_output=True,timeout=8)
        return p.stdout.decode().strip() if p.returncode==0 else ""

    def put(self,ref,value):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}",ref): raise ValueError("Invalid secret reference")
        p=subprocess.run(["secret-tool","store","--label=Clicky "+ref,"application","clicky","entry",ref],input=value.encode(),capture_output=True,timeout=30)
        if p.returncode: raise ValueError("GNOME Keyring could not save the secret; unlock the login keyring")


class Approvals:
    def __init__(self,emit): self.emit=emit;self.pending={}

    async def request(self,tool,arguments,effect):
        key=uuid.uuid4().hex;future=asyncio.get_running_loop().create_future();self.pending[key]=future
        self.emit("approval",id=key,tool=tool,arguments=redacted(arguments),effect=effect,deadline=time.time()+120)
        try: return await asyncio.wait_for(future,120)
        except asyncio.TimeoutError: return False
        finally:
            self.pending.pop(key,None);self.emit("approval_closed",id=key)

    def resolve(self,key,allow):
        f=self.pending.get(key)
        if f and not f.done(): f.set_result(bool(allow))

    def cancel(self):
        for f in list(self.pending.values()):
            if not f.done(): f.set_result(False)
