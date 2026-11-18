from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import create_token_for_user, get_current_user, get_session
from app.models import UserDB
from app.schemas import LoginData, User

router = APIRouter(tags=["auth"])


@router.post("/login")
def login(login_data: LoginData, db: Session = Depends(get_session)):
    user = db.query(UserDB).filter(UserDB.username == login_data.username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token_for_user(user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/users", response_model=list[User])
def get_users(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return db.query(UserDB).order_by(UserDB.id.asc()).all()
