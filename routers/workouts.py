from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from models import DBWorkout
from schemas import WorkoutSet

# Artık "app" değil, sadece bu departmana özel bir "router" tanımlıyoruz
router = APIRouter(
    prefix="/workouts",
    tags=["Workouts"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def add_workout(workout: WorkoutSet, db: Session = Depends(get_db)):
    new_workout = DBWorkout(
        exercise_name=workout.exercise_name,
        weight=workout.weight,
        reps=workout.reps
    )
    db.add(new_workout)
    db.commit()
    db.refresh(new_workout)
    return {"message": "Veri PostgreSQL veritabanına kaydedildi.", "data": new_workout}

@router.get("/")
def get_workouts(db: Session = Depends(get_db)):
    return db.query(DBWorkout).all()