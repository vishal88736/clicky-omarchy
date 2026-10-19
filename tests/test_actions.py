"""Real MCP writes must remain behind one-use approvals."""
import asyncio
import pytest
from clicky.worker import Worker


@pytest.mark.integration
async def test_real_write_denied_approved_and_disabled_while_pending(tmp_path,monkeypatch):
    monkeypatch.setenv('CLICKY_CONFIG_HOME',str(tmp_path/'config'));monkeypatch.setenv('CLICKY_DATA_HOME',str(tmp_path/'data'))
    events=[];worker=Worker(lambda event,**data:events.append((event,data)))
    worker.config.data['roots']=[str(tmp_path)];worker.config.data['servers'][1]['enabled']=False;worker.config.save()
    target=tmp_path/'original.txt';target.write_text('original')
    async def proposal(value):
        events.clear();task=asyncio.create_task(worker.direct_tool('workspace','write_text',{'path':str(target),'text':value}))
        for _ in range(100):
            if any(e=='approval' for e,d in events):break
            await asyncio.sleep(.01)
        else:raise AssertionError('No approval was shown')
        key=next(d['id'] for e,d in events if e=='approval');return task,key
    try:
        await worker.mcp.start()
        task,key=await proposal('denied write');worker.approvals.resolve(key,False);await task
        assert target.read_text()=='original'
        task,key=await proposal('approved write');worker.approvals.resolve(key,True);await task
        assert target.read_text()=='approved write'
        task,key=await proposal('disabled write');worker.config.data['servers'][0]['disabled_tools']=['write_text'];worker.approvals.resolve(key,True)
        with pytest.raises(ValueError,match='disabled'):await task
        assert target.read_text()=='approved write'
    finally:await worker.close()


@pytest.mark.integration
async def test_cancellation_reaps_pending_approval(tmp_path,monkeypatch):
    monkeypatch.setenv('CLICKY_CONFIG_HOME',str(tmp_path/'config'));monkeypatch.setenv('CLICKY_DATA_HOME',str(tmp_path/'data'))
    events=[];worker=Worker(lambda e,**v:events.append((e,v)))
    try:
        await worker.mcp.start()
        task=worker.spawn(worker.direct_tool('workspace','capabilities',{}))
        for _ in range(100):
            if worker.approvals.pending:break
            await asyncio.sleep(.01)
        assert worker.approvals.pending
        await worker.cancel();assert task.done();assert not worker.approvals.pending;assert worker.active is None
    finally:await worker.close()
