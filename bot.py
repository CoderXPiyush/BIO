from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from database import get_group_settings, update_group_settings, store_user
from punishments import apply_punishment, warnings
from promo import broadcast_message
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Debug: Print environment variables
print(f"DEBUG: API_ID = {os.getenv('API_ID')}")
print(f"DEBUG: API_HASH = {os.getenv('API_HASH')}")
print(f"DEBUG: BOT_TOKEN = {os.getenv('BOT_TOKEN')}")
print(f"DEBUG: OWNER_ID = {os.getenv('OWNER_ID')}")

# User Client setup
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
owner_id = os.getenv("OWNER_ID")

# Validate credentials
if not all([api_id, api_hash, bot_token]):
    print("ERROR: Missing API_ID, API_HASH, or BOT_TOKEN in .env")
    exit(1)

try:
    api_id = int(api_id)  # Ensure API_ID is an integer
except ValueError:
    print("ERROR: API_ID must be an integer")
    exit(1)

try:
    owner_id = int(owner_id) if owner_id else None  # Allow OWNER_ID to be optional for other functionality
except ValueError:
    print("ERROR: OWNER_ID must be an integer")
    exit(1)

app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def is_admin(client, chat_id, user_id):
    try:
        async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
            if member.user.id == user_id:
                return True
        return False
    except errors.FloodWait as e:
        print(f"WARNING: FloodWait in is_admin: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to check admin status: {e}")
        return False

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    try:
        user_name = message.from_user.first_name
        # Store user in MongoDB
        await store_user(message.from_user.id)
        start_message = (
            f"Hello {user_name}!\n\n"
            "Welcome to the Bio Link Monitor Bot! I help keep Telegram groups clean by monitoring user bios for unauthorized links. "
            "Group admins can configure me to warn, mute, or ban users who have links in their bios.\n\n"
            "Use the buttons below to join our support group or add me to your group!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Support Group", url="https://t.me/itsSmartDev")],
            [InlineKeyboardButton("Add to Group", url=f"https://t.me/{(await client.get_me()).username}?startgroup=true")]
        ])
        await message.reply_text(
            f"👋 Hello {message.from_user.first_name}!\n\n"
            "I'm a Bio Link Monitor Bot that helps keep your groups clean by monitoring user bios.\n\n"
            "🔹 Admins can configure me with /config in their groups\n"
            "🔹 I can warn, mute, or ban users with suspicious links in their bios",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"ERROR: Failed in start handler: {e}")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast(client, message):
    try:
        if not owner_id or str(message.from_user.id) != str(owner_id):
            await message.reply_text("❌ Only the bot owner can use this command.", parse_mode=enums.ParseMode.HTML)
            return

        if len(message.command) < 2:
            await message.reply_text("Please provide a message to broadcast.\nExample: /broadcast Hello everyone!", parse_mode=enums.ParseMode.HTML)
            return

        broadcast_text = " ".join(message.command[1:])
        await message.reply_text("Starting broadcast...", parse_mode=enums.ParseMode.HTML)
        
        success_count, failure_count = await broadcast_message(client, broadcast_text)
        await message.reply_text(
            f"Broadcast completed.\nSuccess: {success_count}\nFailures: {failure_count}",
            parse_mode=enums.ParseMode.HTML
        )
    except Exception as e:
        print(f"ERROR: Failed in broadcast handler: {e}")
        await message.reply_text("An error occurred during broadcast.", parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.group & filters.command("config"))
async def configure(client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        if not await is_admin(client, chat_id, user_id):
            await message.reply_text("<b>❌ You are not administrator</b>", parse_mode=enums.ParseMode.HTML)
            await message.delete()
            return

        settings = await get_group_settings(chat_id)
        current_punishment = settings["punishment"]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn", callback_data="warn")],
            [InlineKeyboardButton("Mute ✅" if current_punishment == "mute" else "Mute", callback_data="mute"), 
             InlineKeyboardButton("Ban ✅" if current_punishment == "ban" else "Ban", callback_data="ban"),
             InlineKeyboardButton("Delete ✅" if current_punishment == "delete" else "Delete", callback_data="delete")],
            [InlineKeyboardButton("Close", callback_data="close")]
        ])
        await message.reply_text("<b>Select punishment for users who have links in their bio:</b>", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
        await message.delete()
    except Exception as e:
        print(f"ERROR: Failed in config handler: {e}")

@app.on_callback_query()
async def callback_handler(client, callback_query):
    try:
        data = callback_query.data
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id

        if not await is_admin(client, chat_id, user_id):
            await callback_query.answer("❌ You are not administrator", show_alert=True)
            return

        if data == "close":
            await callback_query.message.delete()
            return

        settings = await get_group_settings(chat_id)

        if data == "back":
            current_punishment = settings["punishment"]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Warn", callback_data="warn")],
                [InlineKeyboardButton("Mute ✅" if current_punishment == "mute" else "Mute", callback_data="mute"), 
                 InlineKeyboardButton("Ban ✅" if current_punishment == "ban" else "Ban", callback_data="ban"),
                 InlineKeyboardButton("Delete ✅" if currentesie.py`).

---

### 2. Database Module (`database.py`)

Unchanged, handles MongoDB interactions.

<xaiArtifact artifact_id="a22aa3d0-dbb5-40de-bb35-bc48a4bf94c1" artifact_version_id="bf84b5a6-08f2-482d-9d3b-e183df107ade" title="database.py" contentType="text/python">
```python
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
                "started_at": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"DEBUG: Stored user_id {user_id}")
    except pymongo.errors.PyMongoError as e:
        print(f"ERROR: Failed to store user_id {user_id}: {str(e)}")
