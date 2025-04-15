from pymongo import MongoClient
from bson import Int64
from datetime import datetime
from dotenv import load_dotenv
import os
import pymongo.errors

# Load environment variables from .env file
load_dotenv()

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    print("ERROR: MONGO_URI not found in .env file")
    raise ValueError("MONGO_URI is required")

print(f"DEBUG: Connecting to MongoDB with URI: {mongo_uri}")

try:
    mongo_client = MongoClient(mongo_uri)
    # Test connection
    mongo_client.server_info()  # Raises ConnectionFailure if unreachable
    print("DEBUG: MongoDB connection successful")
except pymongo.errors.ConnectionFailure as e:
    print(f"ERROR: Failed to connect to MongoDB: {str(e)}")
    raise
except pymongo.errors.ConfigurationError as e:
    print(f"ERROR: Invalid MongoDB URI: {str(e)}")
    raise

db = mongo_client["telegram_bot"]
groups_collection = db["groups"]
users_collection = db["users"]

default_warning_limit = 3
default_punishment = "mute"
default_punishment_set = {"type": "warn", "warning_limit": default_warning_limit, "punishment": default_punishment}

async def get_group_settings(chat_id):
    """Retrieve group settings from MongoDB, or return default if not found."""
    try:
        group = groups_collection.find_one({"chat_id": Int64(chat_id)})
        if group:
            return {
                "type": group.get("type", "warn"),
                "warning_limit": group.get("warning_limit", default_warning_limit),
                "punishment": group.get("punishment", default_punishment)
            }
        return default_punishment_set
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to get group settings for chat_id {chat_id}: {str(e)}")
        return default_punishment_set

async def update_group_settings(chat_id, settings):
    """Update group settings in MongoDB."""
    required_keys = ["type", "warning_limit", "punishment"]
    if not all(key in settings for key in required_keys):
        print(f"ERROR: Settings missing required keys: {required_keys}")
        return

    try:
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
        print(f"DEBUG: Updated settings for chat_id {chat_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to update group settings for chat_id {chat_id}: {str(e)}")

async def store_user(user_id):
    """Store a user who started the bot in MongoDB."""
    try:
        users_collection.update_one(
            {"user_id": Int64(user_id)},
            {"$set": {
                "user_id": Int64(user_id),
                "started_at": datetime.utcnow(),
                "is_channel_member": False  # Default to False until verified
            }},
            upsert=True
        )
        print(f"DEBUG: Stored user_id {user_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to store user_id {user_id}: {str(e)}")

async def check_user_membership(user_id):
    """Check if user is marked as a member of the required channel in MongoDB."""
    try:
        user = users_collection.find_one({"user_id": Int64(user_id)})
        if user and user.get("is_channel_member", False):
            return True
        return False
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to check membership for user_id {user_id}: {str(e)}")
        return False

async def update_user_membership(user_id, is_member):
    """Update user's channel membership status in MongoDB."""
    try:
        users_collection.update_one(
            {"user_id": Int64(user_id)},
            {"$set": {
                "user_id": Int64(user_id),
                "is_channel_member": is_member,
                "membership_updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"DEBUG: Updated membership status for user_id {user_id} to {is_member}")
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to update membership for user_id {user_id}: {str(e)}")
