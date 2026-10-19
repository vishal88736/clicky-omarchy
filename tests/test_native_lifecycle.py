"""A visible close-to-hide window must still obey explicit stop and SIGTERM."""
import os
import signal
import subprocess
import time
from pathlib import Path
import pytest
from clicky.config import PROJECT


@pytest.mark.skipif(not (PROJECT/'build/clicky').exists(),reason='Native binary is not built; run bin/build first')
@pytest.mark.parametrize('method',['ipc','sigterm'])
def test_native_visible_clean_shutdown(tmp_path,method):
    env=os.environ|{'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software','CLICKY_DISABLE_TTS':'1',
        'CLICKY_CONFIG_HOME':str(tmp_path/'config'),'CLICKY_DATA_HOME':str(tmp_path/'data'),'CLICKY_RUNTIME_HOME':str(tmp_path/'runtime')}
    p=subprocess.Popen([str(PROJECT/'build/clicky'),'open'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if (tmp_path/'runtime/control').exists():break
            assert p.poll() is None;time.sleep(.05)
        time.sleep(.3)
        if method=='ipc':subprocess.run([str(PROJECT/'build/clicky'),'stop'],env=env,check=True,timeout=5)
        else:p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=7)==0
    finally:
        if p.poll() is None:p.kill();p.wait(timeout=3)
