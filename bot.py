from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_group_settings, update_group_settings, store_user
from punishments import apply_punishment, warnings
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# User Client setup
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

async def is_admin(client, chat_id, user_id):
    async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
        if member.user.id == user_id:
            return True
    return False

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
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
    await message.reply_text(start_message, reply_markup=keyboard, parse_mode=enums.ParseMode.HTML)

@app.on_message(filters.group & filters.command("config"))
async def configure(client, message):
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

@app.on_callback_query()
async def callback_handler(client, callback_query):
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

@app.on_message(filters.group & filters.new_chat_members)
async def bot_added_to_group(client, message):
    chat_id = message.chat.id
    bot_id = (await client.get_me()).id
    for member in message.new_chat_members:
        if member.id == bot_id:
            settings = await get_group_settings(chat_id)
            await update_group_settings(chat_id, settings)
            await message.reply_text("Thank you for adding me! I'll monitor user bios for links. Admins can configure punishments with /config.")

@app.on_message(filters.group)
async def check_bio(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    user_full = await client.get_chat(user_id)
    bio = user_full.bio
    if user_full.username:
        user_name = f"@{user_full.username} [<code>{user_id}</code>]"
    else:
        user_name = f"{user_full.first_name} {user_full.last_name} [<code>{user_id}</code>]" if user_full.last_name else f"{user_full.first_name} [<code>{user_id}</code>]"

    settings = await get_group_settings(chat_id)
    await apply_punishment(client, message, user_id, user_name, bio, settings)

if __name__ == "__main__":
    app.run()
