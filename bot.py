from pyrogram import Client, filters, enums, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from database import get_group_settings, update_group_settings, store_user
from punishments import apply_punishment
from promo import broadcast_message
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) if os.getenv("OWNER_ID") else None
MONGO_URI = os.getenv("MONGO_URI")

# Validate required environment variables
if not all([API_ID, API_HASH, BOT_TOKEN, MONGO_URI]):
    print("ERROR: Missing required environment variables in .env file")
    exit(1)

# Initialize Pyrogram client
app = Client(
    "bio_link_monitor",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in a chat"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER
        ]
    except Exception as e:
        print(f"Admin check error: {e}")
        return False

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message):
    """Handle /start command in private chats"""
    try:
        # Store user in database
        await store_user(message.from_user.id)
        
        # Create response
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Support Group", url="https://t.me/UnfilteredZone")],
            [InlineKeyboardButton("➕ Add to Group", 
             url=f"https://t.me/{(await client.get_me()).username}?startgroup=true")]
        ])
        
        await message.reply_text(
            f"👋 Hello {message.from_user.first_name}!\n\n"
            "I'm a Bio Link Monitor Bot that helps keep your groups clean by monitoring user bios.\n\n"
            "🔹 Admins can configure me with /config in their groups\n"
            "🔹 I can warn, mute, or ban users with suspicious links in their bios",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Start command error: {e}")

@app.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_command(client: Client, message):
    """Handle broadcast messages (owner only)"""
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /broadcast <message>")
        return
    
    msg = await message.reply_text("📢 Starting broadcast...")
    broadcast_text = " ".join(message.command[1:])
    
    try:
        success, failure = await broadcast_message(client, broadcast_text)
        await msg.edit_text(
            f"✅ Broadcast completed!\n\n"
            f"• Success: {success}\n"
            f"• Failed: {failure}"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Broadcast failed: {str(e)}")
        print(f"Broadcast error: {e}")

@app.on_message(filters.command("config") & filters.group)
async def config_command(client: Client, message):
    """Handle group configuration"""
    try:
        if not await is_admin(client, message.chat.id, message.from_user.id):
            await message.delete()
            return await message.reply_text("❌ You need to be an admin to use this command.")
        
        settings = await get_group_settings(message.chat.id)
        current_punishment = settings.get("punishment", "warn")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn", callback_data="punish_warn")],
            [
                InlineKeyboardButton("🔇 Mute" + (" ✅" if current_punishment == "mute" else ""), 
                callback_data="punish_mute"),
                InlineKeyboardButton("🔨 Ban" + (" ✅" if current_punishment == "ban" else ""), 
                callback_data="punish_ban")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="config_close")]
        ])
        
        await message.reply_text(
            "⚙️ <b>Group Configuration</b>\n\n"
            "Select how to handle users with links in their bio:",
            reply_markup=keyboard
        )
        await message.delete()
    except Exception as e:
        print(f"Config command error: {e}")

@app.on_callback_query(filters.regex(r"^punish_"))
async def config_callback(client: Client, callback_query):
    """Handle configuration callbacks"""
    try:
        chat_id = callback_query.message.chat.id
        user_id = callback_query.from_user.id
        
        if not await is_admin(client, chat_id, user_id):
            await callback_query.answer("❌ You're not an admin!", show_alert=True)
            return
        
        action = callback_query.data.split("_")[1]
        
        if action == "close":
            await callback_query.message.delete()
            return
        
        # Update settings in database
        settings = await get_group_settings(chat_id)
        settings["punishment"] = action
        await update_group_settings(chat_id, settings)
        
        # Update the message to show new selection
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Warn", callback_data="punish_warn")],
            [
                InlineKeyboardButton("🔇 Mute" + (" ✅" if action == "mute" else ""), 
                callback_data="punish_mute"),
                InlineKeyboardButton("🔨 Ban" + (" ✅" if action == "ban" else ""), 
                callback_data="punish_ban")
            ],
            [InlineKeyboardButton("❌ Close", callback_data="config_close")]
        ])
        
        await callback_query.message.edit_text(
            "⚙️ <b>Group Configuration</b>\n\n"
            f"Selected action: <b>{action.capitalize()}</b>\n"
            "I will now automatically {action} users with links in their bio.",
            reply_markup=keyboard
        )
        await callback_query.answer(f"Set to {action}")
    except Exception as e:
        print(f"Config callback error: {e}")
        await callback_query.answer("❌ An error occurred", show_alert=True)

@app.on_message(filters.group & filters.new_chat_members)
async def new_member_handler(client: Client, message):
    """Handle new members joining"""
    try:
        bot_id = (await client.get_me()).id
        for member in message.new_chat_members:
            if member.id == bot_id:
                # Bot was added to a new group
                await message.reply_text(
                    "👋 Thanks for adding me!\n\n"
                    "I monitor user bios for suspicious links. "
                    "Admins can configure me with /config\n\n"
                    "Default action: Warn users with links in bio"
                )
                # Initialize group settings
                await get_group_settings(message.chat.id)
    except Exception as e:
        print(f"New member handler error: {e}")

@app.on_message(filters.group)
async def message_handler(client: Client, message):
    """Main message handler for bio checking"""
    try:
        if message.from_user.is_bot:
            return
            
        user_full = await client.get_chat(message.from_user.id)
        bio = user_full.bio or ""
        
        if not bio.strip():
            return
            
        settings = await get_group_settings(message.chat.id)
        await apply_punishment(client, message, message.from_user.id, bio, settings)
    except Exception as e:
        print(f"Message handler error: {e}")

if __name__ == "__main__":
    print("🤖 Starting Bio Link Monitor Bot...")
    try:
        app.run()
    except Exception as e:
        print(f"Failed to start bot: {e}")
        exit(1)
