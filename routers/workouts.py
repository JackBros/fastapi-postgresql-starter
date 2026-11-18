from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import DBWorkout
from schemas import WorkoutSet
from auth import get_current_user_id

router = APIRouter(
    prefix="/workouts",
    tags=["Workouts"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_workout(
    workout: WorkoutSet,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    new_workout = DBWorkout(
        exercise_name=workout.exercise_name,
        weight=workout.weight,
        reps=workout.reps,
        user_id=current_user_id
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    return new_workout

@router.get("/")
def get_workouts(
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    return db.query(DBWorkout).filter(DBWorkout.user_id == current_user_id).all()

@router.put("/{workout_id}")
def update_workout(
    workout_id: int,
    workout: WorkoutSet,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    db_workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not db_workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{workout_id} ID'li antrenman bulunamadı."
        )
    if db_workout.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu antrenmanı güncelleme yetkiniz yok."
        )

    db_workout.exercise_name = workout.exercise_name
    db_workout.weight = workout.weight
    db_workout.reps = workout.reps

    db.commit()
    db.refresh(db_workout)
    return db_workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{workout_id} ID'li antrenman bulunamadı."
        )
    if workout.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu antrenmanı silme yetkiniz yok."
        )

    db.delete(workout)
    db.commit()
    return None