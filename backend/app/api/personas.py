from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.db.mongodb import get_mongo_db
from app.db.mock_data import PERSONA_DEMOGRAPHICS, CATEGORY_TO_PERSONA_ID, resolve_user_id
from app.schemas.requests import PersonaCard
from app.core.logger import get_logger

logger = get_logger("api.personas")
router = APIRouter(prefix="/personas", tags=["Demo Personas"])

PERSONA_METADATA = {
    "DEMO_YOUNGPRO_001": {
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Ananya",
        "tags": ["Lifestyle Creep", "Vehicle Purchase", "100% SIP Discipline"],
    },
    "DEMO_FAMILY_001": {
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Priya",
        "tags": ["Family Planner", "Child Education", "High Savings Rate"],
    },
    "DEMO_STUDENT_001": {
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Aarav",
        "tags": ["Early Saver", "Allowance Budgeting", "Zero Debt"],
    },
    "DEMO_ESTABLISHED_001": {
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Rajiv",
        "tags": ["Pre-Retirement", "Capital Preservation", "High Runway"],
    },
}


@router.get("", response_model=List[PersonaCard], status_code=status.HTTP_200_OK)
async def list_personas(db=Depends(get_mongo_db)):
    """
    Returns the 4 Buildathon demo persona cards for the frontend selection screen.
    Includes demographics, life stage, avatar, and living behavioral highlights.
    """
    cards = []
    categories = ["YOUNGPRO", "FAMILY", "STUDENT", "ESTABLISHED"]

    for cat in categories:
        persona_id = CATEGORY_TO_PERSONA_ID[cat]
        demo = PERSONA_DEMOGRAPHICS.get(persona_id, {})
        meta = PERSONA_METADATA.get(persona_id, {
            "avatar_url": f"https://api.dicebear.com/7.x/bottts/svg?seed={cat}",
            "tags": [cat]
        })

        # Fetch living behavioral summary from MongoDB Atlas
        bi = await db.behavioral_insights.find_one({"user_id": persona_id})
        highlights = {}
        if bi:
            cf = bi.get("cash_flow_summary", {})
            sig = bi.get("behavioral_signals", {})
            highlights = {
                "monthly_income": cf.get("avg_monthly_income_inr", 0),
                "monthly_expense": cf.get("avg_monthly_expense_inr", 0),
                "monthly_surplus": cf.get("net_monthly_surplus_inr", 0),
                "savings_rate_pct": cf.get("savings_rate_pct", 0),
                "liquid_balance": cf.get("latest_liquid_balance_inr", 0),
                "lifestyle_creep_detected": sig.get("lifestyle_inflation_detected", False),
                "emergency_runway_months": sig.get("emergency_runway_months", 0),
            }

        cards.append(PersonaCard(
            user_id=persona_id,
            category=cat,
            name=demo.get("name", cat),
            age=demo.get("age", 25),
            occupation=demo.get("occupation", "Professional"),
            location=demo.get("location", "India"),
            life_stage=demo.get("life_stage", "Career"),
            risk_profile=demo.get("risk_profile", "moderate"),
            income_bracket=demo.get("income_bracket", "N/A"),
            avatar_url=meta["avatar_url"],
            tags=meta["tags"],
            highlights=highlights,
        ))

    return cards


@router.get("/{persona_id}", status_code=status.HTTP_200_OK)
async def get_persona_detail(persona_id: str, db=Depends(get_mongo_db)):
    """
    Returns full demographic profile and detailed 12-month behavioral insights
    for a specific persona from MongoDB Atlas.
    """
    resolved_id = resolve_user_id(persona_id)
    profile = await db.user_profiles.find_one({"user_id": resolved_id}, {"_id": 0})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona '{persona_id}' not found in database.",
        )

    bi = await db.behavioral_insights.find_one({"user_id": resolved_id}, {"_id": 0})
    return {
        "user_id": resolved_id,
        "profile": profile,
        "behavioral_insights": bi or {},
    }
