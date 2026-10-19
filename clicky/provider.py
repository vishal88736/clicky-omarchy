"""Async provider contract and OpenAI-compatible local/hosted adapter."""
import abc
import base64
import json
import struct
import zlib
from dataclasses import dataclass,field
import httpx
from .config import endpoint


@dataclass
class Completion:
    text:str=""
    calls:list=field(default_factory=list)
    usage:dict=field(default_factory=dict)


class Provider(abc.ABC):
    @abc.abstractmethod
    async def complete(self,messages,tools,on_delta): ...


class CompatibleProvider(Provider):
    def __init__(self,config,key=""):
        self.config=config.copy();self.base=endpoint(config["base_url"]);self.key=key
    def client(self):
        return httpx.AsyncClient(timeout=httpx.Timeout(float(self.config.get("timeout",90)),connect=5),follow_redirects=False,trust_env=False,
            headers={"Authorization":"Bearer "+self.key} if self.key else {})
    @staticmethod
    def check(r):
        if r.status_code>=300: raise ValueError(f"Provider returned HTTP {r.status_code}; check endpoint, model and credentials")
    async def models(self):
        async with self.client() as c:
            r=await c.get(self.base+"/models");self.check(r)
            return [m["id"] for m in r.json()["data"] if isinstance(m.get("id"),str)]
    async def complete(self,messages,tools,on_delta):
        if not self.config["model"]: raise ValueError("Configure a local endpoint and model in Settings first")
        body={"model":self.config["model"],"messages":messages,"max_tokens":int(self.config["response_tokens"]),"stream":bool(self.config.get("stream"))}
        if tools: body.update(tools=tools,tool_choice="auto")
        result=Completion()
        async with self.client() as c:
            if not body["stream"]:
                r=await c.post(self.base+"/chat/completions",json=body);self.check(r)
                data=r.json();m=data["choices"][0]["message"]
                result.text=m.get("content") or "";result.calls=m.get("tool_calls") or [];result.usage=data.get("usage") or {}
                if not isinstance(result.text,str) or not isinstance(result.calls,list): raise ValueError("Malformed provider response")
                if len(result.text)>1_000_000: raise ValueError("Provider response too large")
                if result.text: on_delta(result.text)
                return result
            async with c.stream("POST",self.base+"/chat/completions",json=body) as r:
                self.check(r);calls={};finished=False
                async for line in r.aiter_lines():
                    if len(line)>2_000_000: raise ValueError("Provider event too large")
                    if not line.startswith("data:"): continue
                    raw=line[5:].strip()
                    if raw=="[DONE]": finished=True;break
                    data=json.loads(raw)
                    if data.get("usage"): result.usage=data["usage"]
                    for choice in data.get("choices",[]):
                        if choice.get("finish_reason"): finished=True
                        delta=choice.get("delta",{})
                        if delta.get("content"):
                            result.text+=delta["content"];on_delta(delta["content"])
                            if len(result.text)>1_000_000: raise ValueError("Provider response too large")
                        for call in delta.get("tool_calls",[]):
                            item=calls.setdefault(call["index"],{"id":"","type":"function","function":{"name":"","arguments":""}})
                            if call.get("id"): item["id"]=call["id"]
                            for key in ["name","arguments"]: item["function"][key]+=call.get("function",{}).get(key,"")
                if not finished: raise ValueError("Provider stream ended without completion marker")
                result.calls=[calls[k] for k in sorted(calls)]
                return result
    async def probe(self,kind):
        cfg=self.config.copy();cfg.update(stream=kind=="stream",response_tokens=128)
        p=CompatibleProvider(cfg,self.key);messages=[{"role":"user","content":"Reply with the word READY."}];tools=[]
        if kind=="tools":
            messages=[{"role":"user","content":"Call clicky_probe with value READY. Do not answer in prose."}]
            tools=[{"type":"function","function":{"name":"clicky_probe","description":"Synthetic test, no action executes.","parameters":{"type":"object","properties":{"value":{"type":"string","enum":["READY"]}},"required":["value"],"additionalProperties":False}}}]
        if kind=="vision":
            def chunk(t,b): return struct.pack('!I',len(b))+t+b+struct.pack('!I',zlib.crc32(t+b)&0xffffffff)
            png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\x00'+b'\x00\x00\xff'*32)*32))+chunk(b'IEND',b'')
            messages=[{"role":"user","content":[{"type":"text","text":"Name the dominant color in this image in one word."},{"type":"image_url","image_url":{"url":"data:image/png;base64,"+base64.b64encode(png).decode()}}]}]
        result=await p.complete(messages,tools,lambda _:None)
        if kind=="tools": valid=any(c.get("function",{}).get("name")=="clicky_probe" and json.loads(c["function"]["arguments"])=={"value":"READY"} for c in result.calls)
        elif kind=="vision": valid="blue" in result.text.lower()
        else: valid="READY" in result.text.upper()
        if not valid: raise ValueError(f"{kind} probe failed; capability remains unverified")
        return {"verified":True,"usage":result.usage}
