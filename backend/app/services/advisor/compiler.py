from app.core.config import settings
from app.services.advisor.graph import build_graph

# Checkpointer configuration based on simulation mode
MONGO_SIMULATION = settings.MONGO_SIMULATION

if MONGO_SIMULATION:
    # In-memory checkpointer for local simulation / sandbox
    from langgraph.checkpoint.memory import MemorySaver
    checkpointer = MemorySaver()
else:
    # Durable MongoDB checkpointer for production deployment
    from pymongo import MongoClient
    from langgraph.checkpoint.mongodb import MongoDBSaver

    mongo_uri = settings.MONGO_URI
    if not mongo_uri:
        raise ValueError("CRITICAL: MONGO_URI is required when MONGO_SIMULATION=false")

    client = MongoClient(mongo_uri)
    checkpointer = MongoDBSaver(client, db_name=settings.MONGO_DB_NAME)

# Compiled StateGraph instance ready for execution and API endpoints
compiled_graph = build_graph(checkpointer=checkpointer)
