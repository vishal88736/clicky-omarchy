"""Narrow local actions; no shell, clipboard access or raw input permissions."""
import asyncio
import contextlib
import json
import os
import re
import signal
import stat
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


async def command(argv,timeout=10,limit=100000):
    p=await asyncio.create_subprocess_exec(*argv,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,start_new_session=True)
    async def read_limited(stream):
        out=bytearray()
        while chunk:=await stream.read(8192):
            out.extend(chunk)
            if len(out)>limit: raise ValueError("Command output exceeds limit")
        return bytes(out)
    try:
        async with asyncio.timeout(timeout):
            out,err=await asyncio.gather(read_limited(p.stdout),read_limited(p.stderr));await p.wait()
        if p.returncode: raise ValueError(f"{Path(argv[0]).name} failed ({p.returncode}); check device/session permissions")
        return out.decode(errors="replace")
    finally:
        if p.returncode is None:
            with contextlib.suppress(ProcessLookupError): os.killpg(p.pid,signal.SIGTERM)
            try: await asyncio.wait_for(p.wait(),1)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError): os.killpg(p.pid,signal.SIGKILL)
                await p.wait()


class Files:
    def __init__(self,roots): self.roots=[Path(p).resolve() for p in roots]
    def parts(self,path):
        target=Path(os.path.abspath(os.path.expanduser(path)))
        for root in self.roots:
            if target.is_relative_to(root):
                parts=target.relative_to(root).parts
                if any(p.startswith('.') for p in parts): raise ValueError("Hidden paths are not exposed by bundled filesystem tools")
                return root,parts
        raise ValueError("Path is outside explicitly permitted roots")
    @contextlib.contextmanager
    def parent(self,path):
        root,parts=self.parts(path)
        if not parts: raise ValueError("Operation needs a file below a permitted root")
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for part in parts[:-1]:
                new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
            yield fd,parts[-1]
        finally: os.close(fd)
    def read(self,path):
        with self.parent(path) as (fd,name):
            f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            with os.fdopen(f,'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode): raise ValueError("Only regular files may be read")
                data=stream.read(32769)
                if len(data)>32768: raise ValueError("File exceeds 32 KiB limit")
                return data.decode('utf-8')
    def listing(self,path):
        root,parts=self.parts(path);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for part in parts:
                new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=new
            return sorted(n for n in os.listdir(fd) if not n.startswith('.'))[:250]
        finally: os.close(fd)
    def write(self,path,text):
        if len(text.encode())>32768: raise ValueError("Write exceeds 32 KiB limit")
        with self.parent(path) as (fd,name):
            try:
                st=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if not stat.S_ISREG(st.st_mode): raise ValueError("Refusing a symlink or non-regular destination")
            except FileNotFoundError: pass
            tmp='.clicky-'+os.urandom(12).hex()
            try:
                f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
                with os.fdopen(f,'w') as stream: stream.write(text);stream.flush();os.fsync(stream.fileno())
                os.replace(tmp,name,src_dir_fd=fd,dst_dir_fd=fd);os.fsync(fd)
            finally:
                with contextlib.suppress(FileNotFoundError): os.unlink(tmp,dir_fd=fd)
        return {"written":True,"bytes":len(text.encode())}


class DesktopBroker:
    def __init__(self,config): self.config=config
    async def active(self):
        raw=json.loads(await command(["hyprctl","activewindow","-j"],3))
        return {k:raw.get(k) for k in ["address","class","title","pid","xwayland"]}
    async def windows(self):
        raw=json.loads(await command(["hyprctl","clients","-j"],3))
        return [{k:w.get(k) for k in ["address","class","title","pid","floating"]} for w in raw]
    async def window(self,address,action):
        if not re.fullmatch(r"0x[0-9a-fA-F]+",address) or address not in {w["address"] for w in await self.windows()}: raise ValueError("Window no longer exists")
        actions={"focus":"focuswindow","close":"closewindow"}
        if action not in actions: raise ValueError("Only focus and close are permitted")
        return await command(["hyprctl","dispatch",actions[action],"address:"+address],3)
    async def open_url(self,url):
        p=urlsplit(url)
        if p.scheme not in {"https","http"} or not p.hostname or p.username or p.password or any(c in url for c in '\r\n\x00'): raise ValueError("Only ordinary HTTP(S) URLs are permitted")
        return await command(["xdg-open",url],8)
    async def launch(self,application):
        allowed={"browser":["omarchy","launch","browser"],"terminal":["xdg-terminal-exec"],"files":["nautilus","--new-window"]}
        if application not in allowed: raise ValueError("Application is not in the launcher allowlist")
        return await command(allowed[application],8)
    async def approved_command(self,name):
        argv=self.config.data["commands"].get(name)
        if not argv or not Path(argv[0]).is_absolute(): raise ValueError("Command alias is not approved")
        return await command(argv,8)
    async def pointer(self,x,y):
        monitors=json.loads(await command(["hyprctl","monitors","-j"],3))
        if not any(m['x']<=x<m['x']+m['width']/m['scale'] and m['y']<=y<m['y']+m['height']/m['scale'] for m in monitors): raise ValueError("Point is outside connected monitor geometry")
        return await command(["hyprctl","dispatch","movecursor",str(int(x)),str(int(y))],3)
    async def type_text(self,address,text):
        active=await self.active()
        classes=self.config.data.get("input_classes",[])
        if active['address']!=address or active['class'] not in classes: raise ValueError("Input is disabled for this window; configure an explicit input_classes allowlist")
        if len(text)>2000 or any(c in text for c in '\r\n\t\x00'): raise ValueError("Only bounded single-line text is permitted")
        if re.search(r"(?i)(foot|kitty|terminal|alacritty|ghostty|code|emacs)",active['class'] or ''): raise ValueError("Typing into terminal/editor hosts is disabled")
        return await command(["wtype","--",text],5)
    async def capture(self,path,region=False):
        if region:
            geometry=(await command(["slurp"],45,1000)).strip()
            if not re.fullmatch(r"-?\d+,-?\d+ \d+x\d+",geometry): raise ValueError("Region selection cancelled")
            argv=["grim","-g",geometry,str(path)]
        else:
            monitors=json.loads(await command(["hyprctl","monitors","-j"],3))
            chosen=next((m for m in monitors if m.get('focused')),monitors[0])
            argv=["grim","-o",chosen['name'],str(path)]
        await command(argv,8);path.chmod(0o600)
        return {"path":str(path),"bytes":path.stat().st_size,"mime":"image/png","source":"explicit region" if region else "explicit focused monitor"}
