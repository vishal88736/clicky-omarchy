"""HTTP protocol fixtures, deliberately not claimed as live model tests."""
import asyncio
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from clicky.config import defaults,Config
from clicky.provider import CompatibleProvider
from clicky.worker import Worker


@pytest.fixture
def compatible_fixture():
    records=[]
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args):pass
        def reply(self,data,status=200):
            body=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def do_GET(self):self.reply({'data':[{'id':'fixture-not-an-llm'}]})
        def do_POST(self):
            req=json.loads(self.rfile.read(int(self.headers['Content-Length'])));records.append(req)
            if req['model']=='http-failure':self.reply({'error':'private provider body'},503);return
            if req['model']=='slow':
                import time
                time.sleep(3)
            messages=req['messages'];tool_result=any(m['role']=='tool' for m in messages)
            if req.get('tools') and not tool_result:
                tool=req['tools'][0]['function'];args={'value':'READY'} if tool['name']=='clicky_probe' else {}
                m={'role':'assistant','content':'','tool_calls':[{'id':'call_fixture','type':'function','function':{'name':tool['name'],'arguments':json.dumps(args)}}]}
            else:
                content='blue' if isinstance(messages[-1]['content'],list) else 'Fixture tool result received' if tool_result else 'READY'
                m={'role':'assistant','content':content}
            if req.get('stream'):
                events=[{'choices':[{'delta':{'content':'REA'},'finish_reason':None}]},{'choices':[{'delta':{'content':'DY'},'finish_reason':'stop'}]}]
                body=(''.join('data: '+json.dumps(e)+'\n\n' for e in events)+'data: [DONE]\n\n').encode()
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            else:self.reply({'choices':[{'message':m}],'usage':{'prompt_tokens':10,'completion_tokens':2}})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    cfg=defaults()['provider'];cfg.update(base_url=f'http://127.0.0.1:{server.server_port}/v1',model='fixture-not-an-llm',key_ref='')
    yield cfg,records
    server.shutdown();server.server_close();thread.join(2)


async def test_fixture_discovery_text_stream_vision_tools_usage(compatible_fixture):
    cfg,records=compatible_fixture;p=CompatibleProvider(cfg)
    assert await p.models()==['fixture-not-an-llm']
    for kind in ['text','stream','vision','tools']:assert (await p.probe(kind))['verified']
    cfg['stream']=True;chunks=[];result=await CompatibleProvider(cfg).complete([{'role':'user','content':'hello'}],[],chunks.append)
    assert chunks==['REA','DY'];assert result.text=='READY'
    cfg['stream']=False;cfg['model']='http-failure'
    with pytest.raises(ValueError,match='503') as e:await CompatibleProvider(cfg).complete([],[],lambda _:None)
    assert 'private provider body' not in str(e)


async def test_fixture_cancellation(compatible_fixture):
    cfg,_=compatible_fixture;cfg['model']='slow'
    task=asyncio.create_task(CompatibleProvider(cfg).complete([{'role':'user','content':'hello'}],[],lambda _:None))
    await asyncio.sleep(.1);task.cancel()
    with pytest.raises(asyncio.CancelledError):await task


@pytest.mark.integration
async def test_worker_fixture_tool_roundtrip_context_restart(compatible_fixture,tmp_path,monkeypatch):
    cfg,records=compatible_fixture
    monkeypatch.setenv('CLICKY_CONFIG_HOME',str(tmp_path/'config'));monkeypatch.setenv('CLICKY_DATA_HOME',str(tmp_path/'data'))
    events=[];worker=None
    def emit(event,**data):
        events.append((event,data))
        if event=='approval':asyncio.get_running_loop().call_soon(worker.approvals.resolve,data['id'],True)
    worker=Worker(emit);worker.config.data['provider']=cfg|{'context_tokens':30000,'verified':{'text':True,'tools':True}}
    # Only the safe capabilities tool is exposed for this fixture's model response.
    worker.config.data['servers'][0]['disabled_tools']=['list_directory','read_text','write_text','git_read']
    worker.config.data['servers'][1]['enabled']=False;worker.config.save()
    cid=worker.cid;old=worker.store.new('Source');wanted=worker.store.add(old,'user','INTENDED_REFERENCE');worker.store.add(old,'assistant','UNSELECTED_PRIVATE_REFERENCE')
    worker.store.select(cid,wanted,True)
    try:
        await worker.mcp.start();key=worker.prepare('question with selected reference');await worker.send(key)
        assert len(records)==2
        assert 'INTENDED_REFERENCE' in json.dumps(records[0])
        assert 'UNSELECTED_PRIVATE_REFERENCE' not in json.dumps(records[0])
        assert records[1]['messages'][-1]['role']=='tool'
        assert any(e=='activity' and v.get('status')=='completed' for e,v in events)
        assert worker.store.messages(cid)[-1]['content']=='Fixture tool result received'
        worker.store.draft(cid,'saved unsent draft')
    finally:await worker.close()
    from clicky.storage import Store
    s=Store(tmp_path/'data');assert s.messages(cid)[-1]['content']=='Fixture tool result received'
    assert next(c for c in s.conversations() if c['id']==cid)['draft']=='saved unsent draft';s.close()
