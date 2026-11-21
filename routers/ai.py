from datetime import datetime, timezone
import json
import os
from typing import TypeVar
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from auth import get_current_user_id
from database import get_db
from models import DBUser, DBWorkout
from schemas import (
    AIAnalyzeRequest,
    AIAnalyzeResponse,
    AIGeneratePlanRequest,
    AIGeneratePlanResponse,
    DAILY_FREE_AI_LIMIT,
)

load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["AI Coach"],
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


def _get_user_or_404(db: Session, user_id: int) -> DBUser:
    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı.",
        )
    return user


def _check_ai_quota(user: DBUser, db: Session) -> None:
    """Enforce freemium daily quota: unlimited for Pro, max 2/day for free users."""
    if user.is_pro:
        return

    today = datetime.now(timezone.utc).date()
    if user.ai_usage_date != today:
        user.ai_usage_count = 0
        user.ai_usage_date = today
        db.commit()
        db.refresh(user)

    if user.ai_usage_count >= DAILY_FREE_AI_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="FREE_AI_LIMIT_REACHED",
        )


def _consume_ai_quota(user: DBUser, db: Session) -> None:
    """Record 1 AI credit usage only after Gemini succeeds."""
    if user.is_pro:
        return

    today = datetime.now(timezone.utc).date()
    if user.ai_usage_date != today:
        user.ai_usage_count = 1
        user.ai_usage_date = today
    else:
        user.ai_usage_count += 1

    db.commit()
    db.refresh(user)


def _get_gemini_client_and_model(language: str) -> tuple[genai.Client, str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        detail = (
            "AI servisi şu anda yapılandırılmamış (GEMINI_API_KEY eksik)."
            if language == "tr"
            else "AI service is not configured (missing GEMINI_API_KEY)."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    return genai.Client(api_key=api_key), model_name


def _serialize_workouts_for_prompt(workouts: list[DBWorkout]) -> list[dict]:
    serialized = []
    for w in workouts:
        created_iso = w.created_at.isoformat() if w.created_at else None
        weight_val = float(w.weight or 0.0)
        reps_val = int(w.reps or 0)
        serialized.append(
            {
                "exercise_name": w.exercise_name,
                "weight_kg": weight_val,
                "reps": reps_val,
                "volume_kg": round(weight_val * reps_val, 2),
                "muscle_group": w.muscle_group or "General",
                "created_at": created_iso,
            }
        )
    return serialized


def _parse_structured_response(
    raw_text: str | None,
    schema_cls: type[SchemaT],
) -> SchemaT:
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response from Gemini.")

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    parsed = json.loads(cleaned)
    return schema_cls.model_validate(parsed)


@router.post("/analyze", response_model=AIAnalyzeResponse)
def analyze_workouts(
    request: AIAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user = _get_user_or_404(db, current_user_id)

    workouts = (
        db.query(DBWorkout)
        .filter(DBWorkout.user_id == current_user_id)
        .order_by(DBWorkout.created_at.desc(), DBWorkout.id.desc())
        .limit(30)
        .all()
    )

    if not workouts:
        detail = (
            "Analiz yapabilmek için önce en az bir antrenman kaydı eklemelisiniz."
            if request.language == "tr"
            else "Please log at least one workout before requesting an AI analysis."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )

    _check_ai_quota(user, db)

    client, model_name = _get_gemini_client_and_model(request.language)
    workout_records = _serialize_workouts_for_prompt(workouts)
    target_language = "Turkish (Türkçe)" if request.language == "tr" else "English"

    prompt = f"""
You are an elite, evidence-based strength and hypertrophy coach (CSCS certified).
Analyze the athlete's last {len(workout_records)} workout records below and provide specific, data-driven coaching feedback.

Workout history (newest first):
{json.dumps(workout_records, ensure_ascii=False)}

Requirements:
1. Write ALL text values strictly in {target_language}.
2. Reference the athlete's actual exercises, weights (kg), reps, volumes, and muscle_group balance—never invent workouts not present in the log.
3. Return ONLY valid JSON matching this exact schema:
{{
  "summary": "Overall performance, consistency, and training volume assessment",
  "strengths": ["Concrete strength 1", "Concrete strength 2"],
  "weak_points": ["Undertrained muscle group, balance warning, or recovery note"],
  "next_session_targets": [
    {{
      "exercise": "Exact exercise name from history",
      "target": "Specific realistic progressive overload target (e.g. +2.5 kg or +1-2 reps)",
      "reason": "Brief progressive overload rationale based on their logged numbers"
    }}
  ]
}}
""".strip()

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIAnalyzeResponse,
                temperature=0.4,
            ),
        )
        result = _parse_structured_response(response.text, AIAnalyzeResponse)
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError, Exception) as exc:
        detail = (
            "AI analiz yanıtı oluşturulamadı. Lütfen biraz sonra tekrar deneyin."
            if request.language == "tr"
            else "Could not generate AI workout analysis. Please try again shortly."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from exc

    _consume_ai_quota(user, db)
    return result


@router.post("/generate-plan", response_model=AIGeneratePlanResponse)
def generate_workout_plan(
    request: AIGeneratePlanRequest,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    user = _get_user_or_404(db, current_user_id)
    _check_ai_quota(user, db)

    recent_workouts = (
        db.query(DBWorkout)
        .filter(DBWorkout.user_id == current_user_id)
        .order_by(DBWorkout.created_at.desc(), DBWorkout.id.desc())
        .limit(30)
        .all()
    )

    client, model_name = _get_gemini_client_and_model(request.language)
    workout_records = _serialize_workouts_for_prompt(recent_workouts)
    target_language = "Turkish (Türkçe)" if request.language == "tr" else "English"

    history_section = (
        json.dumps(workout_records, ensure_ascii=False)
        if workout_records
        else "No previous workouts logged yet."
    )

    prompt = f"""
You are an elite strength & conditioning coach creating a personalized weekly workout plan.

Athlete profile:
- Primary goal: {request.goal}
- Training frequency: {request.days_per_week} days per week
- Experience level: {request.experience_level}

Recent logged workouts (use as reference for exercise familiarity, weak points, and baseline strength if available):
{history_section}

Requirements:
1. Write `plan_title`, `coach_note`, and `day_name` strictly in {target_language}.
2. Create exactly {request.days_per_week} training days in `days`.
3. For each exercise's `muscle_group`, use one of these standard tags: "Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Full Body".
4. Provide realistic `sets` (integer, e.g. 3 or 4), `reps` (string range like "6-8" or "10-12"), and `rest_seconds` (integer, e.g. 60, 90, 120, 180).
5. Return ONLY valid JSON matching this exact schema:
{{
  "plan_title": "Program title",
  "coach_note": "Short, practical coaching advice tailored to the user",
  "days": [
    {{
      "day_name": "Day 1 - Push",
      "exercises": [
        {{
          "name": "Bench Press",
          "sets": 4,
          "reps": "6-8",
          "muscle_group": "Chest",
          "rest_seconds": 120
        }}
      ]
    }}
  ]
}}
""".strip()

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AIGeneratePlanResponse,
                temperature=0.5,
            ),
        )
        result = _parse_structured_response(response.text, AIGeneratePlanResponse)
    except HTTPException:
        raise
    except (json.JSONDecodeError, ValidationError, ValueError, Exception) as exc:
        detail = (
            "AI antrenman programı oluşturulamadı. Lütfen biraz sonra tekrar deneyin."
            if request.language == "tr"
            else "Could not generate AI workout plan. Please try again shortly."
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=detail,
        ) from exc

    _consume_ai_quota(user, db)
    return result
