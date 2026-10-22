"""Preparation jobs live in the CRM DB; the extract/index itself is separate."""
import time
from sqlalchemy import select
from app.db import DATA,Session,DatasetJob,Setting,serialize,now
from app.osm_download import download_switzerland,DatasetInterrupted
from app.osm_index import build_index
from app.osm_local import manifest,DatasetUnavailable

FOLDER=DATA/'osm'
def dataset_status():
    error=None
    try:ready=manifest(FOLDER)
    except DatasetUnavailable as exc:ready=None;error=str(exc)
    with Session() as db:job=db.scalar(select(DatasetJob).order_by(DatasetJob.created_at.desc()));current_job=serialize(job) if job else None
    return {'ready':bool(ready),'dataset':ready,'job':current_job,'error':error,'license':'https://www.openstreetmap.org/copyright','provider':'https://download.geofabrik.de/europe/switzerland.html','disk_recommendation_gb':4}

def run_dataset_job(id,stop_event):
    last=[0.0];cancel_cache=[False]
    def cancelled():
        if stop_event.is_set():return True
        if time.monotonic()-last[0]>.5:
            with Session() as db:
                job=db.get(DatasetJob,id);cancel_cache[0]=not job or job.state=='cancelled'
            last[0]=time.monotonic()
        return cancel_cache[0]
    last_progress=[0.0]
    def progress(**value):
        if time.monotonic()-last_progress[0]<1 and value.get('stage') not in ('ready','verifying'):return
        with Session() as db:
            job=db.get(DatasetJob,id)
            if job and job.state!='cancelled':job.progress=value;job.updated_at=now()
            db.merge(Setting(key='worker_heartbeat',value={'at':now()}));db.commit()
        last_progress[0]=time.monotonic()
    with Session() as db:
        job=db.get(DatasetJob,id)
        if not job or job.state=='cancelled':return
        job.state='running';job.error=None;job.updated_at=now();db.commit()
    try:
        path,meta=download_switzerland(FOLDER,progress,cancelled)
        if cancelled():raise DatasetInterrupted('Préparation interrompue.')
        import shutil
        if shutil.disk_usage(FOLDER).free<3_000_000_000:raise ValueError('Au moins 3 Go libres sont requis pour l’indexation et son cache temporaire.')
        result=build_index(path,meta,FOLDER,progress,cancelled)
        with Session() as db:
            job=db.get(DatasetJob,id)
            if job.state!='cancelled':job.state='completed';job.progress={'stage':'ready','message':'Annuaire local prêt.','businesses':result['businesses'],'snapshot_at':result['snapshot_at']};job.updated_at=now();db.commit()
    except DatasetInterrupted as exc:
        with Session() as db:
            job=db.get(DatasetJob,id)
            if job.state!='cancelled':job.state='queued' if stop_event.is_set() else 'cancelled'
            job.error=str(exc);job.updated_at=now();db.commit()
    except Exception as exc:
        with Session() as db:
            job=db.get(DatasetJob,id)
            if job.state!='cancelled':job.state='failed';job.error=f'{type(exc).__name__}: {exc}'
            job.updated_at=now();db.commit()
