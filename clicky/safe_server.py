"""Real SDK servers. Only the host's approval broker is allowed to call these."""
import argparse
import asyncio
import json
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from .config import Config
from .desktop import Files,DesktopBroker,command


def build(kind,config):
    server=MCPServer("clicky-"+kind,version="0.1.0",log_level="ERROR")
    files=Files(config.data['roots']);desktop=DesktopBroker(config)
    read=ToolAnnotations(read_only_hint=True,destructive_hint=False,open_world_hint=False)
    @server.tool(annotations=read)
    def capabilities() -> dict:
        """Read the server's limits and permitted filesystem roots. No external data is read."""
        return {"kind":kind,"roots":config.data['roots'],"arbitrary_shell":False,"approval":"host must approve every call"}
    if kind=='workspace':
        @server.tool(annotations=read)
        def list_directory(path:str) -> list[str]:
            """List up to 250 visible names inside an explicitly permitted root; no symlinks."""
            return files.listing(path)
        @server.tool(annotations=read)
        def read_text(path:str) -> str:
            """Read a UTF-8 regular file of at most 32 KiB inside permitted roots. No hidden files."""
            return files.read(path)
        @server.tool()
        def write_text(path:str,text:str) -> dict:
            """WRITE: atomically create or replace a file inside permitted roots. Requires explicit approval."""
            return files.write(path,text)
        @server.tool(annotations=read)
        async def git_read(repository:str,operation:str='status') -> str:
            """Read Git status or diff inside a permitted root; no hooks, external diff, or network."""
            files.listing(repository)
            path=Path(repository).resolve()
            actual=(await command(['git','-C',str(path),'rev-parse','--show-toplevel'],3)).strip()
            if Path(actual)!=path: raise ValueError('Choose the repository root, and explicitly permit it')
            args={'status':['status','--short'],'diff':['diff','--no-ext-diff','--no-textconv','--stat']}
            if operation not in args: raise ValueError('Only status and diff are permitted')
            return await command(['git','-c','core.fsmonitor=false','-C',str(path)]+args[operation],5,32000)
    else:
        @server.tool(annotations=read)
        async def active_window() -> dict:
            """Read active-window metadata, including its title, after explicit approval."""
            return await desktop.active()
        @server.tool(annotations=read)
        async def list_windows() -> list[dict]:
            """Read open-window metadata and addresses after explicit approval."""
            return await desktop.windows()
        @server.tool()
        async def manage_window(address:str,action:str) -> str:
            """Focus or CLOSE one existing window by address. Closing may discard application work."""
            return await desktop.window(address,action)
        @server.tool()
        async def open_url(url:str) -> str:
            """Open an HTTP(S) URL in the user's browser. Navigation can have side effects; approve first."""
            return await desktop.open_url(url)
        @server.tool()
        async def launch_application(application:str) -> str:
            """Open browser, terminal, or files through an explicit application allowlist."""
            return await desktop.launch(application)
        @server.tool()
        async def run_approved_command(name:str) -> str:
            """Run a fixed, administrator-configured argv alias; no arbitrary shell or arguments."""
            return await desktop.approved_command(name)
        @server.tool()
        async def move_pointer(x:int,y:int) -> str:
            """Move pointer inside actual connected monitor geometry; never clicks."""
            return await desktop.pointer(x,y)
        @server.tool()
        async def type_text(address:str,text:str) -> str:
            """Type single-line text only into the currently active, explicitly allowlisted nonterminal window. Disabled by default."""
            return await desktop.type_text(address,text)
    return server


def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['workspace','desktop'],required=True)
    p.add_argument('--transport',choices=['stdio','streamable-http','sse'],default='stdio');p.add_argument('--port',type=int,default=0)
    a=p.parse_args();server=build(a.kind,Config())
    if a.transport=='stdio': server.run()
    elif a.transport=='sse': asyncio.run(server.run_sse_async(host='127.0.0.1',port=a.port))
    else: asyncio.run(server.run_streamable_http_async(host='127.0.0.1',port=a.port))


if __name__=='__main__': main()
