import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import ROOT

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class Institution(Base):
    __tablename__ = 'institutions'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    year: Mapped[str] = mapped_column(String)
    fields: Mapped[list] = mapped_column(JSON)
    logo: Mapped[str | None] = mapped_column(String, nullable=True)
    updated: Mapped[str] = mapped_column(String, default=now)
class Student(Base):
    __tablename__ = 'students'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'))
    data: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default='draft')
    photo_id: Mapped[str | None] = mapped_column(String, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated: Mapped[str] = mapped_column(String, default=now)
class Capture(Base):
    __tablename__ = 'captures'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('students.id'))
    state: Mapped[str] = mapped_column(String)
    original: Mapped[str | None] = mapped_column(String, nullable=True)
    approved: Mapped[str | None] = mapped_column(String, nullable=True)
    digest: Mapped[str | None] = mapped_column(String, nullable=True)
    created: Mapped[str] = mapped_column(String, default=now)
class Template(Base):
    __tablename__ = 'templates'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    institution_id: Mapped[str] = mapped_column(ForeignKey('institutions.id'))
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    mapping: Mapped[dict] = mapped_column(JSON)
    settings: Mapped[dict] = mapped_column(JSON)
class Job(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str] = mapped_column(String, default='generate')
    state: Mapped[str] = mapped_column(String, default='queued')
    payload: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[str] = mapped_column(String, default=now)
    updated: Mapped[str] = mapped_column(String, default=now)
class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    action: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    created: Mapped[str] = mapped_column(String, default=now)
class Setting(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)

engine = create_engine('sqlite:///' + str(ROOT / 'database/studio.db'), connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def pragmas(conn, _):
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=30000')
Session = sessionmaker(engine, expire_on_commit=False)
def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
def audit(db, action, entity): db.add(Audit(action=action, entity_id=entity))
