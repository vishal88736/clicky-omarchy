"""Bounded local recording and isolated Voxtype transcription."""
import asyncio
import contextlib
import os
import signal
from pathlib import Path
from .desktop import command


class Voice:
    def __init__(self,directory,emit): self.directory=directory;self.emit=emit;self.process=None;self.timer=None;self.path=directory/'recording.wav'
    async def start(self):
        if self.process: raise ValueError('Recording is already active')
        self.path.unlink(missing_ok=True)
        self.process=await asyncio.create_subprocess_exec('pw-record','--rate','16000','--channels','1','--format','s16',str(self.path),
            stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,start_new_session=True)
        await asyncio.sleep(.15)
        if self.process.returncode is not None:
            self.process=None;raise ValueError('Microphone recording failed. Check PipeWire and the default input device.')
        self.emit('voice',state='recording',backend='Local PipeWire → Voxtype Whisper base.en')
        self.timer=asyncio.create_task(self.limit())
    async def limit(self):
        await asyncio.sleep(60)
        await self.cancel()
        self.emit('error',message='Recording cancelled after the 60 second limit')
    async def end(self):
        if self.timer and self.timer is not asyncio.current_task(): self.timer.cancel()
        self.timer=None
        if self.process:
            p=self.process;self.process=None
            with contextlib.suppress(ProcessLookupError): os.killpg(p.pid,signal.SIGINT)
            try: await asyncio.wait_for(p.wait(),2)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError): os.killpg(p.pid,signal.SIGKILL)
                await p.wait()
    async def stop(self):
        if not self.process: raise ValueError('No active recording')
        await self.end();self.emit('voice',state='transcribing',backend='Local Voxtype')
        try:
            if not self.path.exists() or self.path.stat().st_size<48: raise ValueError('No microphone audio was captured')
            self.path.chmod(0o600)
            text=(await command(['voxtype','-q','--engine','whisper','--whisper-mode','local','--threads','4','transcribe',str(self.path)],90,16000)).strip()
            if not text: raise ValueError('No speech detected')
            self.emit('transcript',text=text)
        finally: self.path.unlink(missing_ok=True);self.emit('voice',state='idle',backend='Local Voxtype')
    async def cancel(self):
        await self.end();self.path.unlink(missing_ok=True);self.emit('voice',state='idle',backend='Local Voxtype')
