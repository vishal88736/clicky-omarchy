"""Genuine MCP 2.x connections, each owned by one async task."""
import asyncio
import contextlib
import hashlib
import json
import os
from pathlib import Path
import httpx2
from jsonschema import Draft202012Validator
from mcp import ClientSession,StdioServerParameters,types
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client
from .config import PROJECT,endpoint


class Connection:
    def __init__(self,spec,secrets,emit):
        self.spec=spec;self.secrets=secrets;self.emit=emit;self.tools={};self.state="disconnected";self.protocol=""
        self.queue=asyncio.Queue();self.task=None;self.ready=None;self.current=None

    async def connect(self):
        if self.task: await self.close()
        self.ready=asyncio.get_running_loop().create_future();self.state="connecting";self.emit()
        self.task=asyncio.create_task(self.run())
        try: await asyncio.wait_for(asyncio.shield(self.ready),15)
        except BaseException:
            await self.close();raise

    async def run(self):
        try:
            async with contextlib.AsyncExitStack() as stack:
                if self.spec["transport"]=="stdio":
                    allowed=["PATH","HOME","LANG","LC_ALL","XDG_RUNTIME_DIR","WAYLAND_DISPLAY","HYPRLAND_INSTANCE_SIGNATURE","DBUS_SESSION_BUS_ADDRESS","CLICKY_CONFIG_HOME","CLICKY_DATA_HOME"]
                    env={k:os.environ[k] for k in allowed if k in os.environ}
                    for k,v in self.spec.get("env_refs",{}).items(): env[k]=self.secrets.get(v)
                    errlog=stack.enter_context(open(os.devnull,"w"))
                    streams=await stack.enter_async_context(stdio_client(StdioServerParameters(command=self.spec["command"],args=self.spec.get("args",[]),env=env,cwd=str(PROJECT)),errlog=errlog))
                else:
                    url=endpoint(self.spec["url"])
                    headers={k:self.secrets.get(v) for k,v in self.spec.get("header_refs",{}).items()}
                    if self.spec["transport"]=="streamable_http":
                        client=await stack.enter_async_context(httpx2.AsyncClient(headers=headers,trust_env=False,follow_redirects=False,timeout=30))
                        streams=await stack.enter_async_context(streamable_http_client(url,http_client=client))
                    else:
                        def factory(**kwargs): return httpx2.AsyncClient(**(kwargs|{"trust_env":False,"follow_redirects":False}))
                        streams=await stack.enter_async_context(sse_client(url,headers=headers,httpx_client_factory=factory,sse_read_timeout=30))
                session=await stack.enter_async_context(ClientSession(streams[0],streams[1],read_timeout_seconds=25))
                result=await session.initialize();self.protocol=result.protocol_version
                cursor=None;self.tools={}
                for _ in range(30):
                    listing=await session.list_tools(params=types.PaginatedRequestParams(cursor=cursor) if cursor else None)
                    for tool in listing.tools:
                        Draft202012Validator.check_schema(tool.input_schema)
                        self.tools[tool.name]={"name":tool.name,"description":tool.description or "","schema":tool.input_schema}
                    cursor=listing.next_cursor
                    if not cursor: break
                else: raise ValueError("Excessive MCP tool pagination")
                self.state="connected";self.emit();self.ready.set_result(True)
                while True:
                    name,args,future=await self.queue.get();self.current=future
                    try:
                        if not future.cancelled():
                            result=await session.call_tool(name,args,read_timeout_seconds=25)
                            payload=result.model_dump(mode="json",by_alias=True)
                            if len(json.dumps(payload))>100000: raise ValueError("Tool result exceeds 100 KB limit")
                            if not future.done(): future.set_result(payload)
                    except Exception as e:
                        if not future.done(): future.set_exception(ValueError("MCP call failed: "+type(e).__name__))
                    finally: self.current=None
        except asyncio.CancelledError: raise
        except BaseException as e:
            self.state="error";self.emit()
            if self.ready and not self.ready.done(): self.ready.set_exception(ValueError("MCP connection failed: "+type(e).__name__))
        finally:
            if self.current and not self.current.done(): self.current.set_exception(ValueError("MCP connection closed"))
            while not self.queue.empty():
                _,_,f=self.queue.get_nowait()
                if not f.done(): f.set_exception(ValueError("MCP connection closed"))
            if self.state!="error": self.state="disconnected"
            self.emit()

    async def call(self,name,args):
        if self.state!="connected": raise ValueError("MCP server unavailable; reconnect in Tools")
        if name not in self.tools: raise ValueError("Unknown MCP tool")
        Draft202012Validator(self.tools[name]["schema"]).validate(args)
        f=asyncio.get_running_loop().create_future();await self.queue.put((name,args,f))
        try: return await asyncio.wait_for(f,30)
        except (asyncio.CancelledError,asyncio.TimeoutError):
            # Killing the session cancels its in-flight call instead of leaving a hidden action.
            await self.close();raise

    async def close(self):
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError,Exception): await self.task
            self.task=None
        self.state="disconnected";self.emit()


class MCPManager:
    def __init__(self,config,secrets,emit): self.config=config;self.secrets=secrets;self.emit=emit;self.connections={}
    def notify(self): self.emit("mcp",servers=self.status())
    def status(self):
        rows=[]
        for spec in self.config.data["servers"]:
            c=self.connections.get(spec["id"])
            rows.append({"id":spec["id"],"transport":spec["transport"],"enabled":spec.get("enabled",False),
                "state":c.state if c else "disconnected","protocol":c.protocol if c else "",
                "tools":[t|{"enabled":n not in spec.get("disabled_tools",[])} for n,t in c.tools.items()] if c else []})
        return rows
    async def start(self):
        await asyncio.gather(*(self.connect(s["id"]) for s in self.config.data["servers"] if s.get("enabled")),return_exceptions=True)
        self.notify()
    async def connect(self,sid):
        spec=next(s for s in self.config.data["servers"] if s["id"]==sid)
        if not spec.get("enabled"): return
        if sid in self.connections: await self.connections[sid].close()
        c=Connection(spec,self.secrets,self.notify);self.connections[sid]=c
        await c.connect()
    def catalog(self):
        result={}
        for spec in self.config.data["servers"]:
            c=self.connections.get(spec["id"])
            if not spec.get("enabled") or not c or c.state!="connected": continue
            for name,t in c.tools.items():
                if name in spec.get("disabled_tools",[]): continue
                alias="mcp_"+hashlib.sha256((spec["id"]+":"+name).encode()).hexdigest()[:24]
                result[alias]={"server":spec["id"],"tool":name,"schema":t["schema"],
                    "definition":{"type":"function","function":{"name":alias,"description":(spec["id"]+" / "+name+": "+t["description"])[:1800],"parameters":t["schema"]}}}
        return result
    async def call(self,alias,args):
        item=self.catalog().get(alias)
        if not item: raise ValueError("Tool is disabled or unavailable")
        return await self.connections[item["server"]].call(item["tool"],args)
    async def stop(self): await asyncio.gather(*(c.close() for c in self.connections.values()),return_exceptions=True)
