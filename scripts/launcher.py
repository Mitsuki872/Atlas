"""Portable local process supervisor. Only manages exact processes it started."""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
import psutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.db import DATA
RUNTIME=DATA/'runtime.json'

def processes():
    if not RUNTIME.exists():return []
    result=[]
    for entry in json.loads(RUNTIME.read_text()):
        try:
            p=psutil.Process(entry['pid'])
            if p.status()!=psutil.STATUS_ZOMBIE and abs(p.create_time()-entry['created'])<.1 and p.cmdline()==entry['command']:result.append(p)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return result

def stop():
    procs=processes()
    for p in procs:p.terminate()
    deadline=time.monotonic()+45
    while processes() and time.monotonic()<deadline:time.sleep(.2)
    alive=processes()
    if alive:raise RuntimeError('Arrêt en cours ou bloqué. Réessayez ; aucun processus tué de force pour protéger la base.')
    RUNTIME.unlink(missing_ok=True)
    print('Services arrêtés. Données conservées.')

def start(open_browser=True):
    if processes():raise RuntimeError('Application déjà démarrée. Utilisez Stop avant un nouveau démarrage.')
    # Refuse to start over unrelated listeners.
    import socket
    for port in (8765,8766):
        with socket.socket() as s:
            if os.name!='nt':s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try:s.bind(('127.0.0.1',port))
            except OSError:raise RuntimeError(f'Le port {port} est utilisé. Lancez Diagnose.bat.')
    subprocess.run([sys.executable,'-m','app.manage','migrate'],cwd=ROOT,check=True)
    DATA.mkdir(exist_ok=True)
    entries=[]
    try:
        for module,args in [('app.worker',[]),('uvicorn',['app.main:app','--host','127.0.0.1','--port','8765'])]:
            command=[sys.executable,'-m',module,*args]
            log=open(DATA/(module+'.log'),'ab')
            kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
            try:p=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=log,stdin=subprocess.DEVNULL,**kwargs)
            finally:log.close()
            entries.append({'pid':p.pid,'created':psutil.Process(p.pid).create_time(),'command':command})
            RUNTIME.write_text(json.dumps(entries))
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(45):
            try:
                with opener.open('http://127.0.0.1:8765/api/diagnostics',timeout=2) as response:d=json.load(response)
                if d['backend']=='ok' and d['database']=='ok' and d['worker']=='ok':break
            except (OSError,ValueError):pass
            if len(processes())!=2:raise RuntimeError('Un service a quitté. Consultez les journaux data/*.log.')
            time.sleep(1)
        else:raise RuntimeError('Démarrage non confirmé. Consultez Diagnose.bat et les journaux.')
        print('Prospect Engine démarré. Services et base vérifiés.')
        if open_browser:webbrowser.open('http://127.0.0.1:8765')
    except Exception:
        stop();raise

def diagnose():
    print('Python:',sys.version.split()[0]);print('Données:',DATA)
    print('Processus supervisés:',[p.pid for p in processes()])
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8765/api/diagnostics',timeout=5) as response:print(json.dumps(json.load(response),ensure_ascii=False,indent=2))
    except OSError as exc:print('Backend non accessible:',exc)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop','diagnose']);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    if args.action=='start':start(not args.no_browser)
    elif args.action=='stop':stop()
    else:diagnose()
if __name__=='__main__':
    try:main()
    except Exception as exc:print('ERREUR:',exc,file=sys.stderr);sys.exit(1)
