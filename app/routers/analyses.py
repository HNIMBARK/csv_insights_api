from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_session
from app.models import AnalysisDB, UserDB
from app.schemas import AnalysisDetail, AnalysisListItem, StatsSummary
from app.services import compute_global_stats, process_analysis, save_uploaded_csv

router = APIRouter(tags=["analyses"])


@router.post("/analyses/upload", response_model=AnalysisDetail, status_code=202)
def upload_analysis(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    original_file_name, stored_file_name, file_size = save_uploaded_csv(file)

    analysis = AnalysisDB(
        file_name=original_file_name,
        stored_file_name=stored_file_name,
        file_size=file_size,
        owner_id=current_user.id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    background_tasks.add_task(process_analysis, analysis.id)
    return analysis


@router.get("/analyses", response_model=list[AnalysisListItem])
def get_analyses(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return db.query(AnalysisDB).order_by(AnalysisDB.created_at.desc()).all()


@router.get("/analyses/stats/summary", response_model=StatsSummary)
def get_stats_summary(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return compute_global_stats(db)


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis_detail(
    analysis_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    analysis = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.delete("/analyses/{analysis_id}")
def delete_analysis(
    analysis_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    analysis = db.query(AnalysisDB).filter(AnalysisDB.id == analysis_id).first()
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this analysis")

    db.delete(analysis)
    db.commit()
    return {"message": f"Analysis {analysis_id} deleted"}
