from fastapi import FastAPI
from database import Base, engine
from routers import workouts

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workout Tracker REST API")

# Workouts departmanını ana santrale bağla
app.include_router(workouts.router)