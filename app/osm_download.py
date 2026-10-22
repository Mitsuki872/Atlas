"""Fixed Geofabrik Switzerland source, TLS + provider checksum, bounded resumable download."""
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import httpx

LATEST='https://download.geofabrik.de/europe/switzerland-latest.osm.pbf'
MAX_BYTES=2_000_000_000
class DatasetInterrupted(RuntimeError):pass

def checked_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname!='download.geofabrik.de' or p.port not in (None,443) or p.username or p.password or p.query or p.fragment or not re.fullmatch(r'/europe/switzerland-(?:latest|\d{6})\.osm\.pbf(?:\.md5)?',p.path):
        raise ValueError('Destination de téléchargement non autorisée')
    return url

def request(client,method,url,**kw):
    for _ in range(4):
        checked_url(url);r=client.request(method,url,**kw)
        if r.status_code in (301,302,303,307,308):
            target=urljoin(url,r.headers.get('location',''));r.close();url=checked_url(target);continue
        r.raise_for_status();return r
    raise ValueError('Trop de redirections Geofabrik')

def atomic_json(path,payload):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8') as output:
        json.dump(payload,output,ensure_ascii=False,indent=2);output.flush();os.fsync(output.fileno())
    os.replace(temp,path)

def digest_file(path,algorithm,cancel=lambda:False):
    digest=hashlib.new(algorithm)
    with path.open('rb') as f:
        while chunk:=f.read(4*1024*1024):
            if cancel():raise DatasetInterrupted('Préparation interrompue, fichiers partiels conservés.')
            digest.update(chunk)
    return digest.hexdigest()

def download_switzerland(folder,progress=lambda **kw:None,cancel=lambda:False,client=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    own=client is None;client=client or httpx.Client(timeout=httpx.Timeout(30,connect=20),follow_redirects=False,headers={'User-Agent':'ProspectEngine/1.2 (explicit Switzerland extract download)','Accept-Encoding':'identity'})
    try:
        if cancel():raise DatasetInterrupted('Préparation interrompue avant téléchargement.')
        progress(stage='checking_source',message='Vérification du fichier suisse et de sa taille…')
        head=request(client,'HEAD',LATEST)
        url=str(head.url);size=int(head.headers.get('content-length','0'))
        if not 0<size<=MAX_BYTES:raise ValueError('Taille du fichier absente ou supérieure à la limite de 2 Go')
        if cancel():raise DatasetInterrupted('Préparation interrompue.')
        with client.stream('GET',checked_url(url+'.md5'),headers={'Accept-Encoding':'identity'}) as response:
            response.raise_for_status();body=b''
            for chunk in response.iter_bytes():
                body+=chunk
                if len(body)>4096:raise ValueError('Fichier d’empreinte trop volumineux')
            checksum=body.decode('ascii').strip()
        match=re.fullmatch(r'([a-fA-F0-9]{32})\s+\*?(\S+)',checksum)
        if not match or match[2]!=urlsplit(url).path.rsplit('/',1)[-1]:raise ValueError('Empreinte du fournisseur absente ou incohérente')
        expected=match[1].lower();target=folder/f'switzerland-{expected}.osm.pbf';part=target.with_suffix(target.suffix+'.part')
        meta={'url':url,'size':size,'provider_md5':expected,'last_modified':head.headers.get('last-modified'),'etag':head.headers.get('etag'),'attribution':'© OpenStreetMap contributors — ODbL ; extrait Geofabrik','license':'https://www.openstreetmap.org/copyright'}
        if target.exists():
            progress(stage='verifying',message='Vérification de la copie déjà téléchargée…',bytes=target.stat().st_size,total_bytes=size)
            if target.stat().st_size==size and digest_file(target,'md5',cancel)==expected:
                return target,{**meta,'sha256':digest_file(target,'sha256',cancel),'reused_download':True}
            # Quarantine only our own generated cache, preserving bytes for diagnosis.
            os.replace(target,target.with_name(target.name+'.corrupt-'+str(__import__('time').time_ns())))
        start=part.stat().st_size if part.exists() else 0
        if start>size:raise ValueError('Fichier partiel trop long ; téléchargement suspendu, fichier conservé.')
        required=max(0,size-start)+1_000_000_000
        if shutil.disk_usage(folder).free<required:raise ValueError('Espace disque insuffisant pour le téléchargement et l’index local.')
        if start<size:
            if cancel():raise DatasetInterrupted('Téléchargement interrompu.')
            headers={'Accept-Encoding':'identity',**({'Range':f'bytes={start}-'} if start else {})}
            with client.stream('GET',checked_url(url),headers=headers) as response:
                response.raise_for_status()
                if response.status_code==206:
                    expected_range=f'bytes {start}-'
                    if not response.headers.get('content-range','').startswith(expected_range) or not response.headers['content-range'].endswith('/'+str(size)):raise ValueError('Reprise HTTP incohérente ; aucune donnée ajoutée au fichier partiel.')
                elif response.status_code==200:start=0
                else:raise ValueError('Réponse inattendue pendant le téléchargement')
                with part.open('ab' if start else 'wb') as output:
                    downloaded=start
                    for chunk in response.iter_bytes(chunk_size=1024*1024):
                        if cancel():raise DatasetInterrupted('Téléchargement interrompu, reprise disponible.')
                        if downloaded+len(chunk)>size:raise ValueError('Téléchargement plus volumineux que prévu')
                        output.write(chunk);downloaded+=len(chunk)
                        progress(stage='downloading',message='Téléchargement de l’extrait suisse…',bytes=downloaded,total_bytes=size)
                    output.flush();os.fsync(output.fileno())
        if not part.exists() or part.stat().st_size!=size:raise ValueError('Téléchargement incomplet ; le fichier partiel sera réutilisé au prochain essai.')
        progress(stage='verifying',message='Contrôle d’intégrité du téléchargement…',bytes=size,total_bytes=size)
        if digest_file(part,'md5',cancel)!=expected:
            os.replace(part,part.with_name(part.name+'.corrupt-'+str(__import__('time').time_ns())))
            raise ValueError('Le contrôle d’intégrité Geofabrik échoue. Fichier écarté et conservé, jamais importé. Relancez la préparation pour retélécharger une copie saine.')
        sha=digest_file(part,'sha256',cancel);os.replace(part,target)
        meta={**meta,'sha256':sha,'reused_download':False};atomic_json(target.with_suffix(target.suffix+'.json'),meta)
        return target,meta
    finally:
        if own:client.close()
