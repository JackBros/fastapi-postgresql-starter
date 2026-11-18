from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import DBWorkout, DBUser
from schemas import WorkoutSet

router = APIRouter(
    prefix="/workouts",
    tags=["Workouts"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_workout(workout: WorkoutSet, db: Session = Depends(get_db)):
    # 1. Önce bu user_id'ye sahip bir kullanıcı var mı kontrol et
    user = db.query(DBUser).filter(DBUser.id == workout.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{workout.user_id} ID'li kullanıcı bulunamadı."
        )

    # 2. Kullanıcı varsa antrenmanı ona bağlayarak kaydet
    new_workout = DBWorkout(
        exercise_name=workout.exercise_name,
        weight=workout.weight,
        reps=workout.reps,
        user_id=workout.user_id
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    return new_workout

@router.get("/")
def get_workouts(db: Session = Depends(get_db)):
    return db.query(DBWorkout).all()

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    # 1. Önce silinmek istenen antrenmanı veritabanında bul
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    
    # 2. Eğer böyle bir antrenman yoksa 404 hatası dön
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{workout_id} ID'li antrenman bulunamadı."
        )

    # 3. Antrenman bulunduysa sil ve değişikliği veritabanına onayla
    db.delete(workout)
    db.commit()
    return None

@router.put("/{workout_id}")
def update_workout(workout_id: int, workout: WorkoutSet, db: Session = Depends(get_db)):
    # 1. Güncellenecek kaydı bul
    db_workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not db_workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{workout_id} ID'li antrenman bulunamadı."
        )

    # 2. Eski değerlerin üzerine yenilerini yaz
    db_workout.exercise_name = workout.exercise_name
    db_workout.weight = workout.weight
    db_workout.reps = workout.reps
    db_workout.user_id = workout.user_id

    # 3. Değişikliği veritabanına onayla
    db.commit()
    db.refresh(db_workout)
    return db_workout