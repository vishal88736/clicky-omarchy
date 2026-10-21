"""Deterministic HTTP wire fixture for native UI tests. This is not an LLM."""
import json
import time
from http.server import BaseHTTPRequestHandler,HTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert request['model']=='fixture-not-an-llm'
        chunks=['Native UI ', 'protocol fixture reply']
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        for chunk in chunks:
            event={'choices':[{'delta':{'content':chunk},'finish_reason':None}]}
            self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode());self.wfile.flush();time.sleep(.08)
        self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()


server=HTTPServer(('127.0.0.1',0),Handler)
print(json.dumps({'port':server.server_port}),flush=True)
server.serve_forever()
