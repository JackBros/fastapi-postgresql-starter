from pydantic import BaseModel, ConfigDict

class WorkoutSet(BaseModel):
    exercise_name: str
    weight: float
    reps: int

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class WorkoutResponse(WorkoutSet):
    id: int

    model_config = ConfigDict(from_attributes=True)

class UserWithWorkouts(UserResponse):
    workouts: list[WorkoutResponse] = []    

class Token(BaseModel):
    access_token: str
    token_type: str