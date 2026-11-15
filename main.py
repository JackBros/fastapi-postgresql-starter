import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, status
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# .env dosyasındaki gizli değişkenleri yükle
load_dotenv()

# Şifreyi kodun içinden değil, güvenli ortam değişkeninden oku
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DBWorkout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_name = Column(String)
    weight = Column(Float)
    reps = Column(Integer)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workout Tracker REST API")

class WorkoutSet(BaseModel):
    exercise_name: str
    weight: float
    reps: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/workouts", status_code=status.HTTP_201_CREATED)
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

@app.get("/workouts")
def get_workouts(db: Session = Depends(get_db)):
    return db.query(DBWorkout).all()