from pymongo import MongoClient
from bson import Int64
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
mongo_client = MongoClient(mongo_uri)
db = mongo_client["telegram_bot"]
groups_collection = db["groups"]
users_collection = db["users"]

default_warning_limit = 3
default_punishment = "mute"
default_punishment_set = {"type": "warn", "warning_limit": default_warning_limit, "punishment": default_punishment}

async def get_group_settings(chat_id):
    """Retrieve group settings from MongoDB, or return default if not found."""
    group = groups_collection.find_one({"chat_id": Int64(chat_id)})
    if group:
        return {
            "type": group.get("type", "warn"),
            "warning_limit": group.get("warning_limit", default_warning_limit),
            "punishment": group.get("punishment", default_punishment)
        }
    return default_punishment_set

async def update_group_settings(chat_id, settings):
    """Update group settings in MongoDB."""
    groups_collection.update_one(
        {"chat_id": Int64(chat_id)},
        {"$set": {
            "chat_id": Int64(chat_id),
            "type": settings["type"],
            "warning_limit": settings["warning_limit"],
            "punishment": settings["punishment"]
        }},
        upsert=True
    )

async def store_user(user_id):
    """Store a user who started the bot in MongoDB."""
    users_collection.update_one(
        {"user_id": Int64(user_id)},
        {"$set": {
            "user_id": Int64(user_id),
            "started_at": datetime.utcnow()
        }},
        upsert=True
    )
