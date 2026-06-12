from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def setup(bot):
    """Setup start plugin"""
    
    @bot.app.on_message(filters.command("start"))
    async def start_handler(client: Client, message: Message):
        user_id = message.from_user.id
        
        try:
            user = await db.get_user(user_id)
            
            if not user:
                # New user registration
                user_data = {
                    "user_id": user_id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "language_code": message.from_user.language_code
                }
                
                success = await db.create_user(user_data)
                
                if success:
                    welcome_text = (
                        f"🎉 **Welcome to NOVITA, {message.from_user.first_name}!**\n\n"
                        f"Your personal workspace has been created.\n\n"
                        f"✨ **Features:**\n"
                        f"• 📝 Smart Notes\n"
                        f"• ⏰ Reminders\n"
                        f"• 🎵 Music Search\n"
                        f"• 💾 Auto Backup\n"
                        f"• 🌍 Translation\n"
                        f"• 📊 Statistics\n\n"
                        f"🔒 Your data is completely private and isolated.\n\n"
                        f"Use /dashboard to get started!"
                    )
                else:
                    welcome_text = "❌ Error creating account. Please try again later."
            else:
                welcome_text = (
                    f"👋 **Welcome back, {message.from_user.first_name}!**\n\n"
                    f"Your NOVITA workspace is ready.\n"
                    f"Use /dashboard to continue."
                )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
                 InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
                [InlineKeyboardButton("📈 Statistics", callback_data="stats"),
                 InlineKeyboardButton("📚 Help", callback_data="help")]
            ])
            
            await message.reply(welcome_text, reply_markup=keyboard)
            
            await db.add_log(user_id, {
                "action": "registration" if not user else "login",
                "message": "User started bot"
            })
            
        except Exception as e:
            logger.error(f"Start handler error: {e}")
            await message.reply("❌ An error occurred. Please try again.")
