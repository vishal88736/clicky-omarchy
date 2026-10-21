"""Render the real UI with isolated empty history; never capture the desktop."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def main():
    for language,panel,name in [('en','','preview.png'),('en','library','history.png'),('en','toolsDialog','tools.png'),('en','settingsDialog','settings.png')]:
        with tempfile.TemporaryDirectory(prefix='clicky-preview-') as d:
            lang=Path(d)/'language';lang.write_text(language)
            env=os.environ|{'QT_QPA_PLATFORM':'offscreen','QT_QUICK_BACKEND':'software','QT_FORCE_STDERR_LOGGING':'1',
                'CLICKY_DISABLE_TTS':'1','CLICKY_THEME_DIR':d+'/theme','CLICKY_CONFIG_HOME':d+'/config',
                'CLICKY_DATA_HOME':d+'/data','CLICKY_RUNTIME_HOME':d+'/runtime','CLICKY_LANGUAGE_FILE':str(lang)}
            target=ROOT/'artifacts'/name;target.parent.mkdir(exist_ok=True)
            args=[str(ROOT/'build/clicky'),'--smoke',str(target)]
            if panel:args.append(panel)
            result=subprocess.run(args,env=env,capture_output=True,text=True,timeout=20)
            if result.returncode:raise SystemExit('Preview render failed: '+result.stderr[-500:])
            print(target.relative_to(ROOT))


if __name__=='__main__':main()
