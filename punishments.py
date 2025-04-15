import re
from pyrogram import Client
from pyrogram import enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pyrogram import errors

url_pattern = re.compile(
    r'(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+-]*)*'
)

warnings = {}

async def apply_punishment(client: Client, message, user_id: int, user_name: str, bio: str, settings: dict):
    """Apply punishment based on bio content and group settings."""
    if bio and re.search(url_pattern, bio):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            await message.reply_text("ᴘʟᴇᴀꜱᴇ ɢʀᴀɴᴛ ᴍᴇ ᴅᴇʟᴇᴛᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ 🗑")
            return

        if settings["type"] == "warn":
            if user_id not in warnings:
                warnings[user_id] = 0
            warnings[user_id] += 1
            sent_msg = await message.reply_text(
                f"{user_name} ᴘʟᴇᴀꜱᴇ ʀᴇᴍᴏᴠᴇ ᴀɴʏ ʟɪɴᴋꜱ 🔗 ꜰʀᴏᴍ ʏᴏᴜʀ ʙɪᴏ. ⚠️ᴡᴀʀɴᴇᴅ {warnings[user_id]}/{settings['warning_limit']}",
                parse_mode=enums.ParseMode.HTML
            )
            if warnings[user_id] >= settings["warning_limit"]:
                try:
                    if settings["punishment"] == "mute":
                        await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions())
                        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ᴜɴᴍᴜᴛᴇ 🫰🏻", callback_data=f"unmute_{user_id}")]])
                        await sent_msg.edit(
                            f"{user_name} ʜᴀꜱ ʙᴇᴇɴ 🔇 ᴍᴜᴛᴇᴅ ꜰᴏʀ [ ʟɪɴᴋ ɪɴ ʙɪᴏ ].",
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML
                        )
                    elif settings["punishment"] == "ban":
                        await client.ban_chat_member(message.chat.id, user_id)
                        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ᴜɴʙᴀɴ 🪼", callback_data=f"unban_{user_id}")]])
                        await sent_msg.edit(
                            f"{user_name} ʜᴀꜱ ʙᴇᴇɴ 🔨 ʙᴀɴɴᴇᴅ ꜰᴏʀ [ ʟɪɴᴋ ɪɴ ʙɪᴏ ].",
                            reply_markup=keyboard,
                            parse_mode=enums.ParseMode.HTML
                        )
                    elif settings["punishment"] == "delete":
                        await sent_msg.edit(
                            f"{user_name}'ꜱ ᴍᴇꜱꜱᴀɢᴇꜱ ᴀʀᴇ ʙᴇɪɴɢ ᴅᴇʟᴇᴛᴇᴅ ᴅᴜᴇ ᴛᴏ ᴀ ʟɪɴᴋ ɪɴ ᴛʜᴇɪʀ ʙɪᴏ.",
                            parse_mode=enums.ParseMode.HTML
                        )
                except errors.ChatAdminRequired:
                    await sent_msg.edit(f"ɪ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ {settings['punishment']} ᴜꜱᴇʀꜱ.")
        elif settings["punishment"] == "mute":
            try:
                await client.restrict_chat_member(message.chat.id, user_id, ChatPermissions())
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")]])
                await message.reply_text(
                    f"{user_name} ʜᴀꜱ ʙᴇᴇɴ 🔇 ᴍᴜᴛᴇᴅ ꜰᴏʀ [ ʟɪɴᴋ ɪɴ ʙɪᴏ ].",
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
            except errors.ChatAdminRequired:
                await message.reply_text("ɪ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴍᴜᴛᴇ ᴜꜱᴇʀꜱ.")
        elif settings["punishment"] == "ban":
            try:
                await client.ban_chat_member(message.chat.id, user_id)
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                await message.reply_text(
                    f"{user_name} ʜᴀꜱ ʙᴇᴇɴ 🔨 ʙᴀɴɴᴇᴅ ꜰᴏʀ [ ʟɪɴᴋ ɪɴ ʙɪᴏ ].",
                    reply_markup=keyboard,
                    parse_mode=enums.ParseMode.HTML
                )
            except errors.ChatAdminRequired:
                await message.reply_text("ɪ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ʙᴀɴ ᴜꜱᴇʀꜱ.")
        elif settings["punishment"] == "delete":
            await message.reply_text(
                f"{user_name}'ꜱ ᴍᴇꜱꜱᴀɢᴇꜱ ᴀʀᴇ ʙᴇɪɴɢ ᴅᴇʟᴇᴛᴇᴅ ᴅᴜᴇ ᴛᴏ ᴀ ʟɪɴᴋ ɪɴ ᴛʜᴇɪʀ ʙɪᴏ.",
                parse_mode=enums.ParseMode.HTML
            )
    else:
        if user_id in warnings:
            del warnings[user_id]
