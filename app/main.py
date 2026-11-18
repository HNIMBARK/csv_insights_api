from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import UserDB
from app.routers.analyses import router as analyses_router
from app.routers.auth import router as auth_router

Path("uploads").mkdir(exist_ok=True)

app = FastAPI(title="CSV Insights API")

Base.metadata.create_all(bind=engine)


def seed_users() -> None:
    db: Session = SessionLocal()
    try:
        if db.query(UserDB).count() == 0:
            db.add_all([
                UserDB(username="alice"),
                UserDB(username="bob"),
            ])
            db.commit()
    finally:
        db.close()


seed_users()

app.include_router(auth_router)
app.include_router(analyses_router)
