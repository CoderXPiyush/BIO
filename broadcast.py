from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_group_settings, db
from bson import Int64
import os
import logging
from asyncio import sleep

# Setup logging
logger = logging.getLogger(__name__)

async def broadcast_start(client: Client, message):
    """Handle the /broadcast command to initiate the broadcast process."""
    await broadcast_command(client, message)

async def broadcast_callback_handler(client: Client, callback_query):
    """Handle callback queries for broadcast options."""
    await broadcast_callback(client, callback_query)

async def broadcast_command(client: Client, message):
    """Handle the /broadcast command to send messages to users and groups."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if the user is an admin in the current chat (for group) or the bot owner (for private)
    is_admin = False
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "creator"]:
            is_admin = True
    except Exception as e:
        logger.warning(f"Failed to check admin status for chat_id {chat_id}: {e}")
    if message.chat.type == "private" and user_id == int(os.getenv("OWNER_ID", 0)):  # Replace with your bot owner's ID
        is_admin = True
    if not is_admin:
        await message.reply_text("<b>❌ You are not authorized to use this command.</b>", parse_mode=enums.ParseMode.HTML)
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("To Users ✅", callback_data="broadcast_users"),
         InlineKeyboardButton("To Groups ✅", callback_data="broadcast_groups"),
         InlineKeyboardButton("To All ✅", callback_data="broadcast_all")],
        [InlineKeyboardButton("Cancel", callback_data="broadcast_cancel")]
    ])
    await message.reply_text(
        "<b>🔊 Broadcast Message</b>\n\nSelect the target for your broadcast:\n- Users: Send to all users who started the bot.\n- Groups: Send to all groups where the bot is added.\n- All: Send to both users and groups.",
        reply_markup=keyboard,
        parse_mode=enums.ParseMode.HTML
    )

async def broadcast_callback(client: Client, callback_query):
    """Handle callback queries for broadcast options."""
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    # Verify admin/owner again
    is_admin = False
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in ["administrator", "creator"]:
            is_admin = True
    except Exception as e:
        logger.warning(f"Failed to check admin status for callback in chat_id {chat_id}: {e}")
    if callback_query.message.chat.type == "private" and user_id == int(os.getenv("OWNER_ID", 0)):
        is_admin = True
    if not is_admin:
        await callback_query.answer("❌ You are not authorized", show_alert=True)
        return

    if data == "broadcast_cancel":
        await callback_query.message.edit_text("<b>🔊 Broadcast cancelled.</b>", parse_mode=enums.ParseMode.HTML)
        return

    # Prepare broadcast targets
    targets = []
    if data == "broadcast_users":
        async for user in db.users_collection.find():
            targets.append(user["user_id"])
        target_type = "users"
    elif data == "broadcast_groups":
        async for group in db.groups_collection.find():
            targets.append(group["chat_id"])
        target_type = "groups"
    elif data == "broadcast_all":
        async for user in db.users_collection.find():
            targets.append(user["user_id"])
        async for group in db.groups_collection.find():
            targets.append(group["chat_id"])
        target_type = "all"

    await callback_query.message.edit_text(
        f"<b>🔊 Broadcasting to {target_type}...</b>\nPlease reply with the message you want to send within 60 seconds.",
        parse_mode=enums.ParseMode.HTML
    )

    # Wait for the reply message
    @client.on_message(filters.reply & filters.user(user_id) & filters.text & ~filters.command, group=1)
    async def handle_broadcast_message(client, reply_message):
        broadcast_message = reply_message.text
        await reply_message.delete()
        await callback_query.message.edit_text(
            f"<b>🔊 Broadcasting '{broadcast_message}' to {len(targets)} {target_type}...</b>",
            parse_mode=enums.ParseMode.HTML
        )

        success_count = 0
        failed_count = 0
        for target in targets:
            try:
                await client.send_message(target, broadcast_message)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {target}: {e}")
                failed_count += 1

        await callback_query.message.edit_text(
            f"<b>🔊 Broadcast completed!</b>\n"
            f"Sent to {success_count} {target_type} successfully.\n"
            f"Failed for {failed_count} {target_type} due to errors.",
            parse_mode=enums.ParseMode.HTML
        )
        # Remove the temporary handler
        client.remove_handler(handle_broadcast_message)

    # Set a timeout to remove the handler if no reply is received
    await sleep(60)
    client.remove_handler(handle_broadcast_message)
    if callback_query.message.text.startswith("<b>🔊 Broadcasting to"):
        await callback_query.message.edit_text("<b>🔊 Broadcast cancelled due to timeout.</b>", parse_mode=enums.ParseMode.HTML)
