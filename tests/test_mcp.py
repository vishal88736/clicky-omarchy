"""Actual official-SDK subprocess, Streamable HTTP and SSE integration."""
import asyncio
import contextlib
import json
import os
import socket
import sys
import pytest
from clicky.config import Config,PROJECT
from clicky.mcp_manager import MCPManager,Connection
from clicky.security import Secrets


@pytest.fixture
def config(tmp_path,monkeypatch):
    directory=tmp_path/'config';monkeypatch.setenv('CLICKY_CONFIG_HOME',str(directory))
    c=Config(directory);c.data['roots']=[str(tmp_path)];c.save()
    return c


@pytest.mark.integration
async def test_two_real_stdio_servers_discover_call_disable_failure(config):
    events=[];m=MCPManager(config,Secrets(),lambda e,**d:events.append(e))
    try:
        await m.start()
        assert [r['state'] for r in m.status()]==['connected','connected'],m.status()
        assert all(r['protocol'] for r in m.status())
        catalog=m.catalog();alias=next(a for a,t in catalog.items() if t['server']=='workspace' and t['tool']=='capabilities')
        result=await m.call(alias,{})
        assert not result.get('isError')
        assert 'workspace' in json.dumps(result)
        denied=next(a for a,t in catalog.items() if t['server']=='workspace' and t['tool']=='read_text')
        result=await m.call(denied,{'path':'/etc/passwd'})
        assert result.get('isError') is True
        config.data['servers'][0]['disabled_tools']=['capabilities']
        with pytest.raises(ValueError,match='disabled'):await m.call(alias,{})
        with pytest.raises(Exception):await m.call(denied,{'bad':'argument'})
        await m.connections['workspace'].close()
        with pytest.raises(ValueError):await m.call(denied,{'path':'/etc/passwd'})
    finally: await m.stop()


@pytest.mark.integration
async def test_unavailable_stdio_server_is_reported(config):
    c=Connection({'id':'missing','transport':'stdio','command':'/does/not/exist','args':[]},Secrets(),lambda:None)
    with pytest.raises(ValueError):await c.connect()
    await c.close()


@pytest.mark.integration
@pytest.mark.parametrize('transport,path',[('streamable-http','/mcp'),('sse','/sse')])
async def test_real_http_transports(config,transport,path):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    process=await asyncio.create_subprocess_exec(sys.executable,'-m','clicky.safe_server','--kind','workspace','--transport',transport,'--port',str(port),
        cwd=PROJECT,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
    c=None
    try:
        for _ in range(100):
            try:
                r,w=await asyncio.open_connection('127.0.0.1',port);w.close();await w.wait_closed();break
            except OSError:await asyncio.sleep(.05)
        else: raise AssertionError('Real MCP HTTP server did not start')
        c=Connection({'id':'http','transport':'streamable_http' if transport=='streamable-http' else 'sse','url':f'http://127.0.0.1:{port}'+path},Secrets(),lambda:None)
        await c.connect();assert c.state=='connected';assert c.protocol
        result=await c.call('capabilities',{})
        assert not result.get('isError');assert 'workspace' in json.dumps(result)
    finally:
        if c: await c.close()
        process.terminate()
        try:await asyncio.wait_for(process.wait(),3)
        except asyncio.TimeoutError:process.kill();await process.wait()
