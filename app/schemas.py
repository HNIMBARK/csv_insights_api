from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models import AnalysisStatus


class LoginData(BaseModel):
    username: str


class User(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class AnalysisListItem(BaseModel):
    id: int
    file_name: str
    status: AnalysisStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(BaseModel):
    id: int
    file_name: str
    status: AnalysisStatus
    file_size: int
    rows_count: int | None
    columns_count: int | None
    columns: list[str] | None
    stats_summary: dict[str, Any] | None
    created_at: datetime
    finished_at: datetime | None
    error_message: str | None
    owner_id: int

    model_config = {"from_attributes": True}


class StatsSummary(BaseModel):
    total_files: int
    total_rows_processed: int
