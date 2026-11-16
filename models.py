from sqlalchemy import Column, Integer, String, Float
from database import Base

class DBWorkout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_name = Column(String)
    weight = Column(Float)
    reps = Column(Integer)