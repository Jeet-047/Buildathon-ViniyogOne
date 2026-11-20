"""
MongoDB client connection manager.
Provides transparent in-memory simulation using mongomock-motor when MONGO_SIMULATION=true.
Seeds the four demo profiles (YOUNGPRO, FAMILY, STUDENT, ESTABLISHED) from backend/profiles_data.
"""
from typing import Optional
from app.core.config import settings
from app.core.logger import get_logger
from app.db.mock_data import build_all_persona_records

logger = get_logger("db.mongodb")

_mongo_client: Optional[object] = None
_mongo_db: Optional[object] = None
_is_seeded: bool = False


async def seed_demo_data(db) -> None:
    """Seeds the 4 demo personas (user_profiles & behavioral_insights) into MongoDB or MongoMock."""
    global _is_seeded
    if _is_seeded:
        return

    logger.info("Seeding the 4 Buildathon demo profiles from backend/profiles_data...")
    records = build_all_persona_records()
    for item in records:
        collection_name = item["collection"]
        col = getattr(db, collection_name)
        doc = item.get("doc", {})
        user_id = doc.get("user_id")
        await col.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
    _is_seeded = True
    logger.info("✓ 4 Demo profiles (user_profiles & behavioral_insights) seeded successfully.")


def get_mongo_db():
    """
    Returns the active database instance.
    Uses mongomock-motor for in-memory execution if MONGO_SIMULATION=true.
    """
    global _mongo_client, _mongo_db

    if _mongo_db is not None:
        return _mongo_db

    if settings.MONGO_SIMULATION:
        logger.info("MongoDB Simulation Mode active (In-Memory mongomock-motor).")
        import mongomock_motor
        _mongo_client = mongomock_motor.AsyncMongoMockClient()
        _mongo_db = _mongo_client[settings.MONGO_DB_NAME]
    else:
        logger.info(f"Connecting to live MongoDB instance at: {settings.MONGO_URI}")
        import motor.motor_asyncio
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        _mongo_db = _mongo_client[settings.MONGO_DB_NAME]

    return _mongo_db
