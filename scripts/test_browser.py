"""Isolated real-browser test. Never seeds the user's data directory."""
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    env={**os.environ,'PROSPECT_DATA_DIR':tempfile.mkdtemp(prefix='prospect-browser-')}
    def run(args):subprocess.run([sys.executable,*args],cwd=ROOT,env=env,check=True)
    run(['-m','app.manage','migrate'])
    run(['-c',textwrap.dedent("""
    from app.db import Session,Company,Campaign,Job
    from app.domain import CampaignInput
    from app.source_errors import SourceError
    from app.worker import record_failure
    from app.domain import parse_hours,score_company
    with Session() as db:
     c=Company(identity='test:browser',name='Synthetic browser bakery',city='Lausanne',sector='bakery',phone='+41000000000',facts={'source':'https://example.com/fixture','confidence':'synthetic-test','hours':parse_hours('Mo-Fr 09:00-12:00','https://example.com/fixture','2026-10-21T10:00:00+00:00')},audit={})
     db.add(c);db.flush();c.score=score_company(c)
     campaign=Campaign(name='QA Overpass indisponible',config=CampaignInput(name='QA source failure',data_source='osm-overpass').model_dump(),state='running');db.add(campaign);db.flush();job=Job(campaign_id=campaign.id);db.add(job);db.commit();job_id=job.id
    record_failure(job_id,SourceError('Overpass temporairement indisponible (HTTP 502). Données conservées.',status=502,retryable=True,retry_after=300,attempts=3))
    """ )])
    try:
     run(['scripts/launcher.py','start','--no-browser'])
     subprocess.run(['node','tests/browser.cjs'],cwd=ROOT,env=env,check=True)
    finally:run(['scripts/launcher.py','stop'])

if __name__=='__main__':main()
