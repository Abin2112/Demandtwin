from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .config import DATABASE_URL


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    """SQLite returns naive timestamps even though records are written in UTC."""
    if value is None:
        return None
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware.astimezone(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(String(20))


class Login(Record, Base):
    __tablename__ = "logins"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    expires: Mapped[int]


class Project(Record, Base):
    __tablename__ = "projects"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str]


class ProjectMember(Record, Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class Product(Record, Base):
    __tablename__ = "products"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    attributes: Mapped[dict] = mapped_column(JSON)


class Experiment(Record, Base):
    __tablename__ = "experiments"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    synthetic: Mapped[bool] = mapped_column(Boolean)
    seeded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    protocol: Mapped[str | None]
    designs: Mapped[list] = mapped_column(JSON)
    policy: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")


class Participant(Record, Base):
    __tablename__ = "participants"
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    segment: Mapped[str] = mapped_column(String(30))
    consent_version: Mapped[str] = mapped_column(String(30))
    assignment: Mapped[list] = mapped_column(JSON)
    assignment_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Response(Record, Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("participant_id", "task"),)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), index=True)
    task: Mapped[int] = mapped_column(Integer)
    chosen: Mapped[int] = mapped_column(Integer)


class ModelRun(Record, Base):
    __tablename__ = "model_runs"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16))
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    artifact: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim: Mapped[str | None] = mapped_column(String(36))


class ProductImage(Base):
    __tablename__ = "product_images"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)


class Notification(Record, Base):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(250))
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class Simulation(Record, Base):
    __tablename__ = "simulations"
    model_id: Mapped[str] = mapped_column(ForeignKey("model_runs.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    inputs: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)


class Design(Record, Base):
    __tablename__ = "design_history"
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    result: Mapped[dict] = mapped_column(JSON)


class Report(Record, Base):
    __tablename__ = "reports"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    simulation_id: Mapped[str] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"), index=True)


class Audit(Record, Base):
    __tablename__ = "audit"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(36))


engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"timeout": 30} if DATABASE_URL.startswith("sqlite") else {})
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")


def session():
    with Session(engine) as db:
        yield db
