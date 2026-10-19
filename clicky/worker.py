"""Private JSON-lines worker. No listening network API and no shell execution."""
import asyncio
import base64
import contextlib
import copy
import hashlib
import json
import logging
import os
import signal
import sys
import tempfile
import time
import uuid
from pathlib import Path
from .agent import Agent
from .config import Config,PROJECT,provider_key_reference
from .context import Context
from .desktop import DesktopBroker,command
from .mcp_manager import MCPManager
from .provider import CompatibleProvider
from .security import Approvals,Secrets,redacted
from .storage import Store
from .voice import Voice


class Worker:
    def __init__(self,emit=None):
        os.umask(0o077);logging.disable(logging.CRITICAL)
        self.emit=emit or self.output;self.config=Config();self.store=Store();self.context=Context(self.store);self.secrets=Secrets()
        rows=self.store.conversations();last=self.config.data.get('last_conversation')
        self.cid=last if any(r['id']==last for r in rows) else rows[0]['id'] if rows else self.store.new()
        self.approvals=Approvals(self.emit);self.mcp=MCPManager(self.config,self.secrets,self.emit)
        self.agent=Agent(self.store,self.mcp,self.approvals,self.emit);self.desktop=DesktopBroker(self.config)
        self.temp=tempfile.TemporaryDirectory(prefix='clicky-',dir=os.environ.get('XDG_RUNTIME_DIR') or None);self.tempdir=Path(self.temp.name)
        self.voice=Voice(self.tempdir,self.emit);self.attachment=None;self.window=None;self.prepared={};self.active=None;self.tasks=set();self.quitting=False
    def output(self,event,**data):
        print(json.dumps({'event':event,**data},ensure_ascii=False),flush=True)
    def state(self):
        rows=self.store.conversations();current=next(r for r in rows if r['id']==self.cid)
        self.emit('state',conversation=self.cid,conversations=rows,messages=self.store.messages(self.cid),draft=current['draft'],
            selections=self.store.selections(self.cid),activity=self.store.events(self.cid),provider=self.config.data['provider'],
            roots=self.config.data['roots'],busy=self.active is not None,attachment=self.attachment,window=self.window)
    def spawn(self,coro):
        task=asyncio.create_task(self.guarded(coro));self.tasks.add(task);task.add_done_callback(self.tasks.discard);return task
    async def guarded(self,coro):
        try: await coro
        except asyncio.CancelledError: pass
        except Exception as e:
            message=str(e)[:800] if isinstance(e,(ValueError,FileNotFoundError)) else type(e).__name__+': operation failed; check settings and connection'
            self.emit('error',message=redacted(message));self.emit('restore_window')
    async def provider(self):
        cfg=copy.deepcopy(self.config.data['provider']);ref=cfg.get('key_ref','')
        key=await asyncio.to_thread(self.secrets.get,ref) if ref else ''
        return CompatibleProvider(cfg,key)
    def invalidate(self): self.prepared={}
    def remove_attachment(self):
        if self.attachment: Path(self.attachment['path']).unlink(missing_ok=True)
        self.attachment=None
    def prepare(self,text):
        if not text.strip(): raise ValueError('Enter a message first')
        p=self.config.data['provider'];catalog=self.mcp.catalog()
        tools=[v['definition'] for v in catalog.values()] if p['verified'].get('tools') else []
        req=self.context.assemble(self.cid,text,p,tools,self.attachment,self.window)
        req['user_text']=text;req['conversation']=self.cid;req['provider_config']=copy.deepcopy(p)
        if self.attachment:
            data=Path(self.attachment['path']).read_bytes()
            if len(data)>12_000_000: raise ValueError('Capture exceeds 12 MB limit')
            req['messages'][-1]['content']=[{'type':'text','text':redacted(text)},
                {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode()}}]
        key=uuid.uuid4().hex;self.prepared={key:copy.deepcopy(req)}
        shown=copy.deepcopy(req);shown.pop('provider_config')
        if self.attachment:
            shown['messages'][-1]['content'][1]['image_url']['url']='[local preview PNG: sha256 '+hashlib.sha256(data).hexdigest()+', '+str(len(data))+' bytes; encoded only on Send]'
        self.emit('preview',id=key,request=shown)
        return key
    async def send(self,key):
        if self.active: raise ValueError('Another operation is already running')
        req=self.prepared.pop(key,None)
        if not req or req['conversation']!=self.cid: raise ValueError('Request preview expired; preview again')
        p=req['provider_config']
        if p!=self.config.data['provider']: raise ValueError('Provider settings changed; preview again')
        if not p['verified'].get('text'): raise ValueError('Verify the local model with the text probe in Settings before sending')
        if req['attachment'] and not p['verified'].get('vision'): raise ValueError('Vision is unverified. Run the synthetic image probe or remove the capture.')
        self.active=asyncio.current_task();self.emit('busy',value=True)
        try:
            provider=await self.provider()
            async with asyncio.timeout(180): await self.agent.run(self.cid,req,provider)
        finally:
            self.active=None;self.remove_attachment();self.window=None;self.state();self.emit('busy',value=False)
    async def direct_tool(self,sid,name,args):
        if self.active: raise ValueError('Another operation is already running')
        alias=next((a for a,v in self.mcp.catalog().items() if v['server']==sid and v['tool']==name),None)
        if not alias: raise ValueError('Tool is disabled or unavailable')
        self.active=asyncio.current_task();self.emit('busy',value=True)
        try: await self.agent.tool(self.cid,alias,args)
        finally: self.active=None;self.state();self.emit('busy',value=False)
    async def capture(self,region):
        await asyncio.sleep(.25);self.remove_attachment()
        self.attachment=await self.desktop.capture(self.tempdir/'capture.png',region)
        self.invalidate();self.state();self.emit('restore_window')
    async def window_context(self):
        await asyncio.sleep(.25);self.window=await self.desktop.active();self.invalidate();self.state();self.emit('restore_window')
    async def probe(self,kind):
        if kind not in {'text','stream','tools','vision'}: raise ValueError('Unknown probe')
        snapshot=copy.deepcopy(self.config.data['provider']);p=await self.provider();result=await p.probe(kind)
        if snapshot!=self.config.data['provider']: raise ValueError('Settings changed during the probe; retry')
        self.config.data['provider']['verified'][kind]={'at':time.time(),'verified':True}
        if kind=='stream': self.config.data['provider']['stream']=True
        self.config.save();self.invalidate();self.state();self.emit('notice',message=kind+' capability verified with synthetic data')
    async def cancel(self):
        self.approvals.cancel();self.invalidate()
        # Cancel generation, transcription, capture and connection work, then reap subprocesses.
        tasks=[t for t in self.tasks if t is not asyncio.current_task()]
        for t in tasks: t.cancel()
        if tasks: await asyncio.gather(*tasks,return_exceptions=True)
        await self.voice.cancel();self.remove_attachment();(self.tempdir/'capture.png').unlink(missing_ok=True)
        self.emit('busy',value=False);self.emit('restore_window')
    async def dispatch(self,msg):
        cmd=msg.get('cmd');self.invalidate() if cmd in {'draft','select','fresh_context','switch','new','remove_attachment','remove_window'} else None
        if cmd=='state': self.state();self.mcp.notify()
        elif cmd=='draft': self.store.draft(msg.get('conversation') or self.cid,msg.get('text',''))
        elif cmd in {'new','switch','clear'}:
            if self.active: raise ValueError('Stop the current operation before changing conversations')
            if cmd=='new': self.cid=self.store.new()
            elif cmd=='switch':
                if not any(c['id']==msg['id'] for c in self.store.conversations()): raise ValueError('Conversation no longer exists')
                self.cid=msg['id']
            elif msg.get('confirmed'): self.store.clear(self.cid)
            else: raise ValueError('Clear requires explicit confirmation')
            self.remove_attachment();self.window=None;self.config.data['last_conversation']=self.cid;self.config.save();self.state()
        elif cmd=='search': self.emit('search',query=msg.get('text',''),conversations=self.store.conversations(msg.get('text','')))
        elif cmd=='history': self.emit('history',conversation=msg['id'],messages=self.store.messages(msg['id']))
        elif cmd=='select': self.store.select(self.cid,int(msg['message']),bool(msg['enabled']));self.state()
        elif cmd=='fresh_context': self.store.fresh_context(self.cid);self.state()
        elif cmd=='prepare': self.prepare(msg.get('text',''))
        elif cmd=='send': self.spawn(self.send(msg['id']))
        elif cmd=='cancel': await self.cancel()
        elif cmd=='approve': self.approvals.resolve(msg['id'],bool(msg.get('allow')))
        elif cmd=='capture': self.spawn(self.capture(bool(msg.get('region'))))
        elif cmd=='window_context': self.spawn(self.window_context())
        elif cmd=='remove_attachment': self.remove_attachment();self.state()
        elif cmd=='remove_window': self.window=None;self.state()
        elif cmd=='ocr':
            if not self.attachment: raise ValueError('Capture an image first')
            path=self.attachment['path']
            async def ocr(): self.emit('transcript',text=(await command(['tesseract',path,'stdout'],20,32000)).strip())
            self.spawn(ocr())
        elif cmd=='record_start': self.spawn(self.voice.start())
        elif cmd=='record_stop': self.spawn(self.voice.stop())
        elif cmd=='provider_save':
            if self.active: raise ValueError('Stop current operation before changing provider')
            self.config.provider(msg['values'])
            if msg.get('key'):
                ref=provider_key_reference(self.config.data['provider']['base_url'])
                await asyncio.to_thread(self.secrets.put,ref,msg['key']);self.config.data['provider']['key_ref']=ref;self.config.save()
            self.invalidate();self.state()
        elif cmd=='models':
            async def models(): self.emit('models',models=await (await self.provider()).models())
            self.spawn(models())
        elif cmd=='probe': self.spawn(self.probe(msg['kind']))
        elif cmd=='mcp_connect': self.spawn(self.mcp.connect(msg['id']))
        elif cmd=='server_toggle':
            s=next(s for s in self.config.data['servers'] if s['id']==msg['id']);s['enabled']=bool(msg['enabled']);self.config.save();self.invalidate()
            if s['enabled']: self.spawn(self.mcp.connect(s['id']))
            elif s['id'] in self.mcp.connections: await self.mcp.connections[s['id']].close()
            self.mcp.notify()
        elif cmd=='tool_toggle':
            s=next(s for s in self.config.data['servers'] if s['id']==msg['server']);disabled=set(s.get('disabled_tools',[]))
            disabled.discard(msg['tool']) if msg['enabled'] else disabled.add(msg['tool']);s['disabled_tools']=sorted(disabled);self.config.save();self.invalidate();self.mcp.notify()
        elif cmd=='server_register':
            if not msg.get('confirmed'): raise ValueError('Trust confirmation required before registering server code')
            data=copy.deepcopy(self.config.data);data['servers'].append(msg['spec']);self.config.validate(data)
            self.config.data=data;self.config.save();self.mcp.notify()
        elif cmd=='tool_call': self.spawn(self.direct_tool(msg['server'],msg['tool'],msg.get('arguments',{})))
        else: raise ValueError('Unknown worker command')
    async def close(self):
        await self.cancel();await self.mcp.stop();self.store.close();self.temp.cleanup()


async def main():
    worker=Worker();worker.state();worker.spawn(worker.mcp.start())
    reader=asyncio.StreamReader(limit=1_000_000);protocol=asyncio.StreamReaderProtocol(reader)
    await asyncio.get_running_loop().connect_read_pipe(lambda:protocol,sys.stdin)
    try:
        while line:=await reader.readline():
            try:
                msg=json.loads(line)
                if msg.get('cmd')=='quit': break
                await worker.guarded(worker.dispatch(msg))
            except (ValueError,KeyError): worker.emit('error',message='Invalid worker request')
    finally: await worker.close()


if __name__=='__main__': asyncio.run(main())
