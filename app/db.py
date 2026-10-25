import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, event, String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATA = Path(os.environ.get('PROSPECT_DATA_DIR', Path(__file__).resolve().parents[1] / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DATA / "prospect.sqlite"}', connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def configure(conn, record):
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
Session = sessionmaker(engine, expire_on_commit=False)
def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
class Base(DeclarativeBase): pass
class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(30), default='draft', index=True)
    progress: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)
class Company(Base):
    __tablename__ = 'companies'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    identity: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    city: Mapped[str] = mapped_column(String(200), default='', index=True)
    sector: Mapped[str] = mapped_column(String(100), default='')
    phone: Mapped[str] = mapped_column(String(100), default='')
    email: Mapped[str] = mapped_column(String(254), default='', index=True)
    canton: Mapped[str] = mapped_column(String(100), default='', index=True)
    contacts: Mapped[list] = mapped_column(JSON, default=list)
    quality_score: Mapped[dict] = mapped_column(JSON, default=dict)
    website: Mapped[str] = mapped_column(String(2000), default='')
    status: Mapped[str] = mapped_column(String(50), default='À contacter', index=True)
    suppressed: Mapped[int] = mapped_column(Integer, default=0)
    facts: Mapped[dict] = mapped_column(JSON, default=dict)
    audit: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[dict] = mapped_column(JSON, default=dict)
    qualification: Mapped[dict] = mapped_column(JSON, default=dict)
    identification: Mapped[dict] = mapped_column(JSON, default=dict)
    manual_fields: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[str] = mapped_column(String, default=now)
    verified_at: Mapped[str] = mapped_column(String, default=now)
class Membership(Base):
    __tablename__ = 'memberships'
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id'), primary_key=True)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), primary_key=True)
class Activity(Base):
    __tablename__ = 'activities'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text, default='')
    outcome: Mapped[str] = mapped_column(String(100), default='')
    due_at: Mapped[str | None] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[str] = mapped_column(String, default=now)
class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey('campaigns.id'), index=True)
    state: Mapped[str] = mapped_column(String(30), default='queued', index=True)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    records: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=now)
class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
class PlanningExport(Base):
    __tablename__ = 'planning_exports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String, default='Export créé')
    created_at: Mapped[str] = mapped_column(String, default=now)
class Log(Base):
    __tablename__ = 'logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    component: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=now)
def serialize(obj): return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

class SourceRecord(Base):
    __tablename__ = 'source_records'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'), index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey('campaigns.id'), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    collected_at: Mapped[str] = mapped_column(String, default=now)


class DatasetJob(Base):
    __tablename__='dataset_jobs'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    state: Mapped[str] = mapped_column(String(30),default='queued',index=True)
    progress: Mapped[dict] = mapped_column(JSON,default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String,default=now)
    updated_at: Mapped[str] = mapped_column(String,default=now)

class AuditRun(Base):
    __tablename__='audit_runs'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'),index=True)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey('campaigns.id'))
    mode: Mapped[str] = mapped_column(String,default='QUICK')
    status: Mapped[str] = mapped_column(String,default='completed')
    rubric_version: Mapped[str] = mapped_column(String)
    fingerprint: Mapped[str] = mapped_column(String,index=True)
    config: Mapped[dict] = mapped_column(JSON)
    context: Mapped[dict] = mapped_column(JSON,default=dict)
    input: Mapped[dict] = mapped_column(JSON,default=dict)
    result: Mapped[dict] = mapped_column(JSON,default=dict)
    stages: Mapped[list] = mapped_column(JSON,default=list)
    tool_versions: Mapped[dict] = mapped_column(JSON,default=dict)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(String,default=now)
    finished_at: Mapped[str | None] = mapped_column(String)
class CriterionResult(Base):
    __tablename__='criterion_results'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    audit_id: Mapped[str] = mapped_column(ForeignKey('audit_runs.id'),index=True)
    code: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
class AuditEvidence(Base):
    __tablename__='audit_evidence'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    audit_id: Mapped[str] = mapped_column(ForeignKey('audit_runs.id'),index=True)
    reference: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
class ScoreSnapshot(Base):
    __tablename__='score_snapshots'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    audit_id: Mapped[str] = mapped_column(ForeignKey('audit_runs.id'),index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[str] = mapped_column(String,default=now)
class Opportunity(Base):
    __tablename__='audit_opportunities'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    audit_id: Mapped[str] = mapped_column(ForeignKey('audit_runs.id'),index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String,default='REVIEW_REQUIRED')
class OutreachSuppression(Base):
    __tablename__='outreach_suppressions'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'),index=True)
    reason: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String,default=now)
    expires_at: Mapped[str | None] = mapped_column(String)

class WebsiteJob(Base):
    __tablename__='website_jobs'
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=uid)
    company_id: Mapped[str] = mapped_column(ForeignKey('companies.id'),index=True)
    state: Mapped[str] = mapped_column(String(30),default='queued',index=True)
    config: Mapped[dict] = mapped_column(JSON,default=dict)
    result: Mapped[dict] = mapped_column(JSON,default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String,default=now)
    updated_at: Mapped[str] = mapped_column(String,default=now)
