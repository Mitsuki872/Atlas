import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from app.db import DATA

def backup_database():
    folder=DATA/'backups';folder.mkdir(exist_ok=True)
    target=folder/('prospect-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite')
    with sqlite3.connect(DATA/'prospect.sqlite') as source,sqlite3.connect(target) as dest:source.backup(dest)
    return target

def migrate():
    if (DATA/'prospect.sqlite').exists():backup_database()
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(Path(__file__).resolve().parents[1]/'alembic.ini')),'head')
    # Explicitly retired integration; no provider account or remote key is touched.
    (DATA/'search-provider.env').unlink(missing_ok=True)
    (Path(__file__).parent/'search_credentials.py').unlink(missing_ok=True)
    for compiled in (Path(__file__).parent/'__pycache__').glob('search_credentials.*.pyc'):compiled.unlink(missing_ok=True)

def restore(path):
    # Called only by offline CLI, never by an API upload.
    import socket
    for port in (8765,8766):
        s=socket.socket()
        if __import__('os').name!='nt':s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:s.bind(('127.0.0.1',port))
        except OSError:raise RuntimeError('Arrêtez le backend et le worker avant la restauration.')
        finally:s.close()
    candidate=Path(path).resolve()
    if not candidate.is_file():raise ValueError('Sauvegarde introuvable')
    with sqlite3.connect(f'file:{candidate.as_posix()}?mode=ro',uri=True) as source:
        if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Sauvegarde corrompue')
        tables={x[0] for x in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'companies','campaigns','alembic_version'}<=tables:raise ValueError('Format de sauvegarde incompatible')
        backup_database()
        with sqlite3.connect(DATA/'prospect.sqlite') as dest:source.backup(dest)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['migrate','backup','restore']);p.add_argument('path',nargs='?');p.add_argument('--confirm',action='store_true');args=p.parse_args()
    if args.action=='migrate':migrate()
    elif args.action=='backup':print(backup_database())
    else:
        if not args.path or not args.confirm:p.error('restore requiert un fichier et --confirm ; une sauvegarde préalable est conservée')
        restore(args.path);print('Restauration terminée.')
if __name__=='__main__':main()
