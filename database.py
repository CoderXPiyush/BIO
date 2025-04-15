from motor.motor_asyncio import AsyncIOMotorClient
from bson import Int64
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    logger.error("MONGO_URI not found in .env file")
    raise ValueError("MONGO_URI is required")

# MongoDB client (initialized lazily)
mongo_client = None
db = None
groups_collection = None
users_collection = None
warnings_collection = None

async def initialize_db():
    """Initialize the MongoDB connection and collections."""
    global mongo_client, db, groups_collection, users_collection, warnings_collection
    try:
        mongo_client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = mongo_client["telegram_bot"]
        groups_collection = db["groups"]
        users_collection = db["users"]
        warnings_collection = db["warnings"]
        # Test connection
        await db.command("ping")
        logger.info("MongoDB connection successful")
        # Add indexes
        await groups_collection.create_index([("chat_id", 1)], unique=True)
        await users_collection.create_index([("user_id", 1)], unique=True)
        await warnings_collection.create_index([("user_id", 1), ("chat_id", 1)], unique=True)
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

# Defaults
default_warning_limit = 3
default_punishment = "mute"
default_punishment_set = {"type": "warn", "warning_limit": default_warning_limit, "punishment": default_punishment}

async def get_group_settings(chat_id):
    if db is None:  # Explicitly check for None
        await initialize_db()
    try:
        group = await groups_collection.find_one({"chat_id": Int64(chat_id)})
        if group:
            return {
                "type": group.get("type", "warn"),
                "warning_limit": group.get("warning_limit", default_warning_limit),
                "punishment": group.get("punishment", default_punishment)
            }
        return default_punishment_set
    except Exception as e:
        logger.error(f"Failed to get group settings for chat_id {chat_id}: {e}")
        return default_punishment_set

async def update_group_settings(chat_id, settings):
    if db is None:  # Explicitly check for None
        await initialize_db()
    required_keys = ["type", "warning_limit", "punishment"]
    if not all(key in settings for key in required_keys):
        logger.error(f"Settings missing required keys: {required_keys}")
        return

    try:
        await groups_collection.update_one(
            {"chat_id": Int64(chat_id)},
            {"$set": {
                "chat_id": Int64(chat_id),
                "type": settings["type"],
                "warning_limit": settings["warning_limit"],
                "punishment": settings["punishment"],
                "last_updated": datetime.utcnow()
            }},
            upsert=True
        )
        logger.debug(f"Updated settings for chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Failed to update group settings for chat_id {chat_id}: {e}")

async def store_user(user_id):
    if db is None:  # Explicitly check for None
        await initialize_db()
    try:
        await users_collection.update_one(
            {"user_id": Int64(user_id)},
            {"$set": {
                "user_id": Int64(user_id),
                "started_at": datetime.utcnow()
            }},
            upsert=True
        )
        logger.debug(f"Stored user_id {user_id}")
    except Exception as e:
        logger.error(f"Failed to store user_id {user_id}: {e}")

async def get_warnings(user_id, chat_id):
    if db is None:  # Explicitly check for None
        await initialize_db()
    result = await warnings_collection.find_one({"user_id": Int64(user_id), "chat_id": Int64(chat_id)})
    return result["count"] if result else 0

async def update_warnings(user_id, chat_id, count):
    if db is None:  # Explicitly check for None
        await initialize_db()
    try:
        await warnings_collection.update_one(
            {"user_id": Int64(user_id), "chat_id": Int64(chat_id)},
            {"$set": {"count": count, "last_updated": datetime.utcnow()}},
            upsert=True
        )
        logger.debug(f"Updated warnings for user_id {user_id}, chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Failed to update warnings for user_id {user_id}, chat_id {chat_id}: {e}")

# Initialize DB when the module is imported (called by bot.py)
import asyncio
loop = asyncio.get_event_loop()
loop.run_until_complete(initialize_db())
