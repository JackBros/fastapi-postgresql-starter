from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

DAILY_FREE_AI_LIMIT = 2
PRO_UNLIMITED_CREDITS = 999


class WorkoutSet(BaseModel):
    exercise_name: str
    weight: float
    reps: int
    muscle_group: str = "General"

    @field_validator("muscle_group", mode="before")
    @classmethod
    def normalize_muscle_group(cls, value: Optional[str]) -> str:
        if value is None:
            return "General"
        cleaned = str(value).strip()
        return cleaned if cleaned else "General"


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserMeResponse(BaseModel):
    id: int
    email: str
    is_pro: bool
    daily_ai_limit: int = DAILY_FREE_AI_LIMIT
    remaining_ai_credits: int


class SubscriptionSyncRequest(BaseModel):
    is_pro: bool
    provider_id: Optional[str] = None


class WorkoutResponse(WorkoutSet):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithWorkouts(UserResponse):
    workouts: list[WorkoutResponse] = []


class Token(BaseModel):
    access_token: str
    token_type: str


class AIAnalyzeRequest(BaseModel):
    language: Literal["tr", "en"] = "tr"


class NextSessionTarget(BaseModel):
    exercise: str
    target: str
    reason: str


class AIAnalyzeResponse(BaseModel):
    summary: str
    strengths: list[str]
    weak_points: list[str]
    next_session_targets: list[NextSessionTarget]


class AIGeneratePlanRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=200)
    days_per_week: int = Field(..., ge=1, le=7)
    experience_level: str = Field(..., min_length=1, max_length=100)
    language: Literal["tr", "en"] = "tr"


class PlanExercise(BaseModel):
    name: str
    sets: int
    reps: str
    muscle_group: str
    rest_seconds: int


class PlanDay(BaseModel):
    day_name: str
    exercises: list[PlanExercise]


class AIGeneratePlanResponse(BaseModel):
    plan_title: str
    coach_note: str
    days: list[PlanDay]
