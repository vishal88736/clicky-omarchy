"""Auditable model/tool loop with immutable approvals and bounded rounds."""
import asyncio
import copy
import json
from jsonschema import Draft202012Validator
from .context import estimate
from .security import redacted


class Agent:
    def __init__(self,store,mcp,approvals,emit): self.store=store;self.mcp=mcp;self.approvals=approvals;self.emit=emit
    async def tool(self,cid,alias,args):
        args=copy.deepcopy(args);catalog=self.mcp.catalog();item=catalog.get(alias)
        if not item: raise ValueError('Tool is disabled or unavailable')
        Draft202012Validator(item['schema']).validate(args)
        label=item['server']+' / '+item['tool']
        self.store.event(cid,'tool',label,'proposed');self.emit('activity',tool=label,status='proposed',arguments=redacted(args))
        reported_read=item.get('annotations',{}).get('read_only_hint',False)
        effect=('Reported read-only operation. Reading may disclose private data.' if reported_read else 'Action: may change files/apps or communicate externally.')
        effect+='\n'+item['definition']['function']['description']+'\nServer annotations are advisory. Approve only this reviewed invocation.'
        if not await self.approvals.request(label,args,redacted(effect)):
            self.store.event(cid,'tool',label,'denied');self.emit('activity',tool=label,status='denied')
            return {'isError':True,'content':[{'type':'text','text':'User denied the action'}]}
        # Recheck configuration after the approval wait, so a disabled tool cannot execute.
        if alias not in self.mcp.catalog(): raise ValueError('Tool was disabled while awaiting approval')
        try:
            result=await self.mcp.call(alias,args)
            state='failed' if result.get('isError') else 'completed'
            self.store.event(cid,'tool',label,state)
            self.emit('activity',tool=label,status=state,result=redacted(result))
            return redacted(result)
        except BaseException:
            self.store.event(cid,'tool',label,'cancelled_or_failed');self.emit('activity',tool=label,status='cancelled_or_failed');raise

    async def run(self,cid,request,provider):
        messages=copy.deepcopy(request['messages']);tools=request['tools'];text=request['user_text']
        self.store.add(cid,'user',redacted(text));self.store.draft(cid,'')
        mid=self.store.add(cid,'assistant','','streaming');answer='';status='complete'
        self.emit('request_started',conversation=cid)
        def delta(chunk):
            nonlocal answer
            answer+=chunk;self.store.update(mid,redacted(answer),'streaming');self.emit('delta',conversation=cid,message=mid,text=chunk)
        try:
            for _ in range(8):
                result=await provider.complete(messages,tools,delta)
                self.emit('usage',usage=result.usage)
                if not result.calls: break
                if len(result.calls)>8: raise ValueError('Too many tool calls in one round')
                messages.append({'role':'assistant','content':result.text or None,'tool_calls':result.calls})
                ids=set()
                for call in result.calls:
                    if not isinstance(call.get('id'),str) or call['id'] in ids: raise ValueError('Malformed tool call ID')
                    ids.add(call['id']);fn=call['function'];args=json.loads(fn['arguments'])
                    if not any(t['function']['name']==fn['name'] for t in tools): raise ValueError('Provider requested a tool outside the reviewed request')
                    try: value=await self.tool(cid,fn['name'],args)
                    except Exception as e: value={'isError':True,'content':[{'type':'text','text':str(e)[:500]}]}
                    messages.append({'role':'tool','tool_call_id':call['id'],'content':json.dumps(value,ensure_ascii=False)})
                if estimate(messages)+estimate(tools)+request['max_tokens']+1024>provider.config['context_tokens']:
                    raise ValueError('Tool results exceed context budget. Start a new request with fewer tools/context.')
            else: raise ValueError('Stopped at the eight-round tool safety limit')
        except asyncio.CancelledError:
            status='cancelled';raise
        except Exception:
            status='error';raise
        finally:
            self.store.update(mid,redacted(answer),status)
