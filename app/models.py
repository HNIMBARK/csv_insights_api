from datetime import datetime
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text

from app.database import Base


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)


class AnalysisDB(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    stored_file_name = Column(String, nullable=False, unique=True)
    status = Column(Enum(AnalysisStatus), nullable=False, default=AnalysisStatus.pending)
    file_size = Column(Integer, nullable=False)
    rows_count = Column(Integer, nullable=True)
    columns_count = Column(Integer, nullable=True)
    columns = Column(JSON, nullable=True)
    stats_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
