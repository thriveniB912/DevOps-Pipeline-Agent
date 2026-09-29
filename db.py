from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, ForeignKey, JSON, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from .config import DATABASE_URL


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    service: Mapped[str] = mapped_column(String(80), default="general")
    severity: Mapped[str] = mapped_column(String(10), default="sev3")
    status: Mapped[str] = mapped_column(String(20), default="open")
    memory_assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution = relationship("Resolution", back_populates="incident", uselist=False)
    messages = relationship("ChatMessage", back_populates="incident", order_by="ChatMessage.id")


class Resolution(Base):
    __tablename__ = "resolutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), unique=True)
    root_cause: Mapped[str] = mapped_column(Text)
    fix: Mapped[str] = mapped_column(Text)
    resolved_by: Mapped[str] = mapped_column(String(80), default="on-call")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    incident = relationship("Incident", back_populates="resolution")


class IncidentMemory(Base):
    __tablename__ = "incident_memories"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    service: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    fix: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)
    in_hindsight: Mapped[bool] = mapped_column(Boolean, default=False)
    times_recalled: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    recalled: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    incident = relationship("Incident", back_populates="messages")


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
