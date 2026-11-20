"""
Mock demographic definitions and JSON loader for the four Buildathon demo profiles:
1. YOUNGPRO    -> DEMO_YOUNGPRO_001 (Ananya Mehta - 28, Product & Marketing Professional)
2. FAMILY      -> DEMO_FAMILY_001   (Priya Nair - 35, Senior Corporate Professional)
3. STUDENT     -> DEMO_STUDENT_001  (Aarav Sharma - 20, College Student)
4. ESTABLISHED -> DEMO_ESTABLISHED_001 (Rajiv Kapoor - 50, Senior Corporate Executive)

Loads rich behavioral intelligence from backend/profiles_data/<CATEGORY>/behavioral_insights.json.
"""
import json
from pathlib import Path
from typing import Dict, Any, List

# Persona demographics metadata mapping
PERSONA_DEMOGRAPHICS: Dict[str, Dict[str, Any]] = {
    "DEMO_YOUNGPRO_001": {
        "user_id": "DEMO_YOUNGPRO_001",
        "category": "YOUNGPRO",
        "name": "Ananya Mehta",
        "age": 28,
        "occupation": "Product & Marketing Professional",
        "location": "Pune, Maharashtra",
        "income_bracket": "6-8 Lakhs",
        "risk_profile": "aggressive",
        "tax_slab": "20%",
        "life_stage": "Young Professional / Wealth Accumulator",
    },
    "DEMO_FAMILY_001": {
        "user_id": "DEMO_FAMILY_001",
        "category": "FAMILY",
        "name": "Priya Nair",
        "age": 35,
        "occupation": "Senior Corporate Professional",
        "location": "Bengaluru, Karnataka",
        "income_bracket": "24-30 Lakhs",
        "risk_profile": "moderate",
        "tax_slab": "30%",
        "life_stage": "Family / Child Education & Home Planner",
    },
    "DEMO_STUDENT_001": {
        "user_id": "DEMO_STUDENT_001",
        "category": "STUDENT",
        "name": "Aarav Sharma",
        "age": 20,
        "occupation": "College Student",
        "location": "Lucknow, Uttar Pradesh",
        "income_bracket": "Under 3 Lakhs (Allowance)",
        "risk_profile": "moderate_aggressive",
        "tax_slab": "0%",
        "life_stage": "Student / Early Saver",
    },
    "DEMO_ESTABLISHED_001": {
        "user_id": "DEMO_ESTABLISHED_001",
        "category": "ESTABLISHED",
        "name": "Rajiv Kapoor",
        "age": 50,
        "occupation": "Senior Corporate Executive",
        "location": "Mumbai, Maharashtra",
        "income_bracket": "50+ Lakhs",
        "risk_profile": "moderate_conservative",
        "tax_slab": "30%",
        "life_stage": "Established / Pre-Retirement & Preservation",
    },
}

# Category to Persona ID mapping
CATEGORY_TO_PERSONA_ID: Dict[str, str] = {
    "YOUNGPRO": "DEMO_YOUNGPRO_001",
    "FAMILY": "DEMO_FAMILY_001",
    "STUDENT": "DEMO_STUDENT_001",
    "ESTABLISHED": "DEMO_ESTABLISHED_001",
}


def resolve_user_id(identifier: str) -> str:
    """Resolves a category name (e.g. 'YOUNGPRO') or persona id to normalized user_id."""
    clean = str(identifier).strip().upper()
    return CATEGORY_TO_PERSONA_ID.get(clean, identifier)


def get_profiles_dir() -> Path:
    """Returns the absolute path to backend/profiles_data directory."""
    # Current file: backend/app/db/mock_data.py -> backend root is 3 levels up
    backend_root = Path(__file__).resolve().parent.parent.parent
    return backend_root / "profiles_data"


def load_persona_behavioral_insights(category: str) -> Dict[str, Any]:
    """Loads behavioral_insights.json for a given persona category."""
    profiles_dir = get_profiles_dir()
    file_path = profiles_dir / category / "behavioral_insights.json"
    if not file_path.exists():
        print(f"⚠️ Warning: behavioral_insights.json not found at {file_path}")
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_all_persona_records() -> List[Dict[str, Any]]:
    """
    Builds database seeding records for all four persona categories.
    For each user:
    - user_profiles record (demographics)
    - behavioral_insights record (from profiles_data/<CATEGORY>/behavioral_insights.json)
    """
    records = []
    categories = ["YOUNGPRO", "FAMILY", "STUDENT", "ESTABLISHED"]

    for cat in categories:
        persona_id = CATEGORY_TO_PERSONA_ID[cat]
        demographics = PERSONA_DEMOGRAPHICS[persona_id]
        raw_insights = load_persona_behavioral_insights(cat)

        # 1. Profile Record
        records.append({
            "collection": "user_profiles",
            "doc": {
                "user_id": persona_id,
                "persona_id": persona_id,
                "category": cat,
                "demographics": demographics,
            }
        })

        # 2. Behavioral Insights Record
        insights_doc = dict(raw_insights)
        insights_doc["user_id"] = persona_id
        insights_doc["persona_id"] = persona_id
        insights_doc["category"] = cat

        records.append({
            "collection": "behavioral_insights",
            "doc": insights_doc
        })

    return records
