from fastapi import FastAPI
from database import Base, engine
from routers import workouts, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workout Tracker REST API")

app.include_router(workouts.router)
app.include_router(users.router)