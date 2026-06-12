import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.errors import FloodWait, RPCError
from config import Config
from database import db
import importlib
import os
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('novita.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NovitaBot:
    def __init__(self):
        self.app = Client(
            "novita_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=10
        )
        self.plugins = {}
        self.rate_limits = defaultdict(list)
        self.start_time = datetime.utcnow()
        
    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting NOVITA Bot...")
            await db.connect()
            await self.load_plugins()
            self.register_handlers()
            await self.app.start()
            logger.info("NOVITA Bot started successfully!")
            await self.send_startup_message()
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)
    
    async def stop(self):
        """Stop the bot"""
        try:
            logger.info("Stopping NOVITA Bot...")
            await self.send_shutdown_message()
            await db.disconnect()
            await self.app.stop()
            logger.info("NOVITA Bot stopped successfully!")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    async def load_plugins(self):
        """Load all plugins dynamically"""
        logger.info("Loading plugins...")
        plugin_dir = "plugins"
        
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)
            logger.warning(f"Created plugins directory: {plugin_dir}")
        
        for plugin_name in Config.ENABLED_PLUGINS:
            try:
                module = importlib.import_module(f"plugins.{plugin_name}")
                if hasattr(module, 'setup'):
                    await module.setup(self)
                    self.plugins[plugin_name] = module
                    logger.info(f"Loaded plugin: {plugin_name}")
                else:
                    logger.warning(f"Plugin {plugin_name} has no setup function")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")
    
    def register_handlers(self):
        """Register all message and callback handlers"""
        # Main menu handlers
        self.app.add_handler(MessageHandler(self.start_command, filters.command("start")))
        self.app.add_handler(MessageHandler(self.help_command, filters.command("help")))
        self.app.add_handler(MessageHandler(self.dashboard_command, filters.command("dashboard")))
        self.app.add_handler(MessageHandler(self.settings_command, filters.command("settings")))
        self.app.add_handler(MessageHandler(self.plugins_command, filters.command("plugins")))
        self.app.add_handler(MessageHandler(self.stats_command, filters.command("stats")))
        self.app.add_handler(MessageHandler(self.notes_command, filters.command("notes")))
        self.app.add_handler(MessageHandler(self.reminders_command, filters.command("reminders")))
        self.app.add_handler(MessageHandler(self.music_command, filters.command("music")))
        self.app.add_handler(MessageHandler(self.profile_command, filters.command("profile")))
        self.app.add_handler(MessageHandler(self.backup_command, filters.command("backup")))
        self.app.add_handler(MessageHandler(self.restore_command, filters.command("restore")))
        self.app.add_handler(MessageHandler(self.logs_command, filters.command("logs")))
        self.app.add_handler(MessageHandler(self.support_command, filters.command("support")))
        self.app.add_handler(MessageHandler(self.feedback_command, filters.command("feedback")))
        self.app.add_handler(MessageHandler(self.language_command, filters.command("language")))
        
        # Owner commands
        self.app.add_handler(MessageHandler(self.block_command, filters.command("block") & filters.user(Config.OWNER_ID)))
        self.app.add_handler(MessageHandler(self.unblock_command, filters.command("unblock") & filters.user(Config.OWNER_ID)))
        self.app.add_handler(MessageHandler(self.broadcast_command, filters.command("broadcast") & filters.user(Config.OWNER_ID)))
        
        # Callback query handler
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Error handler
        self.app.add_handler(MessageHandler(self.error_handler, filters.all))
    
    async def check_rate_limit(self, user_id: int) -> bool:
        """Check rate limiting for user"""
        now = time.time()
        user_requests = self.rate_limits[user_id]
        
        # Remove old requests
        user_requests = [req for req in user_requests if req > now - 60]
        self.rate_limits[user_id] = user_requests
        
        if len(user_requests) >= Config.RATE_LIMIT:
            return False
        
        user_requests.append(now)
        return True
    
    async def check_user_access(self, user_id: int) -> bool:
        """Check if user has access"""
        return not await db.is_user_blocked(user_id)
    
    async def start_command(self, client: Client, message: Message):
        """Handle /start command"""
        user_id = message.from_user.id
        
        if not await self.check_rate_limit(user_id):
            await message.reply("⚠️ Rate limit exceeded. Please wait.")
            return
        
        try:
            user = await db.get_user(user_id)
            
            if not user:
                # Create new user
                user_data = {
                    "user_id": user_id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "language_code": message.from_user.language_code
                }
                await db.create_user(user_data)
                
                welcome_text = (
                    f"🎉 **Welcome to NOVITA!**\n\n"
                    f"Hi {message.from_user.first_name}!\n\n"
                    f"I'm your personal assistant bot with powerful features:\n"
                    f"• 📝 Notes management\n"
                    f"• ⏰ Smart reminders\n"
                    f"• 🎵 Music search\n"
                    f"• 📊 Personal statistics\n"
                    f"• 💾 Data backup & restore\n"
                    f"• 🌍 Language translation\n"
                    f"• And much more!\n\n"
                    f"Use /dashboard to see your control panel."
                )
            else:
                welcome_text = (
                    f"👋 **Welcome back, {message.from_user.first_name}!**\n\n"
                    f"Your NOVITA workspace is ready.\n"
                    f"Use /dashboard to continue."
                )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                 InlineKeyboardButton("📈 Stats", callback_data="stats")],
                [InlineKeyboardButton("❓ Help", callback_data="help")]
            ])
            
            await message.reply(welcome_text, reply_markup=keyboard)
            await db.add_log(user_id, {"action": "start", "message": "Bot started"})
            await db.increment_command_usage(user_id)
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.reply("❌ An error occurred. Please try again.")
    
    async def dashboard_command(self, client: Client, message: Message):
        """Show user dashboard"""
        user_id = message.from_user.id
        
        if not await self.check_user_access(user_id):
            await message.reply("⛔ You are blocked from using this bot.")
            return
        
        try:
            stats = await db.get_statistics(user_id)
            settings = await db.get_settings(user_id)
            
            dashboard_text = (
                f"📊 **{message.from_user.first_name}'s Dashboard**\n\n"
                f"📝 Notes: {stats.get('total_notes', 0)}\n"
                f"⏰ Reminders: {stats.get('total_reminders', 0)}\n"
                f"💾 Backups: {stats.get('total_backups', 0)}\n"
                f"⚡ Commands Used: {stats.get('commands_used', 0)}\n"
                f"🌍 Language: {settings.get('language', 'en').upper()}\n"
                f"🕐 Timezone: {settings.get('timezone', 'UTC')}\n"
                f"🔔 Notifications: {'✅ On' if settings.get('notifications') else '❌ Off'}\n\n"
                f"Last Active: {stats.get('last_active', datetime.utcnow()).strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Notes", callback_data="notes_menu"),
                 InlineKeyboardButton("⏰ Reminders", callback_data="reminders_menu")],
                [InlineKeyboardButton("🎵 Music", callback_data="music_menu"),
                 InlineKeyboardButton("🌍 Translate", callback_data="translate_menu")],
                [InlineKeyboardButton("💾 Backup", callback_data="backup_menu"),
                 InlineKeyboardButton("📤 Restore", callback_data="restore_menu")],
                [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
                 InlineKeyboardButton("📈 Stats", callback_data="stats")],
                [InlineKeyboardButton("🔌 Plugins", callback_data="plugins_menu"),
                 InlineKeyboardButton("📋 Logs", callback_data="logs_menu")]
            ])
            
            await message.reply(dashboard_text, reply_markup=keyboard)
            await db.increment_command_usage(user_id)
            
        except Exception as e:
            logger.error(f"Error in dashboard: {e}")
            await message.reply("❌ Error loading dashboard.")
    
    async def help_command(self, client: Client, message: Message):
        """Show help menu"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        help_text = (
            "📚 **NOVITA Help Center**\n\n"
            "**Main Commands:**\n"
            "/start - Start the bot\n"
            "/dashboard - Your control panel\n"
            "/profile - View your profile\n"
            "/settings - Configure settings\n"
            "/plugins - Manage plugins\n"
            "/stats - Your statistics\n\n"
            "**Features:**\n"
            "/notes - Personal notes\n"
            "/reminders - Smart reminders\n"
            "/music - Music search\n"
            "/translate - Text translation\n"
            "/polls - Create polls\n"
            "/backup - Backup data\n"
            "/restore - Restore backup\n"
            "/logs - Activity logs\n"
            "/language - Change language\n"
            "/support - Get support\n"
            "/feedback - Send feedback\n\n"
            "**Media Tools:**\n"
            "/sticker - Sticker utilities\n"
            "/media - Media tools\n"
            "/download - Download helper\n"
            "/upload - Upload helper"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
             InlineKeyboardButton("💬 Support", callback_data="support")]
        ])
        
        await message.reply(help_text, reply_markup=keyboard)
    
    async def settings_command(self, client: Client, message: Message):
        """Settings command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        # This will be handled by settings plugin
        await message.reply("⚙️ Opening settings... Use the buttons below.")
    
    async def plugins_command(self, client: Client, message: Message):
        """Plugins management command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        plugins_data = await db.get_plugins(user_id)
        if not plugins_data:
            await message.reply("❌ Error loading plugins.")
            return
        
        enabled = plugins_data.get("enabled_plugins", [])
        
        text = "🔌 **Plugin Manager**\n\n"
        text += "Manage your plugins:\n\n"
        
        for plugin in Config.ENABLED_PLUGINS:
            status = "✅" if plugin in enabled else "❌"
            text += f"{status} {plugin}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Toggle Plugins", callback_data="toggle_plugins")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(text, reply_markup=keyboard)
    
    async def stats_command(self, client: Client, message: Message):
        """Statistics command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        stats = await db.get_statistics(user_id)
        if not stats:
            await message.reply("❌ No statistics available.")
            return
        
        stats_text = (
            f"📈 **Your Statistics**\n\n"
            f"📝 Total Notes: {stats.get('total_notes', 0)}\n"
            f"⏰ Total Reminders: {stats.get('total_reminders', 0)}\n"
            f"💾 Total Backups: {stats.get('total_backups', 0)}\n"
            f"⚡ Commands Used: {stats.get('commands_used', 0)}\n"
            f"🕐 Last Active: {stats.get('last_active', datetime.utcnow()).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"📅 Member Since: {stats.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(stats_text, reply_markup=keyboard)
    
    async def notes_command(self, client: Client, message: Message):
        """Notes command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        notes = await db.get_notes(user_id, limit=5)
        
        if not notes:
            await message.reply(
                "📝 You have no notes yet!\n\n"
                "Create a note by sending:\n"
                "`/addnote Your note text here`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Add Note", callback_data="add_note")
                ]])
            )
            return
        
        text = "📝 **Your Recent Notes**\n\n"
        for i, note in enumerate(notes, 1):
            text += f"{i}. {note.get('content', 'No content')[:100]}\n"
            text += f"   📅 {note.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d')}\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Note", callback_data="add_note"),
             InlineKeyboardButton("📋 View All", callback_data="notes_menu")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(text, reply_markup=keyboard)
    
    async def reminders_command(self, client: Client, message: Message):
        """Reminders command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        reminders = await db.get_reminders(user_id)
        
        if not reminders:
            await message.reply(
                "⏰ You have no active reminders!\n\n"
                "Create one by sending:\n"
                "`/remind 30m Check email`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Add Reminder", callback_data="add_reminder")
                ]])
            )
            return
        
        text = "⏰ **Your Reminders**\n\n"
        for i, reminder in enumerate(reminders[:10], 1):
            text += f"{i}. {reminder.get('message', 'No message')}\n"
            text += f"   ⏰ {reminder.get('remind_at', datetime.utcnow()).strftime('%Y-%m-%d %H:%M')}\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add", callback_data="add_reminder"),
             InlineKeyboardButton("🗑️ Delete", callback_data="delete_reminder")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(text, reply_markup=keyboard)
    
    async def music_command(self, client: Client, message: Message):
        """Music command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        await message.reply(
            "🎵 **Music Search**\n\n"
            "Send me a song name or artist to search!\n\n"
            "Usage: `/music search song name`\n"
            "Or: `/music info` for last search",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")
            ]])
        )
    
    async def profile_command(self, client: Client, message: Message):
        """Profile command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        user = message.from_user
        db_user = await db.get_user(user_id)
        
        profile_text = (
            f"👤 **Your Profile**\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"👤 Name: {user.first_name} {user.last_name or ''}\n"
            f"📛 Username: @{user.username or 'None'}\n"
            f"🌍 Language: {user.language_code or 'en'}\n"
            f"📅 Joined: {db_user.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d') if db_user else 'Unknown'}\n"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
             InlineKeyboardButton("📈 Stats", callback_data="stats")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(profile_text, reply_markup=keyboard)
    
    async def backup_command(self, client: Client, message: Message):
        """Backup command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Create Backup", callback_data="create_backup")],
            [InlineKeyboardButton("📋 View Backups", callback_data="backup_menu")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(
            "💾 **Backup System**\n\n"
            "Create backups of your data safely.\n"
            "Your backups are private and encrypted.",
            reply_markup=keyboard
        )
    
    async def restore_command(self, client: Client, message: Message):
        """Restore command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        backups = await db.get_backups(user_id)
        
        if not backups:
            await message.reply("❌ No backups found to restore.")
            return
        
        text = "📤 **Restore Backup**\n\nSelect a backup to restore:\n\n"
        
        buttons = []
        for backup in backups[:5]:
            buttons.append([InlineKeyboardButton(
                f"📦 {backup.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d %H:%M')}",
                callback_data=f"restore_{backup['backup_id']}"
            )])
        
        buttons.append([InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")])
        keyboard = InlineKeyboardMarkup(buttons)
        
        await message.reply(text, reply_markup=keyboard)
    
    async def logs_command(self, client: Client, message: Message):
        """Logs command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        logs = await db.get_logs(user_id, limit=10)
        
        if not logs:
            await message.reply("📋 No activity logs yet.")
            return
        
        text = "📋 **Recent Activity**\n\n"
        for log in logs:
            text += f"• {log.get('action', 'Unknown')} - "
            text += f"{log.get('timestamp', datetime.utcnow()).strftime('%H:%M:%S')}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(text, reply_markup=keyboard)
    
    async def support_command(self, client: Client, message: Message):
        """Support command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        await message.reply(
            "💬 **Support Center**\n\n"
            "Need help? Contact us:\n"
            "• Use /feedback to send feedback\n"
            "• Check /help for commands\n"
            "• Report bugs via support",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Send Feedback", callback_data="feedback"),
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")
            ]])
        )
    
    async def feedback_command(self, client: Client, message: Message):
        """Feedback command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        await message.reply(
            "📝 **Send Feedback**\n\n"
            "Please send your feedback, suggestions, or bug reports.\n"
            "Just type your message after this.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")
            ]])
        )
    
    async def language_command(self, client: Client, message: Message):
        """Language settings command"""
        user_id = message.from_user.id
        await db.increment_command_usage(user_id)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
             InlineKeyboardButton("🇪🇸 Spanish", callback_data="lang_es")],
            [InlineKeyboardButton("🇫🇷 French", callback_data="lang_fr"),
             InlineKeyboardButton("🇩🇪 German", callback_data="lang_de")],
            [InlineKeyboardButton("🇮🇹 Italian", callback_data="lang_it"),
             InlineKeyboardButton("🇵🇹 Portuguese", callback_data="lang_pt")],
            [InlineKeyboardButton("🇷🇺 Russian", callback_data="lang_ru"),
             InlineKeyboardButton("🇯🇵 Japanese", callback_data="lang_ja")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply("🌍 **Select Language**", reply_markup=keyboard)
    
    # Owner Commands
    async def block_command(self, client: Client, message: Message):
        """Owner: Block user"""
        if message.from_user.id != Config.OWNER_ID:
            return
        
        try:
            user_id = int(message.command[1]) if len(message.command) > 1 else None
            if not user_id:
                await message.reply("❌ Usage: /block user_id")
                return
            
            await db.block_user(user_id)
            await message.reply(f"✅ User {user_id} blocked successfully.")
            
            # Log to channel
            await client.send_message(
                Config.LOG_CHANNEL,
                f"🚫 User {user_id} has been blocked."
            )
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
    
    async def unblock_command(self, client: Client, message: Message):
        """Owner: Unblock user"""
        if message.from_user.id != Config.OWNER_ID:
            return
        
        try:
            user_id = int(message.command[1]) if len(message.command) > 1 else None
            if not user_id:
                await message.reply("❌ Usage: /unblock user_id")
                return
            
            await db.unblock_user(user_id)
            await message.reply(f"✅ User {user_id} unblocked successfully.")
            
            await client.send_message(
                Config.LOG_CHANNEL,
                f"✅ User {user_id} has been unblocked."
            )
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
    
    async def broadcast_command(self, client: Client, message: Message):
        """Owner: Broadcast message to all users"""
        if message.from_user.id != Config.OWNER_ID:
            return
        
        try:
            broadcast_text = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
            if not broadcast_text:
                await message.reply("❌ Usage: /broadcast Your message here")
                return
            
            users = await db.db.users.find({}).to_list(length=None)
            success = 0
            failed = 0
            
            await message.reply(f"📢 Broadcasting to {len(users)} users...")
            
            for user in users:
                try:
                    await client.send_message(user['user_id'], f"📢 **Announcement**\n\n{broadcast_text}")
                    success += 1
                except:
                    failed += 1
                await asyncio.sleep(0.05)  # Avoid flood
            
            await message.reply(f"✅ Broadcast complete!\nSent: {success}\nFailed: {failed}")
            
        except Exception as e:
            await message.reply(f"❌ Error: {e}")
    
    async def handle_callback(self, client: Client, callback: CallbackQuery):
        """Handle all callback queries"""
        user_id = callback.from_user.id
        
        if not await self.check_user_access(user_id):
            await callback.answer("⛔ Access denied.", show_alert=True)
            return
        
        data = callback.data
        
        try:
            if data == "dashboard":
                await self.dashboard_callback(client, callback)
            elif data == "settings":
                await self.settings_callback(client, callback)
            elif data == "stats":
                await self.stats_callback(client, callback)
            elif data == "help":
                await self.help_callback(client, callback)
            elif data == "notes_menu":
                await self.notes_menu_callback(client, callback)
            elif data == "reminders_menu":
                await self.reminders_menu_callback(client, callback)
            elif data == "music_menu":
                await self.music_menu_callback(client, callback)
            elif data == "backup_menu":
                await self.backup_menu_callback(client, callback)
            elif data == "restore_menu":
                await self.restore_menu_callback(client, callback)
            elif data == "plugins_menu":
                await self.plugins_menu_callback(client, callback)
            elif data == "logs_menu":
                await self.logs_menu_callback(client, callback)
            elif data == "support":
                await self.support_callback(client, callback)
            elif data == "feedback":
                await self.feedback_callback(client, callback)
            elif data.startswith("lang_"):
                await self.language_callback(client, callback)
            elif data == "add_note":
                await callback.answer("📝 Send your note text after /addnote command")
            elif data == "add_reminder":
                await callback.answer("⏰ Use: /remind [time] [message]")
            elif data == "create_backup":
                await self.create_backup_callback(client, callback)
            elif data == "toggle_plugins":
                await self.toggle_plugins_callback(client, callback)
            else:
                await callback.answer("Unknown action")
        except Exception as e:
            logger.error(f"Callback error: {e}")
            await callback.answer("❌ Error processing request", show_alert=True)
    
    # Callback Handlers
    async def dashboard_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        stats = await db.get_statistics(user_id)
        settings = await db.get_settings(user_id)
        
        dashboard_text = (
            f"📊 **{callback.from_user.first_name}'s Dashboard**\n\n"
            f"📝 Notes: {stats.get('total_notes', 0)}\n"
            f"⏰ Reminders: {stats.get('total_reminders', 0)}\n"
            f"💾 Backups: {stats.get('total_backups', 0)}\n"
            f"⚡ Commands: {stats.get('commands_used', 0)}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Notes", callback_data="notes_menu"),
             InlineKeyboardButton("⏰ Reminders", callback_data="reminders_menu")],
            [InlineKeyboardButton("🎵 Music", callback_data="music_menu"),
             InlineKeyboardButton("💾 Backup", callback_data="backup_menu")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
             InlineKeyboardButton("🔌 Plugins", callback_data="plugins_menu")]
        ])
        
        await callback.message.edit_text(dashboard_text, reply_markup=keyboard)
        await callback.answer()
    
    async def settings_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        settings = await db.get_settings(user_id)
        
        notif_status = "✅ ON" if settings.get('notifications') else "❌ OFF"
        
        text = (
            f"⚙️ **Settings**\n\n"
            f"🔔 Notifications: {notif_status}\n"
            f"🌍 Language: {settings.get('language', 'en')}\n"
            f"🕐 Timezone: {settings.get('timezone', 'UTC')}\n"
            f"🎨 Theme: {settings.get('theme', 'default')}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Toggle Notifications", callback_data="toggle_notifications")],
            [InlineKeyboardButton("🌍 Language", callback_data="lang_settings"),
             InlineKeyboardButton("🕐 Timezone", callback_data="timezone_settings")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def stats_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        stats = await db.get_statistics(user_id)
        
        text = (
            f"📈 **Statistics**\n\n"
            f"📝 Notes: {stats.get('total_notes', 0)}\n"
            f"⏰ Reminders: {stats.get('total_reminders', 0)}\n"
            f"💾 Backups: {stats.get('total_backups', 0)}\n"
            f"⚡ Commands: {stats.get('commands_used', 0)}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def help_callback(self, client: Client, callback: CallbackQuery):
        await callback.answer("Opening help...")
        # This would redirect to help menu
    
    async def notes_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        notes = await db.get_notes(user_id, limit=10)
        
        if not notes:
            text = "📝 No notes yet. Create one with /addnote"
        else:
            text = "📝 **Your Notes**\n\n"
            for i, note in enumerate(notes, 1):
                text += f"{i}. {note.get('content', '')[:100]}\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Note", callback_data="add_note"),
             InlineKeyboardButton("🗑️ Delete", callback_data="delete_note")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def reminders_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        reminders = await db.get_reminders(user_id)
        
        if not reminders:
            text = "⏰ No active reminders."
        else:
            text = "⏰ **Your Reminders**\n\n"
            for reminder in reminders[:10]:
                text += f"• {reminder.get('message', '')}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add", callback_data="add_reminder"),
             InlineKeyboardButton("🗑️ Delete", callback_data="delete_reminder")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def music_menu_callback(self, client: Client, callback: CallbackQuery):
        text = "🎵 **Music Search**\n\nSend a song name to search!"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def backup_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        backups = await db.get_backups(user_id)
        
        if not backups:
            text = "💾 No backups yet."
        else:
            text = "💾 **Your Backups**\n\n"
            for backup in backups[:10]:
                text += f"• {backup.get('created_at', '').strftime('%Y-%m-%d %H:%M')}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Create Backup", callback_data="create_backup")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def restore_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        backups = await db.get_backups(user_id)
        
        if not backups:
            await callback.answer("No backups to restore")
            return
        
        text = "📤 Select backup to restore:"
        buttons = []
        for backup in backups[:5]:
            buttons.append([InlineKeyboardButton(
                backup.get('created_at', '').strftime('%Y-%m-%d %H:%M'),
                callback_data=f"restore_{backup['backup_id']}"
            )])
        
        buttons.append([InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")])
        keyboard = InlineKeyboardMarkup(buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def plugins_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        plugins_data = await db.get_plugins(user_id)
        enabled = plugins_data.get("enabled_plugins", []) if plugins_data else []
        
        text = "🔌 **Plugin Manager**\n\n"
        for plugin in Config.ENABLED_PLUGINS:
            status = "✅" if plugin in enabled else "❌"
            text += f"{status} {plugin}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Toggle Plugins", callback_data="toggle_plugins")],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def logs_menu_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        logs = await db.get_logs(user_id, limit=15)
        
        if not logs:
            text = "📋 No activity logs."
        else:
            text = "📋 **Recent Activity**\n\n"
            for log in logs:
                text += f"• {log.get('action', 'Unknown')}\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def support_callback(self, client: Client, callback: CallbackQuery):
        text = "💬 **Support**\n\nUse /feedback to send feedback\nUse /help for commands"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Feedback", callback_data="feedback"),
             InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    
    async def feedback_callback(self, client: Client, callback: CallbackQuery):
        await callback.answer("Please send your feedback message")
    
    async def language_callback(self, client: Client, callback: CallbackQuery):
        lang_code = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        await db.update_settings(user_id, {"language": lang_code})
        await callback.answer(f"✅ Language set to {lang_code.upper()}")
        await self.settings_callback(client, callback)
    
    async def create_backup_callback(self, client: Client, callback: CallbackQuery):
        user_id = callback.from_user.id
        
        try:
            # Gather user data
            notes = await db.get_notes(user_id, limit=1000)
            reminders = await db.get_reminders(user_id)
            settings = await db.get_settings(user_id)
            
            backup_data = {
                "backup_id": str(int(time.time())),
                "user_id": user_id,
                "notes": notes,
                "reminders": reminders,
                "settings": settings,
                "created_at": datetime.utcnow()
            }
            
            backup_id = await db.create_backup(user_id, backup_data)
            
            if backup_id:
                await callback.answer("✅ Backup created successfully!", show_alert=True)
                await self.backup_menu_callback(client, callback)
            else:
                await callback.answer("❌ Failed to create backup", show_alert=True)
        except Exception as e:
            logger.error(f"Backup error: {e}")
            await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    async def toggle_plugins_callback(self, client: Client, callback: CallbackQuery):
        await callback.answer("Use /plugins command to toggle individual plugins")
    
    async def send_startup_message(self):
        """Send startup notification to log channel"""
        try:
            await self.app.send_message(
                Config.LOG_CHANNEL,
                f"🟢 **NOVITA Bot Started**\n\n"
                f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"📦 Version: 1.0.0\n"
                f"🔧 Status: Operational"
            )
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")
    
    async def send_shutdown_message(self):
        """Send shutdown notification"""
        try:
            await self.app.send_message(
                Config.LOG_CHANNEL,
                f"🔴 **NOVITA Bot Stopped**\n\n"
                f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
        except:
            pass
    
    async def error_handler(self, client: Client, message: Message):
        """Global error handler"""
        if message.command and message.command[0] not in [
            "start", "help", "dashboard", "settings", "plugins", "stats",
            "notes", "reminders", "music", "profile", "backup", "restore",
            "logs", "support", "feedback", "language", "block", "unblock", "broadcast"
        ]:
            await message.reply(
                "❓ Unknown command. Use /help to see available commands.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📚 Help", callback_data="help")
                ]])
            )

# Main entry point
async def main():
    bot = NovitaBot()
    try:
        await bot.start()
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
