python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    OWNER_ID = int(os.getenv("OWNER_ID"))
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
    
    # Rate Limiting
    RATE_LIMIT = 30  # messages per minute
    RATE_LIMIT_BURST = 5  # burst messages
    
    # Sessions
    SESSION_TIMEOUT = 3600  # 1 hour
    
    # Plugins
    ENABLED_PLUGINS = [
        "start", "help", "dashboard", "profile", "settings",
        "plugins", "stats", "translator", "notes", "reminders",
        "polls", "sticker", "media_tools", "downloader", "upload",
        "logs", "notifications", "backup", "restore", "language",
        "support", "feedback", "music"
    ]
