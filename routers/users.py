from datetime import datetime, timezone
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import DBUser, DBWorkout
from schemas import (
    DAILY_FREE_AI_LIMIT,
    PRO_UNLIMITED_CREDITS,
    SubscriptionSyncRequest,
    Token,
    UserCreate,
    UserMeResponse,
    UserResponse,
    UserWithWorkouts,
)
from auth import create_access_token, get_current_user_id

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


def _build_user_me_response(user: DBUser) -> UserMeResponse:
    today = datetime.now(timezone.utc).date()
    if user.is_pro:
        remaining_credits = PRO_UNLIMITED_CREDITS
    else:
        used_today = user.ai_usage_count if user.ai_usage_date == today else 0
        remaining_credits = max(0, DAILY_FREE_AI_LIMIT - used_today)

    return UserMeResponse(
        id=user.id,
        email=user.email,
        is_pro=bool(user.is_pro),
        daily_ai_limit=DAILY_FREE_AI_LIMIT,
        remaining_ai_credits=remaining_credits,
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(DBUser).filter(DBUser.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kayıtlı."
        )

    hashed_pw = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    new_user = DBUser(
        email=user.email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/me", response_model=UserMeResponse)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user = db.query(DBUser).filter(DBUser.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )
    return _build_user_me_response(user)


@router.post("/subscription/sync", response_model=UserMeResponse)
def sync_subscription(
    payload: SubscriptionSyncRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user = db.query(DBUser).filter(DBUser.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )

    user.is_pro = payload.is_pro
    db.commit()
    db.refresh(user)
    return _build_user_me_response(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user_account(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user = db.query(DBUser).filter(DBUser.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )

    # Delete user's workouts explicitly before deleting the user to satisfy
    # PostgreSQL FK constraints regardless of ON DELETE CASCADE settings.
    db.query(DBWorkout).filter(DBWorkout.user_id == current_user_id).delete(
        synchronize_session=False
    )
    db.delete(user)
    db.commit()
    return None


@router.get("/{user_id}", response_model=UserWithWorkouts)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı."
        )
    return user


@router.post("/login", response_model=Token)
def login_user(user_credentials: UserCreate, db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.email == user_credentials.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı."
        )

    is_valid = bcrypt.checkpw(
        user_credentials.password.encode("utf-8"),
        user.hashed_password.encode("utf-8")
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı."
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
