from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    workouts = relationship("DBWorkout", back_populates="owner")

class DBWorkout(Base):
    __tablename__ = "workouts"
    
    id = Column(Integer, primary_key=True, index=True)
    exercise_name = Column(String)
    weight = Column(Float)
    reps = Column(Integer)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("DBUser", back_populates="workouts")