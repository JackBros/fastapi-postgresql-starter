from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship
from database import Base


class DBUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_pro = Column(Boolean, default=False, nullable=False)
    ai_usage_count = Column(Integer, default=0, nullable=False)
    ai_usage_date = Column(Date, nullable=True)

    workouts = relationship(
        "DBWorkout",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class DBWorkout(Base):
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    exercise_name = Column(String)
    weight = Column(Float)
    reps = Column(Integer)
    muscle_group = Column(String, default="General", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("DBUser", back_populates="workouts")
