from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy import func

from app.database import SessionLocal
from app.models import AnalysisDB, AnalysisStatus

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def save_uploaded_csv(file: UploadFile) -> tuple[str, str, int]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    stored_file_name = f"{uuid4().hex}_{file.filename}"
    target_path = UPLOAD_DIR / stored_file_name

    content = file.file.read()
    file_size = len(content)
    with open(target_path, "wb") as output_file:
        output_file.write(content)

    return file.filename, stored_file_name, file_size


def _build_stats_summary(df: pd.DataFrame) -> dict:
    summary: dict[str, dict] = {}
    numeric_columns = set(df.select_dtypes(include="number").columns)

    for column in df.columns:
        column_info: dict = {"type": str(df[column].dtype)}

        if column in numeric_columns:
            described = df[column].describe().to_dict()
            clean_describe = {}
            for key, value in described.items():
                clean_describe[str(key)] = None if pd.isna(value) else float(value)
            column_info["describe"] = clean_describe

        summary[str(column)] = column_info

    return summary


def process_analysis(analysis_id: int) -> None:
    db = SessionLocal()
    try:
        analysis = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if analysis is None:
            return

        analysis.status = AnalysisStatus.running
        db.commit()

        file_path = UPLOAD_DIR / analysis.stored_file_name
        df = pd.read_csv(file_path)

        analysis.rows_count = int(df.shape[0])
        analysis.columns_count = int(df.shape[1])
        analysis.columns = [str(column) for column in df.columns.tolist()]
        analysis.stats_summary = _build_stats_summary(df)
        analysis.status = AnalysisStatus.completed
        analysis.error_message = None
        analysis.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:
        analysis = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
        if analysis is not None:
            analysis.status = AnalysisStatus.failed
            analysis.error_message = str(exc)
            analysis.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def compute_global_stats(db) -> dict[str, int]:
    total_files = db.query(func.count(AnalysisDB.id)).scalar() or 0
    total_rows = (
        db.query(func.coalesce(func.sum(AnalysisDB.rows_count), 0))
        .filter(AnalysisDB.status == AnalysisStatus.completed)
        .scalar()
        or 0
    )
    return {
        "total_files": int(total_files),
        "total_rows_processed": int(total_rows),
    }
