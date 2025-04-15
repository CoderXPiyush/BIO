from pyrogram import Client, enums
from pymongo import MongoClient
from bson import Int64
from dotenv import load_dotenv
import os
import pymongo.errors
import asyncio

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")

# MongoDB setup
try:
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client["telegram_bot"]
    groups_collection = db["groups"]
    users_collection = db["users"]
except pymongo.errors.ConnectionFailure as e:
    print(f"ERROR: Failed to connect to MongoDB: {str(e)}")
    raise
except pymongo.errors.ConfigurationError as e:
    print(f"ERROR: Invalid MongoDB URI: {str(e)}")
    raise

async def broadcast_message(client: Client, message_text: str):
    """
    Broadcast a message to all users and groups in MongoDB.
    Returns (success_count, failure_count).
    """
    success_count = 0
    failure_count = 0

    # Broadcast to users
    try:
        async for user in users_collection.find():
            user_id = user["user_id"]
            try:
                await client.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=enums.ParseMode.HTML
                )
                print(f"DEBUG: Broadcast sent to user_id {user_id}")
                success_count += 1
                await asyncio.sleep(0.1)  # Avoid flood limits
            except (enums.exceptions.bad_request_400.UserIsBlocked, 
                    enums.exceptions.bad_request_400.ChatWriteForbidden,
                    enums.exceptions.forbidden_403.ChatWriteForbidden) as e:
                print(f"WARNING: Failed to send to user_id {user_id}: {str(e)}")
                failure_count += 1
            except enums.exceptions.flood_420.FloodWait as e:
                print(f"WARNING: FloodWait for user_id {user_id}: {e}")
                failure_count += 1
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"ERROR: Failed to send to user_id {user_id}: {str(e)}")
                failure_count += 1
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to fetch users from MongoDB: {str(e)}")
        failure_count += 1

    # Broadcast to groups
    try:
        async for group in groups_collection.find():
            chat_id = group["chat_id"]
            try:
                await client.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode=enums.ParseMode.HTML
                )
                print(f"DEBUG: Broadcast sent to chat_id {chat_id}")
                success_count += 1
                await asyncio.sleep(0.1)  # Avoid flood limits
            except (enums.exceptions.bad_request_400.ChatWriteForbidden,
                    enums.exceptions.forbidden_403.ChatWriteForbidden) as e:
                print(f"WARNING: Failed to send to chat_id {chat_id}: {str(e)}")
                failure_count += 1
            except enums.exceptions.flood_420.FloodWait as e:
                print(f"WARNING: FloodWait for chat_id {chat_id}: {e}")
                failure_count += 1
                await asyncio.sleep(e.value)
            except Exception as e:
                print(f"ERROR: Failed to send to chat_id {chat_id}: {str(e)}")
                failure_count += 1
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to fetch groups from MongoDB: {str(e)}")
        failure_count += 1

    return success_count, failure_count
