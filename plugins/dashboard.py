from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def setup(bot):
    """Setup dashboard plugin"""
    
    @bot.app.on_message(filters.command("dashboard"))
    async def dashboard_handler(client: Client, message: Message):
        user_id = message.from_user.id
        
        if await db.is_user_blocked(user_id):
            await message.reply("⛔ Access denied.")
            return
        
        try:
            stats = await db.get_statistics(user_id)
            settings = await db.get_settings(user_id)
            
            dashboard_text = (
                f"📊 **{message.from_user.first_name}'s Dashboard**\n\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📝 **Notes:** `{stats.get('total_notes', 0)}`\n"
                f"⏰ **Reminders:** `{stats.get('total_reminders', 0)}`\n"
                f"💾 **Backups:** `{stats.get('total_backups', 0)}`\n"
                f"⚡ **Commands Used:** `{stats.get('commands_used', 0)}`\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🌍 **Language:** {settings.get('language', 'en').upper()}\n"
                f"🕐 **Timezone:** {settings.get('timezone', 'UTC')}\n"
                f"🔔 **Notifications:** {'✅ On' if settings.get('notifications') else '❌ Off'}\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"🕐 Last Active: {stats.get('last_active', datetime.utcnow()).strftime('%Y-%m-%d %H:%M')}"
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📝 Notes", callback_data="notes_menu"),
                    InlineKeyboardButton("⏰ Reminders", callback_data="reminders_menu")
                ],
                [
                    InlineKeyboardButton("🎵 Music", callback_data="music_menu"),
                    InlineKeyboardButton("🌍 Translate", callback_data="translate_menu")
                ],
                [
                    InlineKeyboardButton("💾 Backup", callback_data="backup_menu"),
                    InlineKeyboardButton("📤 Restore", callback_data="restore_menu")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                    InlineKeyboardButton("📈 Stats", callback_data="stats")
                ],
                [
                    InlineKeyboardButton("🔌 Plugins", callback_data="plugins_menu"),
                    InlineKeyboardButton("📋 Logs", callback_data="logs_menu")
                ],
                [
                    InlineKeyboardButton("💬 Support", callback_data="support"),
                    InlineKeyboardButton("📝 Feedback", callback_data="feedback")
                ]
            ])
            
            await message.reply(dashboard_text, reply_markup=keyboard)
            await db.increment_command_usage(user_id)
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            await message.reply("❌ Error loading dashboard.")
