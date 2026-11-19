from fastapi import FastAPI
from database import Base, engine
from routers import workouts, users
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workout Tracker REST API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workouts.router)
app.include_router(users.router)
@app.get("/")
def root():
    return {"status": "ok", "message": "Workout API is running"}