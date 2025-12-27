import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Telegram Bot Token (REQUIRED)
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Admin IDs (comma separated)
    ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    
    # Sudo Users (full access, comma separated)
    SUDO_IDS = [int(id.strip()) for id in os.getenv("SUDO_IDS", "").split(",") if id.strip()]
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Redis for caching
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Report Channel ID (optional)
    REPORT_CHANNEL = os.getenv("REPORT_CHANNEL_ID", "")
    
    # Moderation Thresholds (0.0 to 1.0)
    NSFW_THRESHOLD = float(os.getenv("NSFW_THRESHOLD", "0.85"))
    VIOLENCE_THRESHOLD = float(os.getenv("VIOLENCE_THRESHOLD", "0.80"))
    SPAM_THRESHOLD = int(os.getenv("SPAM_THRESHOLD", "5"))
    
    # Cooldown settings (seconds)
    USER_WARN_COOLDOWN = int(os.getenv("USER_WARN_COOLDOWN", "300"))
    AUTO_DELETE_DELAY = int(os.getenv("AUTO_DELETE_DELAY", "60"))
    
    # GBAN Settings
    ENABLE_GBAN = os.getenv("ENABLE_GBAN", "true").lower() == "true"
    GBAN_SYNC_INTERVAL = int(os.getenv("GBAN_SYNC_INTERVAL", "300"))  # 5 minutes
    
    # Paths
    BASE_DIR = Path(__file__).parent.absolute()
    TEMP_DIR = BASE_DIR / "temp_files"
    MODELS_DIR = BASE_DIR / "models"
    LOGS_DIR = BASE_DIR / "logs"
    BACKUP_DIR = BASE_DIR / "backup"
    
    # Enable/Disable features
    ENABLE_NSFW_DETECTION = os.getenv("ENABLE_NSFW_DETECTION", "true").lower() == "true"
    ENABLE_VIOLENCE_DETECTION = os.getenv("ENABLE_VIOLENCE_DETECTION", "true").lower() == "true"
    ENABLE_SPAM_DETECTION = os.getenv("ENABLE_SPAM_DETECTION", "true").lower() == "true"
    
    # Maximum warnings before ban
    MAX_WARNINGS = int(os.getenv("MAX_WARNINGS", "3"))
    
    # Bot settings
    DROP_PENDING_UPDATES = os.getenv("DROP_PENDING_UPDATES", "true").lower() == "true"
    
    # Security
    ALLOW_SUDO_COMMANDS = os.getenv("ALLOW_SUDO_COMMANDS", "true").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.TOKEN or cls.TOKEN == "YOUR_BOT_TOKEN_HERE":
            raise ValueError("❌ BOT_TOKEN is required in .env file. Get it from @BotFather")
        
        if not cls.ADMIN_IDS:
            print("⚠️ Warning: No ADMIN_IDS configured")
        
        if not cls.SUDO_IDS:
            print("⚠️ Warning: No SUDO_IDS configured")
        else:
            print(f"✅ Sudo users: {len(cls.SUDO_IDS)}")
        
        # Create necessary directories
        cls.TEMP_DIR.mkdir(exist_ok=True)
        cls.MODELS_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)
        cls.BACKUP_DIR.mkdir(exist_ok=True)
        
        print("✅ Configuration validated successfully")
        
    @classmethod
    def print_config(cls):
        """Print configuration summary"""
        print("\n" + "="*50)
        print("🤖 BOT CONFIGURATION")
        print("="*50)
        print(f"Token: {'✓' if cls.TOKEN and cls.TOKEN != 'YOUR_BOT_TOKEN_HERE' else '✗'}")
        print(f"Admin IDs: {len(cls.ADMIN_IDS)}")
        print(f"Sudo IDs: {len(cls.SUDO_IDS)}")
        print(f"Database: {cls.DATABASE_URL}")
        print(f"GBAN Enabled: {cls.ENABLE_GBAN}")
        print(f"NSFW Detection: {cls.ENABLE_NSFW_DETECTION}")
        print(f"Violence Detection: {cls.ENABLE_VIOLENCE_DETECTION}")
        print(f"Spam Detection: {cls.ENABLE_SPAM_DETECTION}")
        print("="*50 + "\n")

# Create global instance
config = Config()
