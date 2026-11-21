from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import Base, engine
from routers import ai, users, workouts

Base.metadata.create_all(bind=engine)


def run_safe_migrations() -> None:
    """Idempotently add new columns on existing Neon PostgreSQL tables without data loss."""
    migration_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_pro BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_usage_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_usage_date DATE",
        "ALTER TABLE workouts ADD COLUMN IF NOT EXISTS muscle_group VARCHAR NOT NULL DEFAULT 'General'",
        "ALTER TABLE workouts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
    ]
    with engine.begin() as conn:
        for statement in migration_statements:
            conn.execute(text(statement))


run_safe_migrations()

app = FastAPI(title="Workout Tracker & AI Fitness Coach REST API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workouts.router)
app.include_router(users.router)
app.include_router(ai.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Workout API is running"}
