import os
import shutil
import sys
from pathlib import Path
from django.conf import settings

def command(name):
    configured=getattr(settings,name.upper()+'_COMMAND','')
    if configured: return [configured]
    if name=='ocrmypdf':
        found=shutil.which(name)
        return [found] if found else [sys.executable,'-m','ocrmypdf']
    for base in [settings.BASE_DIR/'tools',settings.BASE_DIR.parent.parent/'work'/'tools']:
        if base.exists():
            candidates=list(base.glob('**/'+name+('.exe' if os.name=='nt' else '')))
            if candidates: return [str(candidates[0])]
    found=shutil.which(name)
    return [found or name]

def environment():
    env=os.environ.copy()
    tesseract=Path(command('tesseract')[0])
    if tesseract.is_file():
        env['PATH']=str(tesseract.parent)+os.pathsep+env.get('PATH','')
        data=tesseract.parent/'tessdata'
        if data.is_dir(): env.setdefault('TESSDATA_PREFIX',str(data))
    return env
