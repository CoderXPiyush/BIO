from pyrogram import Client, enums
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import asyncio
from typing import Tuple

load_dotenv()

class BroadcastManager:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")
        
        self.client = AsyncIOMotorClient(self.mongo_uri)
        self.db = self.client["telegram_bot"]
        self.users_collection = self.db["users"]
        self.groups_collection = self.db["groups"]

    async def send_safely(self, client: Client, chat_id: int, text: str) -> bool:
        """Safely send a message with error handling"""
        try:
            await client.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=enums.ParseMode.HTML
            )
            return True
        except (errors.UserIsBlocked, errors.ChatWriteForbidden):
            return False
        except errors.FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.send_safely(client, chat_id, text)
        except Exception as e:
            print(f"Send error to {chat_id}: {e}")
            return False

    async def broadcast_users(self, client: Client, text: str) -> Tuple[int, int]:
        """Broadcast to all users"""
        success = failure = 0
        try:
            async for user in self.users_collection.find({"user_id": {"$exists": True}}):
                if await self.send_safely(client, user["user_id"], text):
                    success += 1
                else:
                    failure += 1
                await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"User broadcast error: {e}")
            failure += 1
        return success, failure

    async def broadcast_groups(self, client: Client, text: str) -> Tuple[int, int]:
        """Broadcast to all groups"""
        success = failure = 0
        try:
            async for group in self.groups_collection.find({"chat_id": {"$exists": True}}):
                if await self.send_safely(client, group["chat_id"], text):
                    success += 1
                else:
                    failure += 1
                await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"Group broadcast error: {e}")
            failure += 1
        return success, failure

    async def broadcast_message(self, client: Client, text: str) -> Tuple[int, int]:
        """Main broadcast method"""
        user_success, user_failure = await self.broadcast_users(client, text)
        group_success, group_failure = await self.broadcast_groups(client, text)
        
        return (
            user_success + group_success,
            user_failure + group_failure
        )

# Initialize singleton instance
broadcast_manager = BroadcastManager()

async def broadcast_message(client: Client, text: str) -> Tuple[int, int]:
    """Public interface for broadcasting"""
    return await broadcast_manager.broadcast_message(client, text)
