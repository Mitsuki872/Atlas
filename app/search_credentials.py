"""Dedicated local env file; never included in SQLite, exports, logs or source ZIP."""
import json
import os
import re
from app.db import DATA
FILE=DATA/'search-provider.env'
def search_key():
    if FILE.is_file():
        text=FILE.read_text(encoding='utf-8').strip()
        if text.startswith('BRAVE_SEARCH_API_KEY='):
            try:
                value=json.loads(text.split('=',1)[1]);return value if isinstance(value,str) else ''
            except ValueError:return ''
    return os.environ.get('BRAVE_SEARCH_API_KEY','')
def validate_search_key(value):
    if not re.fullmatch(r'[A-Za-z0-9_.+/=\-]{10,256}',value):raise ValueError('Format de clé non valide')
def save_search_key(value):
    validate_search_key(value)
    path=FILE.with_suffix('.tmp')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        f.write('BRAVE_SEARCH_API_KEY='+json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(path,FILE)
    try:os.chmod(FILE,0o600)
    except OSError:pass
