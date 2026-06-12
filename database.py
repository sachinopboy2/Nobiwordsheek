from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(Config.MONGO_URI)
            self.db = self.client[Config.DATABASE_NAME]
            
            # Create indexes
            await self.db.users.create_index("user_id", unique=True)
            await self.db.settings.create_index("user_id", unique=True)
            await self.db.statistics.create_index("user_id", unique=True)
            await self.db.plugins.create_index("user_id", unique=True)
            await self.db.notes.create_index([("user_id", 1), ("note_id", 1)])
            await self.db.reminders.create_index([("user_id", 1), ("reminder_id", 1)])
            await self.db.logs.create_index([("user_id", 1), ("timestamp", -1)])
            await self.db.backups.create_index([("user_id", 1), ("backup_id", 1)])
            
            logger.info("Database connected and indexes created")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database disconnected")
    
    # User Management
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create new user"""
        try:
            user_data["created_at"] = datetime.utcnow()
            user_data["is_blocked"] = False
            await self.db.users.insert_one(user_data)
            
            # Initialize user settings
            await self.db.settings.insert_one({
                "user_id": user_data["user_id"],
                "language": "en",
                "timezone": "UTC",
                "notifications": True,
                "theme": "default"
            })
            
            # Initialize statistics
            await self.db.statistics.insert_one({
                "user_id": user_data["user_id"],
                "total_notes": 0,
                "total_reminders": 0,
                "total_backups": 0,
                "commands_used": 0,
                "last_active": datetime.utcnow()
            })
            
            # Initialize plugins
            await self.db.plugins.insert_one({
                "user_id": user_data["user_id"],
                "enabled_plugins": Config.ENABLED_PLUGINS.copy()
            })
            
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return await self.db.users.find_one({"user_id": user_id})
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> bool:
        """Update user data"""
        try:
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    async def block_user(self, user_id: int) -> bool:
        """Block user"""
        return await self.update_user(user_id, {"is_blocked": True})
    
    async def unblock_user(self, user_id: int) -> bool:
        """Unblock user"""
        return await self.update_user(user_id, {"is_blocked": False})
    
    async def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        user = await self.get_user(user_id)
        return user.get("is_blocked", False) if user else False
    
    # Settings
    async def get_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings"""
        return await self.db.settings.find_one({"user_id": user_id})
    
    async def update_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            await self.db.settings.update_one(
                {"user_id": user_id},
                {"$set": settings},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False
    
    # Statistics
    async def get_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        return await self.db.statistics.find_one({"user_id": user_id})
    
    async def update_statistics(self, user_id: int, stats: Dict[str, Any]) -> bool:
        """Update user statistics"""
        try:
            await self.db.statistics.update_one(
                {"user_id": user_id},
                {"$set": stats},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return False
    
    async def increment_command_usage(self, user_id: int) -> bool:
        """Increment command usage counter"""
        try:
            await self.db.statistics.update_one(
                {"user_id": user_id},
                {"$inc": {"commands_used": 1}, "$set": {"last_active": datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error incrementing command usage: {e}")
            return False
    
    # Notes
    async def create_note(self, user_id: int, note_data: Dict[str, Any]) -> str:
        """Create new note"""
        try:
            note_data["created_at"] = datetime.utcnow()
            result = await self.db.notes.insert_one(note_data)
            await self.db.statistics.update_one(
                {"user_id": user_id},
                {"$inc": {"total_notes": 1}}
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            return None
    
    async def get_notes(self, user_id: int, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
        """Get user notes with pagination"""
        cursor = self.db.notes.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def delete_note(self, user_id: int, note_id: str) -> bool:
        """Delete note"""
        try:
            result = await self.db.notes.delete_one({"user_id": user_id, "note_id": note_id})
            if result.deleted_count > 0:
                await self.db.statistics.update_one(
                    {"user_id": user_id},
                    {"$inc": {"total_notes": -1}}
                )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting note: {e}")
            return False
    
    # Reminders
    async def create_reminder(self, user_id: int, reminder_data: Dict[str, Any]) -> str:
        """Create new reminder"""
        try:
            reminder_data["created_at"] = datetime.utcnow()
            result = await self.db.reminders.insert_one(reminder_data)
            await self.db.statistics.update_one(
                {"user_id": user_id},
                {"$inc": {"total_reminders": 1}}
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return None
    
    async def get_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user reminders"""
        cursor = self.db.reminders.find({"user_id": user_id, "is_active": True})
        return await cursor.to_list(length=100)
    
    async def delete_reminder(self, user_id: int, reminder_id: str) -> bool:
        """Delete reminder"""
        try:
            result = await self.db.reminders.delete_one(
                {"user_id": user_id, "reminder_id": reminder_id}
            )
            if result.deleted_count > 0:
                await self.db.statistics.update_one(
                    {"user_id": user_id},
                    {"$inc": {"total_reminders": -1}}
                )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            return False
    
    # Backups
    async def create_backup(self, user_id: int, backup_data: Dict[str, Any]) -> str:
        """Create user backup"""
        try:
            backup_data["created_at"] = datetime.utcnow()
            result = await self.db.backups.insert_one(backup_data)
            await self.db.statistics.update_one(
                {"user_id": user_id},
                {"$inc": {"total_backups": 1}}
            )
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    async def get_backups(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user backups"""
        cursor = self.db.backups.find({"user_id": user_id}).sort("created_at", -1)
        return await cursor.to_list(length=50)
    
    async def get_backup(self, user_id: int, backup_id: str) -> Dict[str, Any]:
        """Get specific backup"""
        return await self.db.backups.find_one({"user_id": user_id, "backup_id": backup_id})
    
    # Logs
    async def add_log(self, user_id: int, log_data: Dict[str, Any]) -> bool:
        """Add activity log"""
        try:
            log_data["timestamp"] = datetime.utcnow()
            await self.db.logs.insert_one(log_data)
            return True
        except Exception as e:
            logger.error(f"Error adding log: {e}")
            return False
    
    async def get_logs(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user activity logs"""
        cursor = self.db.logs.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    # Plugins
    async def get_plugins(self, user_id: int) -> Dict[str, Any]:
        """Get user plugins status"""
        return await self.db.plugins.find_one({"user_id": user_id})
    
    async def toggle_plugin(self, user_id: int, plugin_name: str, enable: bool) -> bool:
        """Enable or disable plugin"""
        try:
            if enable:
                await self.db.plugins.update_one(
                    {"user_id": user_id},
                    {"$addToSet": {"enabled_plugins": plugin_name}}
                )
            else:
                await self.db.plugins.update_one(
                    {"user_id": user_id},
                    {"$pull": {"enabled_plugins": plugin_name}}
                )
            return True
        except Exception as e:
            logger.error(f"Error toggling plugin: {e}")
            return False
    
    # Music History
    async def add_music_history(self, user_id: int, music_data: Dict[str, Any]) -> bool:
        """Add to music search history"""
        try:
            music_data["searched_at"] = datetime.utcnow()
            await self.db.music_history.insert_one(music_data)
            return True
        except Exception as e:
            logger.error(f"Error adding music history: {e}")
            return False
    
    async def get_music_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get music search history"""
        cursor = self.db.music_history.find({"user_id": user_id}).sort("searched_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

# Global database instance
db = Database()
