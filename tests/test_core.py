import asyncio
import json
import os
from pathlib import Path
import pytest
from clicky.storage import Store
from clicky.context import Context
from clicky.config import defaults,Config,endpoint,provider_key_reference
from clicky.desktop import Files
from clicky.security import Approvals,redacted


def test_history_restart_drafts_and_opt_in_context(tmp_path):
    s=Store(tmp_path);a=s.new('A');mid=s.add(a,'user','explicit reference');s.add(a,'assistant','private unselected answer')
    b=s.new('B');s.draft(b,'unfinished draft');s.add(b,'user','current conversation');s.add(b,'assistant','current answer')
    cfg=defaults()['provider'];ctx=Context(s)
    assert 'explicit reference' not in json.dumps(ctx.assemble(b,'question',cfg))
    s.select(b,mid,True);s.close();s=Store(tmp_path)
    assert next(c for c in s.conversations() if c['id']==b)['draft']=='unfinished draft'
    request=Context(s).assemble(b,'question',cfg)
    assert 'explicit reference' in json.dumps(request)
    assert 'private unselected answer' not in json.dumps(request)
    assert [m['content'] for m in request['messages'][-3:]]==['current conversation','current answer','question']
    s.select(b,mid,False);assert not s.selections(b)
    s.select(b,mid,True);s.clear(a);assert not s.selections(b)
    assert s.db.execute('PRAGMA user_version').fetchone()[0]==1
    s.close()


def test_context_budget_is_explicit_and_whole_turns(tmp_path):
    s=Store(tmp_path);cid=s.new();cfg=defaults()['provider'];cfg['context_tokens']=3000;cfg['response_tokens']=256
    for n in range(8): s.add(cid,'user','x'*350);s.add(cid,'assistant','y'*200)
    req=Context(s).assemble(cid,'latest',cfg)
    assert req['omitted_turns']>0
    roles=[m['role'] for m in req['messages'][1:-1]]
    assert roles==['user','assistant']*(len(roles)//2)
    with pytest.raises(ValueError,match='budget'): Context(s).assemble(cid,'x'*10000,cfg)
    s.close()


def test_private_db_and_interrupted_generation(tmp_path):
    s=Store(tmp_path);c=s.new();mid=s.add(c,'assistant','partial','streaming');s.close();s=Store(tmp_path)
    assert s.message(mid)['status']=='interrupted'
    assert (tmp_path/'history.sqlite3').stat().st_mode & 0o777==0o600
    s.close()


def test_files_reject_escapes_symlinks_hidden_and_devices(tmp_path):
    root=tmp_path/'root';root.mkdir();outside=tmp_path/'outside';outside.write_text('secret')
    f=Files([str(root)]);f.write(str(root/'ok'),'hello');assert f.read(str(root/'ok'))=='hello'
    (root/'link').symlink_to(outside)
    (root/'dirlink').symlink_to(tmp_path,target_is_directory=True)
    (root/'.hidden').write_text('secret')
    for path in [outside,root/'../outside',root/'.hidden',root/'dirlink/outside',root/'link']:
        with pytest.raises((ValueError,OSError)): f.read(str(path))
    with pytest.raises((ValueError,OSError)): f.write(str(root/'link'),'no')
    assert outside.read_text()=='secret'


async def test_one_use_approval_and_cancel():
    events=[];a=Approvals(lambda event,**kw:events.append((event,kw)))
    t=asyncio.create_task(a.request('read',{'path':'/x'},'read'));await asyncio.sleep(0)
    key=events[0][1]['id'];a.resolve('wrong',True);assert not t.done();a.resolve(key,True);assert await t is True
    assert not a.pending;a.resolve(key,True)
    t=asyncio.create_task(a.request('write',{},'write'));await asyncio.sleep(0);a.cancel();assert await t is False


def test_config_endpoint_and_secret_references(tmp_path):
    c=Config(tmp_path);c.provider({'base_url':'http://127.0.0.1:9000/v1','model':'a'})
    c.data['provider']['verified']={'text':True};c.provider({'model':'b'});assert not c.data['provider']['verified']
    for u in ['http://example.org/v1','https://user:pass@example.org/v1','https://x/v1?key=secret']:
        with pytest.raises(ValueError): endpoint(u)
    bad=defaults();bad['servers'][0]['env']={'TOKEN':'secret'}
    with pytest.raises(ValueError):Config.validate(bad)
    assert redacted({'api_key':'secret','text':'Bearer aaaaa'})=={'api_key':'[redacted]','text':'Bearer [redacted]'}


def test_credentials_are_scoped_to_endpoint_and_never_follow_url_changes(tmp_path):
    c=Config(tmp_path);first=c.data['provider']['base_url'];ref=provider_key_reference(first)
    c.data['provider']['key_ref']=ref;c.save()
    c.provider({'model':'same endpoint'});assert c.data['provider']['key_ref']==ref
    c.provider({'base_url':'http://127.0.0.1:9000/v1'});assert c.data['provider']['key_ref']==''
    assert provider_key_reference(first)!=provider_key_reference(c.data['provider']['base_url'])
    assert provider_key_reference(first+'/')==ref
