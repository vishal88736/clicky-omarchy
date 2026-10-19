import json
import pytest
from clicky.config import defaults
from clicky.desktop import DesktopBroker


async def test_broker_uses_bounded_lua_without_legacy_dispatch_or_injection(monkeypatch):
    calls=[]
    async def fake(argv,*args):
        calls.append(argv)
        if argv[1]=='clients':return json.dumps([{'address':'0x123','class':'clicky'}])
        if argv[1]=='activewindow':return json.dumps({'address':'0x123','class':'clicky'})
        if argv[1]=='monitors':return json.dumps([{'x':-100,'y':0,'width':1000,'height':1000,'scale':1.25}])
        if argv[1]=='cursorpos':return json.dumps({'x':-50,'y':50})
        return 'ok'
    monkeypatch.setattr('clicky.desktop.command',fake)
    class C:data=defaults()
    b=DesktopBroker(C())
    await b.window('0x123','focus');await b.pointer(-50,50)
    assert any(c[2]=='hl.dsp.focus({ window = "address:0x123" })' for c in calls if c[1]=='dispatch')
    assert any(c[2]=='hl.dsp.cursor.move({ x = -50, y = 50 })' for c in calls if c[1]=='dispatch')
    with pytest.raises(ValueError):await b.window('0x123"; os.execute("bad")','focus')
    with pytest.raises(ValueError):await b.pointer(9999,50)
    with pytest.raises(ValueError):await b.approved_command('arbitrary shell')
    with pytest.raises(ValueError):await b.type_text('0x123','text')
