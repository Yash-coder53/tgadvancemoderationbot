#!/usr/bin/env python3
"""
Main entry point for Telegram Moderation Bot
"""

import logging
import sys
import os
import signal
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError

# Import modules
from config import config
from handlers import (
    # Basic commands
    start_command, help_command, report_command, appeal_command,
    
    # Admin commands
    warn_command, ban_command, mute_command, kick_command,
    whitelist_command, unwhitelist_command, settings_command, stats_command,
    
    # Sudo commands
    gban_command, ungban_command, gbanlist_command, gbanstats_command,
    addsudo_command, delsudo_command, sudolist_command, sudostats_command,
    shell_command, eval_command, broadcast_command, restart_command, update_command,
    
    # Message handlers
    handle_photo, handle_document, handle_text, handle_new_chat_members,
    
    # Callback handlers
    button_callback,
    
    # Other handlers
    handle_message
)
from utils import schedule_cleanup
from moderator import moderator
import asyncio

# Configure logging
def setup_logging():
    """Configure logging system"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if not exists
    config.LOGS_DIR.mkdir(exist_ok=True)
    
    # Generate log filename with date
    log_file = config.LOGS_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific log levels
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Get logger
logger = setup_logging()

# Global variables for cleanup
cleanup_task = None
application = None

async def error_handler(update: object, context):
    """Handle errors in telegram bot"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)
    
    # Try to notify admin
    try:
        if config.ADMIN_IDS:
            error_msg = f"⚠️ *Bot Error*\n\n`{str(context.error)[:200]}`"
            
            for admin_id in config.ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=error_msg,
                        parse_mode='Markdown'
                    )
                except:
                    continue
    except Exception as e:
        logger.error(f"Failed to notify admin about error: {e}")

async def post_init(application: Application):
    """Post initialization tasks"""
    logger.info("🤖 Bot initialization complete")
    logger.info("✅ ML models loaded" if moderator.models_loaded else "⚠️ Using rule-based detection")
    logger.info(f"✅ Admin IDs: {len(config.ADMIN_IDS)}")
    logger.info(f"✅ Sudo IDs: {len(config.SUDO_IDS)}")
    logger.info(f"✅ GBAN Enabled: {config.ENABLE_GBAN}")
    logger.info(f"✅ Database initialized")
    
    # Print welcome message
    print("\n" + "="*50)
    print("🤖 TELEGRAM MODERATION BOT")
    print("="*50)
    print(f"Status: ✅ ONLINE")
    print(f"Bot: @{application.bot.username}")
    print(f"Admins: {len(config.ADMIN_IDS)}")
    print(f"Sudo Users: {len(config.SUDO_IDS)}")
    print(f"GBAN System: {'✅ Enabled' if config.ENABLE_GBAN else '❌ Disabled'}")
    print(f"NSFW Detection: {'✅' if config.ENABLE_NSFW_DETECTION else '❌'}")
    print(f"Violence Detection: {'✅' if config.ENABLE_VIOLENCE_DETECTION else '❌'}")
    print(f"Spam Detection: {'✅' if config.ENABLE_SPAM_DETECTION else '❌'}")
    print("="*50)
    print("📝 Commands available:")
    print("  /start - Start the bot")
    print("  /help - Show help")
    print("  /settings - Configure bot (admin only)")
    print("  /stats - View statistics (admin only)")
    print("  /gban - Global ban user (sudo only)")
    print("  /ungban - Remove global ban (sudo only)")
    print("  /addsudo - Add sudo user (sudo only)")
    print("  /report <reason> - Report a message")
    print("  /appeal - Appeal a warning")
    print("="*50 + "\n")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    if application:
        application.stop()
    sys.exit(0)

def main():
    """Main function to start the bot"""
    global cleanup_task, application
    
    try:
        # Validate configuration
        logger.info("🔧 Validating configuration...")
        config.validate()
        config.print_config()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create application
        logger.info("🚀 Creating bot application...")
        application = Application.builder().token(config.TOKEN).build()
        
        # Add command handlers
        logger.info("📝 Setting up command handlers...")
        
        # Basic commands
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("report", report_command))
        application.add_handler(CommandHandler("appeal", appeal_command))
        
        # Admin commands
        application.add_handler(CommandHandler("warn", warn_command))
        application.add_handler(CommandHandler("ban", ban_command))
        application.add_handler(CommandHandler("mute", mute_command))
        application.add_handler(CommandHandler("kick", kick_command))
        application.add_handler(CommandHandler("whitelist", whitelist_command))
        application.add_handler(CommandHandler("unwhitelist", unwhitelist_command))
        application.add_handler(CommandHandler("settings", settings_command))
        application.add_handler(CommandHandler("stats", stats_command))
        
        # Sudo commands
        application.add_handler(CommandHandler("gban", gban_command))
        application.add_handler(CommandHandler("ungban", ungban_command))
        application.add_handler(CommandHandler("gbanlist", gbanlist_command))
        application.add_handler(CommandHandler("gbanstats", gbanstats_command))
        application.add_handler(CommandHandler("addsudo", addsudo_command))
        application.add_handler(CommandHandler("delsudo", delsudo_command))
        application.add_handler(CommandHandler("sudolist", sudolist_command))
        application.add_handler(CommandHandler("sudostats", sudostats_command))
        
        if config.ALLOW_SUDO_COMMANDS:
            application.add_handler(CommandHandler("shell", shell_command))
            application.add_handler(CommandHandler("eval", eval_command))
            application.add_handler(CommandHandler("broadcast", broadcast_command))
            application.add_handler(CommandHandler("restart", restart_command))
            application.add_handler(CommandHandler("update", update_command))
        
        # Message handlers
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # GBAN handler for new chat members
        if config.ENABLE_GBAN:
            application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Handle regular messages for settings
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Add post initialization
        application.post_init = post_init
        
        # Start bot
        logger.info("🤖 Starting bot...")
        
        # Get event loop
        loop = asyncio.get_event_loop()
        
        # Start cleanup task
        cleanup_task = loop.create_task(schedule_cleanup())
        
        # Run the bot
        application.run_polling(
            drop_pending_updates=config.DROP_PENDING_UPDATES,
            allowed_updates=[
                "message",
                "callback_query",
                "chat_member",
                "my_chat_member",
                "chat_join_request"
            ]
        )
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        print(f"\n❌ ERROR: {e}")
        print("Please check your .env file and ensure BOT_TOKEN is set correctly.")
        sys.exit(1)
        
    except TelegramError as e:
        logger.error(f"❌ Telegram error: {e}")
        print(f"\n❌ TELEGRAM ERROR: {e}")
        print("Please check your bot token and internet connection.")
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
        print("\n👋 Bot stopped gracefully")
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)
        
    finally:
        # Cancel cleanup task
        if cleanup_task and not cleanup_task.done():
            cleanup_task.cancel()
        
        logger.info("📴 Bot shutdown complete")
        print("\n📴 Bot shutdown complete")

if __name__ == '__main__':
    main()
