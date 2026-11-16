from pydantic import BaseModel

class WorkoutSet(BaseModel):
    exercise_name: str
    weight: float
    reps: int