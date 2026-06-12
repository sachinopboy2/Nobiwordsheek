from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

async def setup(bot):
    """Setup notes plugin"""
    
    @bot.app.on_message(filters.command("notes"))
    async def notes_handler(client: Client, message: Message):
        user_id = message.from_user.id
        
        if await db.is_user_blocked(user_id):
            await message.reply("⛔ Access denied.")
            return
        
        notes = await db.get_notes(user_id, limit=10)
        
        if not notes:
            await message.reply(
                "📝 **No Notes Yet**\n\n"
                "Create a note:\n"
                "`/addnote Your note content here`\n\n"
                "Delete a note:\n"
                "`/delnote note_id`",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("➕ Create First Note", callback_data="add_note")
                ]])
            )
            return
        
        text = "📝 **Your Notes**\n\n"
        for i, note in enumerate(notes, 1):
            content = note.get('content', 'No content')
            if len(content) > 80:
                content = content[:77] + "..."
            text += f"`{i}.` {content}\n"
            text += f"   📅 {note.get('created_at', datetime.utcnow()).strftime('%b %d, %H:%M')}\n"
            text += f"   🆔 `{note.get('note_id', '')[:8]}`\n\n"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("➕ Add Note", callback_data="add_note"),
                InlineKeyboardButton("🗑️ Delete Note", callback_data="delete_note")
            ],
            [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]
        ])
        
        await message.reply(text, reply_markup=keyboard)
        await db.increment_command_usage(user_id)
    
    @bot.app.on_message(filters.command("addnote"))
    async def add_note_handler(client: Client, message: Message):
        user_id = message.from_user.id
        
        if await db.is_user_blocked(user_id):
            await message.reply("⛔ Access denied.")
            return
        
        try:
            # Get note content from message
            content = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
            
            if not content:
                await message.reply(
                    "❌ Please provide note content.\n"
                    "Usage: `/addnote Your note text here`"
                )
                return
            
            note_data = {
                "user_id": user_id,
                "note_id": str(uuid.uuid4()),
                "content": content,
                "created_at": datetime.utcnow()
            }
            
            note_id = await db.create_note(user_id, note_data)
            
            if note_id:
                await message.reply(
                    f"✅ **Note saved!**\n\n"
                    f"🆔 ID: `{note_data['note_id'][:8]}`\n"
                    f"📝 Content: {content[:200]}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 View Notes", callback_data="notes_menu")
                    ]])
                )
            else:
                await message.reply("❌ Failed to save note.")
                
        except Exception as e:
            logger.error(f"Add note error: {e}")
            await message.reply("❌ Error saving note.")
    
    @bot.app.on_message(filters.command("delnote"))
    async def delete_note_handler(client: Client, message: Message):
        user_id = message.from_user.id
        
        if await db.is_user_blocked(user_id):
            await message.reply("⛔ Access denied.")
            return
        
        try:
            note_id = message.command[1] if len(message.command) > 1 else None
            
            if not note_id:
                await message.reply(
                    "❌ Please provide note ID.\n"
                    "Usage: `/delnote note_id`\n\n"
                    "Find IDs with /notes command"
                )
                return
            
            # Find full note_id
            notes = await db.get_notes(user_id, limit=100)
            full_id = None
            for note in notes:
                if note.get('note_id', '').startswith(note_id):
                    full_id = note['note_id']
                    break
            
            if not full_id:
                await message.reply("❌ Note not found. Check the ID with /notes")
                return
            
            success = await db.delete_note(user_id, full_id)
            
            if success:
                await message.reply(
                    "✅ **Note deleted successfully!**",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 View Notes", callback_data="notes_menu")
                    ]])
                )
            else:
                await message.reply("❌ Failed to delete note.")
                
        except Exception as e:
            logger.error(f"Delete note error: {e}")
            await message.reply("❌ Error deleting note.")
