import re
from pyrogram import Client, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram import errors
from database import get_warnings, update_warnings
from bson import Int64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

url_pattern = re.compile(
    r'(?:(?:https?://|www\.)|(t\.me/))[a-zA-Z0-9.\-]+(?:\.[a-zA-Z]{2,})?(?:/[a-zA-Z0-9._%+-]*)?'
)

async def apply_punishment(client: Client, message, user_id: int, user_name: str, bio: str, settings: dict):
    """Apply punishment based on bio content and group settings."""
    if bio and re.search(url_pattern, bio):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            await message.reply_text("Please grant me delete permission.")
            logger.warning(f"Failed to delete message in chat {message.chat.id}: No permission")
            return

        if settings["type"] == "warn":
            warnings_count = await get_warnings(user_id, message.chat.id)
            warnings_count += 1
            await update_warnings(user_id, message.chat.id, warnings_count)
            sent_msg = await message.reply_text(
                f"{user_name} please remove any links from your bio. Warned {warnings_count}/{settings['warning_limit']}",
                parse_mode=enums.ParseMode.HTML
            )
            if warnings_count >= settings["warning_limit"]:
                try:
                    if settings["punishment"] == "mute":
                        await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions())
                        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute ✅", callback_data=f"unmute_{user_id}")]])
                        await sent_msg.edit(
                            f"{user_name} has been 🔇 muted for [ Link In Bio ].",
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML
                        )
                    elif settings["punishment"] == "ban":
                        await client.ban_chat_member(message.chat.id, user_id)
                        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unban ✅", callback_data=f"unban_{user_id}")]])
                        await sent_msg.edit(
                            f"{user_name} has been 🔨 banned for [ Link In Bio ].",
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML
                        )
                    elif settings["punishment"] == "delete":
                        async for msg in client.get_chat_history(message.chat.id, limit=10):
                            if msg.from_user.id == user_id:
                                try:
                                    await msg.delete()
                                except:
                                    pass
                        await sent_msg.edit(
                            f"{user_name}'s recent messages were deleted due to a link in their bio.",
                            parse_mode=enums.ParseMode.HTML
                        )
                    await update_warnings(user_id, message.chat.id, 0)  # Reset warnings
                except errors.ChatAdminRequired:
                    await sent_msg.edit(f"I don't have permission to {settings['punishment']} users.")
                    logger.error(f"Permission error for {settings['punishment']} in chat {message.chat.id}")
        elif settings["punishment"] == "mute":
            try:
                await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions())
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")]])
                await message.reply_text(
                    f"{user_name} has been 🔇 muted for [ Link In Bio ].",
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
            except errors.ChatAdminRequired:
                await message.reply_text("I don't have permission to mute users.")
                logger.error("No permission to mute in chat {message.chat.id}")
        elif settings["punishment"] == "ban":
            try:
                await client.ban_chat_member(message.chat.id, user_id)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                await message.reply_text(
                    f"{user_name} has been 🔨 banned for [ Link In Bio ].",
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
            except errors.ChatAdminRequired:
                await message.reply_text("I don't have permission to ban users.")
                logger.error("No permission to ban in chat {message.chat.id}")
        elif settings["punishment"] == "delete":
            async for msg in client.get_chat_history(message.chat.id, limit=10):
                if msg.from_user.id == user_id:
                    try:
                        await msg.delete()
                    except:
                        pass
            await message.reply_text(
                f"{user_name}'s recent messages were deleted due to a link in their bio.",
                parse_mode=enums.ParseMode.HTML
            )
    else:
        await update_warnings(user_id, message.chat.id, 0)  # Clear warnings
