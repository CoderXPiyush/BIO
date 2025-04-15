from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from database import get_group_settings, update_group_settings, store_user
from punishments import apply_punishment, warnings
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Debug: Print environment variables
print(f"DEBUG: API_ID = {os.getenv('API_ID')}")
print(f"DEBUG: API_HASH = {os.getenv('API_HASH')}")
print(f"DEBUG: BOT_TOKEN = {os.getenv('BOT_TOKEN')}")

# User Client setup
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

# Validate credentials
if not all([api_id, api_hash, bot_token]):
    print("ERROR: Missing API_ID, API_HASH, or BOT_TOKEN in .env")
    exit(1)

try:
    api_id = int(api_id)  # Ensure API_ID is an integer
except ValueError:
    print("ERROR: API_ID must be an integer")
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
    f"✨ ʜᴇʟʟᴏ {user_name}! ✨\n\n"
    "🤖 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ʙɪᴏ ʟɪɴᴋ ᴍᴏɴɪᴛᴏʀ ʙᴏᴛ! 🛡️\n"
    "ɪ ʜᴇʟᴘ ᴋᴇᴇᴘ ᴛᴇʟᴇɢʀᴀᴍ ɢʀᴏᴜᴘꜱ ᴄʟᴇᴀɴ ʙʏ 🕵️‍♂️ ᴍᴏɴɪᴛᴏʀɪɴɢ ᴜꜱᴇʀ ʙɪᴏꜱ ꜰᴏʀ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ʟɪɴᴋꜱ. 🔗\n\n"
    "⚙️ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴꜱ ᴄᴀɴ ᴄᴏɴꜰɪɢᴜʀᴇ ᴍᴇ ᴛᴏ ⚠️ ᴡᴀʀɴ | 🔇 ᴍᴜᴛᴇ | 🚫 ʙᴀɴ ᴜꜱᴇʀꜱ ᴡɪᴛʜ ʙɪᴏ ʟɪɴᴋꜱ.\n\n"
    "👇 ᴜꜱᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ᴊᴏɪɴ ᴏᴜʀ ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ᴏʀ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ!"
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
                 InlineKeyboardButton("Delete ✅" if current_punishment == "delete" else "Delete", callback_data="delete")],
                [InlineKeyboardButton("Close", callback_data="close")]
            ])
            await callback_query.message.edit_text("<b>Select punishment for users who have links in their bio:</b>", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
            await callback_query.answer()
            return

        if data == "warn":
            current_warning_limit = settings["warning_limit"]
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("3 ✅" if current_warning_limit == 3 else "3", callback_data="warn_3"), 
                 InlineKeyboardButton("4 ✅" if current_warning_limit == 4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton("5 ✅" if current_warning_limit == 5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")]
            ])
            await callback_query.message.edit_text("<b>Select the number of warnings before punishment:</b>", reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)
            return

        if data in ["mute", "ban", "delete"]:
            settings["type"] = "warn"
            settings["punishment"] = data
            await update_group_settings(chat_id, settings)
            selected_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Warn", callback_data="warn")],
                [InlineKeyboardButton("Mute ✅" if data == "mute" else "Mute", callback_data="mute"), 
                 InlineKeyboardButton("Ban ✅" if data == "ban" else "Ban", callback_data="ban"),
                 InlineKeyboardButton("Delete ✅" if data == "delete" else "Delete", callback_data="delete")],
                [InlineKeyboardButton("Close", callback_data="close")]
            ])
            await callback_query.message.edit_text("<b>Punishment selected:</b>", reply_markup=selected_keyboard, parse_mode=enums.ParseMode.HTML)
            await callback_query.answer()
        elif data.startswith("warn_"):
            num_warnings = int(data.split("_")[1])
            settings["type"] = "warn"
            settings["warning_limit"] = num_warnings
            await update_group_settings(chat_id, settings)
            selected_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("3 ✅" if num_warnings == 3 else "3", callback_data="warn_3"), 
                 InlineKeyboardButton("4 ✅" if num_warnings == 4 else "4", callback_data="warn_4"),
                 InlineKeyboardButton("5 ✅" if num_warnings == 5 else "5", callback_data="warn_5")],
                [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")]
            ])
            await callback_query.message.edit_text(f"<b>Warning limit set to {num_warnings}</b>", reply_markup=selected_keyboard, parse_mode=enums.ParseMode.HTML)
            await callback_query.answer()
        elif data.startswith("unmute_"):
            target_user_id = int(data.split("_")[1])
            target_user = await client.get_chat(target_user_id)
            target_user_name = f"{target_user.first_name} {target_user.last_name}" if target_user.last_name else target_user.first_name
            try:
                await client.restrict_chat_member(chat_id, target_user_id, ChatPermissions(can_send_messages=True))
                await callback_query.message.edit(f"{target_user_name} [<code>{target_user_id}</code>] has been unmuted", parse_mode=enums.ParseMode.HTML)
            except errors.ChatAdminRequired:
                await callback_query.message.edit("I don't have permission to unmute users.")
            await callback_query.answer()
        elif data.startswith("unban_"):
            target_user_id = int(data.split("_")[1])
            target_user = await client.get_chat(target_user_id)
            target_user_name = f"{target_user.first_name} {target_user.last_name}" if target_user.last_name else target_user.first_name
            try:
                await client.unban_chat_member(chat_id, target_user_id)
                await callback_query.message.edit(f"{target_user_name} [<code>{target_user_id}</code>] has been unbanned", parse_mode=enums.ParseMode.HTML)
            except errors.ChatAdminRequired:
                await callback_query.message.edit("I don't have permission to unban users.")
            await callback_query.answer()
    except Exception as e:
        print(f"ERROR: Failed in callback_handler: {e}")
        await callback_query.answer("An error occurred", show_alert=True)

@app.on_message(filters.group & filters.new_chat_members)
async def bot_added_to_group(client, message):
    try:
        chat_id = message.chat.id
        bot_id = (await client.get_me()).id
        for member in message.new_chat_members:
            if member.id == bot_id:
                settings = await get_group_settings(chat_id)
                await update_group_settings(chat_id, settings)
                await message.reply_text("Thank you for adding me! I'll monitor user bios for links. Admins can configure punishments with /config.")
    except Exception as e:
        print(f"ERROR: Failed in bot_added_to_group: {e}")

@app.on_message(filters.group)
async def check_bio(client, message):
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id

        user_full = await client.get_chat(user_id)
        bio = user_full.bio if user_full.bio else ""
        if user_full.username:
            user_name = f"@{user_full.username} [<code>{user_id}</code>]"
        else:
            user_name = f"{user_full.first_name} {user_full.last_name} [<code>{user_id}</code>]" if user_full.last_name else f"{user_full.first_name} [<code>{user_id}</code>]"

        settings = await get_group_settings(chat_id)
        await apply_punishment(client, message, user_id, user_name, bio, settings)
    except Exception as e:
        print(f"ERROR: Failed in check_bio: {e}")

if __name__ == "__main__":
    print("DEBUG: Starting bot...")
    try:
        app.run()
    except errors.AuthKeyUnregistered:
        print("ERROR: Invalid API_ID, API_HASH, or BOT_TOKEN. Please verify credentials.")
        exit(1)
    except Exception as e:
        print(f"ERROR: Failed to start bot: {str(e)}")
        exit(1)
