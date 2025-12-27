from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import os
import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from config import config
from database import db
from moderator import moderator
from actions import ActionManager
from gban import gban_system
from sudo import sudo_system
from utils import (
    download_file, is_admin, is_sudo, format_bytes, 
    backup_database, get_bot_info, execute_shell, eval_python
)

logger = logging.getLogger(__name__)

# Store user message history for spam detection
user_message_history: Dict[int, List[Dict]] = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Add user to database
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Check user permissions
    admin_status = await is_admin(update, context)
    sudo_status = await is_sudo(update, context)
    
    welcome_text = (
        f"🤖 *Advanced Moderation Bot*\n\n"
        f"Hello {user.first_name}! I'm here to help moderate this group.\n\n"
        f"*Features:*\n"
        f"• 🚫 NSFW content detection\n"
        f"• ⚔️ Violence detection\n"
        f"• 📢 Spam protection\n"
        f"• ©️ Copyright monitoring\n"
        f"• 🌍 Global Ban (GBAN) System\n"
        f"• 👑 Sudo Users System\n"
        f"• ⚡ Auto-moderation\n\n"
    )
    
    if sudo_status:
        welcome_text += (
            "*👑 Sudo Commands:*\n"
            f"/gban <user_id> <reason> - Globally ban user\n"
            f"/ungban <user_id> - Remove global ban\n"
            f"/gbanlist - List GBANNED users\n"
            f"/gbanstats - GBAN statistics\n"
            f"/addsudo <user_id> - Add sudo user\n"
            f"/delsudo <user_id> - Remove sudo user\n"
            f"/sudolist - List sudo users\n"
            f"/sudostats - Sudo statistics\n"
            f"/shell <command> - Execute shell command\n"
            f"/eval <code> - Evaluate Python code\n"
            f"/broadcast <message> - Broadcast to all chats\n"
            f"/restart - Restart bot\n"
            f"/update - Update bot\n\n"
        )
    
    if admin_status:
        welcome_text += (
            "*⚡ Admin Commands:*\n"
            f"/warn <user_id> <reason> - Warn a user\n"
            f"/ban <user_id> <reason> - Ban a user\n"
            f"/mute <user_id> <duration> <reason> - Mute a user\n"
            f"/kick <user_id> <reason> - Kick a user\n"
            f"/whitelist <user_id> - Add to whitelist\n"
            f"/unwhitelist <user_id> - Remove from whitelist\n"
            f"/settings - Configure bot\n"
            f"/stats - View statistics\n"
            f"/logs - View recent logs\n"
            f"/backup - Backup database\n"
            f"/cleanup - Clean temporary files\n\n"
        )
    
    welcome_text += (
        "*👤 User Commands:*\n"
        f"/report <reason> - Report a message (reply to message)\n"
        f"/appeal - Appeal a moderation action\n"
        f"/help - Show help message\n\n"
        f"*Your Status:*\n"
        f"• Sudo: {'✅ Yes' if sudo_status else '❌ No'}\n"
        f"• Admin: {'✅ Yes' if admin_status else '❌ No'}\n"
        f"• GBAN Enabled: {'✅ Yes' if config.ENABLE_GBAN else '❌ No'}"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# ===== SUDO COMMANDS =====

async def gban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /gban command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/gban <user_id> <reason>`\n\n"
            "Example: `/gban 123456 Spamming multiple groups`\n"
            "Example: `/gban 123456 Posting illegal content everywhere`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        
        result = await gban_system.gban_user(update, context, user_id, reason)
        
        if result['success']:
            response = (
                f"✅ *User Globally Banned*\n\n"
                f"*User:* {result.get('user_info', f'ID: {user_id}')}\n"
                f"*User ID:* `{user_id}`\n"
                f"*Reason:* {reason}\n"
                f"*Banned by:* {update.effective_user.mention_html()}\n"
                f"*Time:* {result['timestamp'][:19]}\n"
                f"*Chats banned:* {len(result.get('banned_chats', []))}"
            )
        else:
            response = f"❌ *GBAN Failed*\n\nError: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in gban command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def ungban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ungban command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/ungban <user_id>`\n\n"
            "Example: `/ungban 123456`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        result = await gban_system.ungban_user(update, context, user_id)
        
        if result['success']:
            response = (
                f"✅ *User Globally Unbanned*\n\n"
                f"*User:* {result.get('user_info', f'ID: {user_id}')}\n"
                f"*User ID:* `{user_id}`\n"
                f"*Removed by:* {update.effective_user.mention_html()}\n"
                f"*Time:* {result['timestamp'][:19]}\n"
                f"*Chats unbanned:* {len(result.get('unbanned_chats', []))}"
            )
        else:
            response = f"❌ *UNGBAN Failed*\n\nError: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in ungban command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def gbanlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /gbanlist command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
        
        result = await gban_system.gban_list(update, context, page)
        
        if not result['success']:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
            return
        
        if not result['gban_list']:
            await update.message.reply_text("📭 GBAN list is empty")
            return
        
        response = f"🌍 *Global Ban List - Page {page}/{result['total_pages']}*\n\n"
        response += f"*Total GBANNED users:* {result['total_gbans']}\n\n"
        
        for i, gban in enumerate(result['gban_list'], 1):
            username = gban.get('username', '') or gban.get('first_name', '')
            if gban.get('last_name'):
                username = f"{username} {gban['last_name']}"
            
            response += (
                f"{i}. *User:* {username or 'Unknown'}\n"
                f"   *ID:* `{gban['user_id']}`\n"
                f"   *Reason:* {gban['reason']}\n"
                f"   *Banned by:* `{gban['banned_by']}`\n"
                f"   *Date:* {gban['banned_at'][:19]}\n\n"
            )
        
        # Add pagination buttons
        keyboard = []
        if page > 1:
            keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"gban_page_{page-1}"))
        if page < result['total_pages']:
            keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"gban_page_{page+1}"))
        
        reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in gbanlist command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def gbanstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /gbanstats command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        result = await gban_system.gban_stats(update, context)
        
        if not result['success']:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
            return
        
        stats = result['stats']
        
        response = (
            f"📊 *Global Ban Statistics*\n\n"
            f"*Total GBANNED users:* {stats.get('total_gbans', 0)}\n"
            f"*GBANS today:* {stats.get('gbans_today', 0)}\n"
            f"*GBANS this week:* {stats.get('gbans_week', 0)}\n\n"
            f"*Last updated:* {result['timestamp'][:19]}"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in gbanstats command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def addsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addsudo command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/addsudo <user_id>`\n\n"
            "Example: `/addsudo 123456`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        result = await sudo_system.add_sudo(update, context, user_id)
        
        if result['success']:
            response = (
                f"✅ *User Added as Sudo*\n\n"
                f"*User:* {result.get('user_info', f'ID: {user_id}')}\n"
                f"*User ID:* `{user_id}`\n"
                f"*Added by:* {update.effective_user.mention_html()}\n"
                f"*Time:* {result['timestamp'][:19]}\n\n"
                f"User now has full access to all bot commands."
            )
        else:
            response = f"❌ *Failed to Add Sudo*\n\nError: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in addsudo command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def delsudo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /delsudo command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/delsudo <user_id>`\n\n"
            "Example: `/delsudo 123456`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        result = await sudo_system.remove_sudo(update, context, user_id)
        
        if result['success']:
            response = (
                f"✅ *User Removed from Sudo*\n\n"
                f"*User:* {result.get('user_info', f'ID: {user_id}')}\n"
                f"*User ID:* `{user_id}`\n"
                f"*Removed by:* {update.effective_user.mention_html()}\n"
                f"*Time:* {result['timestamp'][:19]}"
            )
        else:
            response = f"❌ *Failed to Remove Sudo*\n\nError: {result.get('error', 'Unknown error')}"
        
        await update.message.reply_text(response, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in delsudo command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sudolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sudolist command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        result = await sudo_system.sudo_list(update, context)
        
        if not result['success']:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
            return
        
        response = f"👑 *Sudo Users List*\n\n"
        response += f"*Total Sudo users:* {result['total_sudo']}\n\n"
        
        for i, sudo_user in enumerate(result['sudo_users'], 1):
            source = "⚙️ Config" if sudo_user['source'] == 'config' else "💾 Database"
            
            response += (
                f"{i}. *User:* {sudo_user.get('username', f'ID: {sudo_user["user_id"]}')}\n"
                f"   *ID:* `{sudo_user['user_id']}`\n"
                f"   *Source:* {source}\n"
            )
            
            if sudo_user['source'] == 'database':
                response += f"   *Added by:* `{sudo_user.get('added_by', 'Unknown')}`\n"
                if sudo_user.get('added_at'):
                    response += f"   *Added:* {sudo_user['added_at'][:19]}\n"
            
            response += "\n"
        
        await update.message.reply_text(
            response,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in sudolist command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def sudostats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sudostats command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        result = await sudo_system.sudo_stats(update, context)
        
        if not result['success']:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
            return
        
        stats = result['stats']
        
        response = (
            f"📊 *Sudo Statistics*\n\n"
            f"*Total Sudo users:* {stats.get('total_sudo', 0)}\n"
            f"*From config:* {stats.get('config_sudo', 0)}\n"
            f"*From database:* {stats.get('db_sudo', 0)}\n\n"
            f"*Last updated:* {stats.get('timestamp', '')[:19]}"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sudostats command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def shell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /shell command (sudo only - DANGEROUS)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if not config.ALLOW_SUDO_COMMANDS:
        await update.message.reply_text("❌ Sudo commands are disabled in config")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/shell <command>`\n\n"
            "Example: `/shell ls -la`\n"
            "Example: `/shell pwd`\n\n"
            "⚠️ *Warning:* This is a dangerous command!",
            parse_mode='Markdown'
        )
        return
    
    try:
        command = ' '.join(context.args)
        
        # Show "processing" message
        processing_msg = await update.message.reply_text("⚡ Executing command...")
        
        # Execute command
        result = await execute_shell(command)
        
        # Format response
        if result['success']:
            response = f"✅ *Command Executed Successfully*\n\n"
        else:
            response = f"❌ *Command Failed*\n\n"
        
        response += f"*Command:* `{command}`\n"
        response += f"*Return code:* `{result['return_code']}`\n\n"
        
        if result['output']:
            output = result['output'][:1000]  # Limit output
            response += f"*Output:*\n```\n{output}\n```\n\n"
        
        if result['error']:
            error = result['error'][:500]  # Limit error
            response += f"*Error:*\n```\n{error}\n```"
        
        # Send response
        await processing_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in shell command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def eval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /eval command (sudo only - VERY DANGEROUS)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if not config.ALLOW_SUDO_COMMANDS:
        await update.message.reply_text("❌ Sudo commands are disabled in config")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/eval <python_code>`\n\n"
            "Example: `/eval 2 + 2`\n"
            "Example: `/eval len(\"hello\")`\n\n"
            "⚠️ *Warning:* This is a VERY dangerous command!",
            parse_mode='Markdown'
        )
        return
    
    try:
        code = ' '.join(context.args)
        
        # Show "processing" message
        processing_msg = await update.message.reply_text("⚡ Evaluating code...")
        
        # Evaluate code
        result = await eval_python(code)
        
        # Format response
        if result['success']:
            response = f"✅ *Code Evaluated Successfully*\n\n"
        else:
            response = f"❌ *Evaluation Failed*\n\n"
        
        response += f"*Code:* `{code}`\n\n"
        
        if result['result']:
            result_text = str(result['result'])[:1000]  # Limit result
            response += f"*Result:*\n```\n{result_text}\n```\n\n"
        
        if result['error']:
            error = result['error'][:500]  # Limit error
            response += f"*Error:*\n```\n{error}\n```"
        
        # Send response
        await processing_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in eval command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/broadcast <message>`\n\n"
            "Example: `/broadcast Hello everyone!`\n"
            "Example: `/broadcast System maintenance in 10 minutes`",
            parse_mode='Markdown'
        )
        return
    
    try:
        message = ' '.join(context.args)
        
        # TODO: Implement actual broadcast to all chats
        # For now, just acknowledge
        response = (
            f"📢 *Broadcast Message*\n\n"
            f"{message}\n\n"
            f"*Sent by:* {update.effective_user.mention_html()}\n"
            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await update.message.reply_text(response, parse_mode='HTML')
        logger.info(f"Broadcast sent by {update.effective_user.id}: {message}")
        
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /restart command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        await update.message.reply_text("🔄 Restarting bot...")
        logger.info(f"Bot restart requested by {update.effective_user.id}")
        
        # In production, you would restart the bot here
        # For now, just acknowledge
        await update.message.reply_text(
            "✅ Restart command received.\n\n"
            "In production, the bot would restart now.\n"
            "To implement restart, use a process manager like systemd or supervisor."
        )
        
    except Exception as e:
        logger.error(f"Error in restart command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /update command (sudo only)"""
    if not await is_sudo(update, context):
        await update.message.reply_text("👑 Sudo only command")
        return
    
    try:
        await update.message.reply_text("🔄 Updating bot...")
        logger.info(f"Bot update requested by {update.effective_user.id}")
        
        # Execute git pull
        result = await execute_shell("git pull")
        
        if result['success']:
            response = (
                f"✅ *Update Successful*\n\n"
                f"*Output:*\n```\n{result['output'][:500]}\n```\n\n"
                f"Please restart the bot with /restart to apply changes."
            )
        else:
            response = (
                f"❌ *Update Failed*\n\n"
                f"*Error:*\n```\n{result['error'][:500]}\n```"
            )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in update command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ===== EXISTING COMMANDS (UPDATED FOR GBAN/SUDO) =====

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /warn command"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/warn <user_id> <reason>`\n\n"
            "Example: `/warn 123456 Spamming the chat`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        
        # Check if user is GBANNED
        is_gbanned, gban_reason = db.is_user_gbanned(user_id)
        if is_gbanned:
            await update.message.reply_text(
                f"⚠️ *User is Globally Banned*\n\n"
                f"User ID: `{user_id}`\n"
                f"GBAN Reason: {gban_reason}\n\n"
                f"GBANNED users are automatically banned from all chats.",
                parse_mode='Markdown'
            )
            return
        
        result = await ActionManager.warn_user(
            update=update,
            context=context,
            user_id=user_id,
            reason=reason,
            warning_type="manual"
        )
        
        if result['success']:
            if result.get('action') == 'banned':
                await update.message.reply_text(
                    f"✅ User {user_id} has been warned and banned for exceeding warnings."
                )
            else:
                await update.message.reply_text(
                    f"✅ User {user_id} warned successfully.\n"
                    f"Total warnings: {result['warnings']}"
                )
        else:
            reason_msg = result.get('reason', 'Unknown error')
            await update.message.reply_text(f"❌ Failed to warn user: {reason_msg}")
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in warn command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban command"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/ban <user_id> <reason>`\n\n"
            "Example: `/ban 123456 Violating rules`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        chat_id = update.effective_chat.id
        
        # Check if user is GBANNED
        is_gbanned, gban_reason = db.is_user_gbanned(user_id)
        if is_gbanned:
            await update.message.reply_text(
                f"⚠️ *User is Already Globally Banned*\n\n"
                f"User ID: `{user_id}`\n"
                f"GBAN Reason: {gban_reason}\n\n"
                f"No action needed - user is already banned everywhere.",
                parse_mode='Markdown'
            )
            return
        
        # Ask for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, ban user", callback_data=f"confirm_ban_{user_id}_{reason}"),
                InlineKeyboardButton("🌍 GBAN instead", callback_data=f"suggest_gban_{user_id}_{reason}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_ban")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ *Confirm Ban*\n\n"
            f"User ID: `{user_id}`\n"
            f"Reason: {reason}\n\n"
            f"Are you sure you want to ban this user?\n"
            f"Or use GBAN to ban from all chats?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
            
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user = update.effective_user
    sudo_status = await is_sudo(update, context)
    admin_status = await is_admin(update, context)
    
    help_text = (
        "📖 *Help Guide*\n\n"
        
        "*For Sudo Users:*\n"
        "You have full control over the bot.\n"
        "Use /start to see all available commands.\n\n"
        
        "*For Admins:*\n"
        "1. Add me as admin with delete messages permission\n"
        "2. Use /settings to configure filters\n"
        "3. Use /warn or /ban to moderate users\n"
        "4. Use /whitelist to exempt trusted users\n\n"
        
        "*For Users:*\n"
        "• Follow group rules\n"
        "• Use /report to report violations (reply to message)\n"
        "• Use /appeal if you believe a moderation action was wrong\n"
        "• Contact admins for help\n\n"
        
        "*Auto-moderation Features:*\n"
        f"• NSFW Detection: {'✅ Enabled' if config.ENABLE_NSFW_DETECTION else '❌ Disabled'}\n"
        f"• Violence Detection: {'✅ Enabled' if config.ENABLE_VIOLENCE_DETECTION else '❌ Disabled'}\n"
        f"• Spam Protection: {'✅ Enabled' if config.ENABLE_SPAM_DETECTION else '❌ Disabled'}\n"
        f"• GBAN System: {'✅ Enabled' if config.ENABLE_GBAN else '❌ Disabled'}\n\n"
        
        "*Your Permissions:*\n"
        f"• Sudo: {'✅ Yes' if sudo_status else '❌ No'}\n"
        f"• Admin: {'✅ Yes' if admin_status else '❌ No'}\n\n"
        
        "*Need Help?*\n"
        "Contact bot admin for assistance."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ===== UPDATED SETTINGS COMMAND =====

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    chat_id = update.effective_chat.id
    current_settings = db.get_chat_settings(chat_id)
    
    # Create settings keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                f"NSFW Filter: {'✅' if current_settings['enable_nsfw_filter'] else '❌'}",
                callback_data="toggle_nsfw"
            ),
            InlineKeyboardButton(
                f"Violence Filter: {'✅' if current_settings['enable_violence_filter'] else '❌'}",
                callback_data="toggle_violence"
            )
        ],
        [
            InlineKeyboardButton(
                f"Spam Filter: {'✅' if current_settings['enable_spam_filter'] else '❌'}",
                callback_data="toggle_spam"
            ),
            InlineKeyboardButton(
                f"GBAN Sync: {'✅' if current_settings['enable_gban_sync'] else '❌'}",
                callback_data="toggle_gban_sync"
            )
        ],
        [
            InlineKeyboardButton(
                f"Auto Delete: {'✅' if current_settings['auto_delete_messages'] else '❌'}",
                callback_data="toggle_auto_delete"
            ),
            InlineKeyboardButton(
                f"Warn Before Ban: {'✅' if current_settings['warn_before_ban'] else '❌'}",
                callback_data="toggle_warn_before_ban"
            )
        ],
        [
            InlineKeyboardButton(
                f"Max Warnings: {current_settings['max_warnings']}",
                callback_data="change_max_warnings"
            ),
            InlineKeyboardButton("📊 View Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("💾 Backup", callback_data="backup_db"),
            InlineKeyboardButton("🗑️ Cleanup", callback_data="cleanup_files")
        ],
        [
            InlineKeyboardButton("✅ Save", callback_data="save_settings"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_settings")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = (
        f"⚙️ *Bot Settings - Chat ID: `{chat_id}`*\n\n"
        f"Configure moderation settings for this group:\n\n"
        f"• *NSFW Filter:* {'Enabled' if current_settings['enable_nsfw_filter'] else 'Disabled'}\n"
        f"• *Violence Filter:* {'Enabled' if current_settings['enable_violence_filter'] else 'Disabled'}\n"
        f"• *Spam Filter:* {'Enabled' if current_settings['enable_spam_filter'] else 'Disabled'}\n"
        f"• *GBAN Sync:* {'Enabled' if current_settings['enable_gban_sync'] else 'Disabled'}\n"
        f"• *Auto Delete Messages:* {'Enabled' if current_settings['auto_delete_messages'] else 'Disabled'}\n"
        f"• *Warn Before Ban:* {'Enabled' if current_settings['warn_before_ban'] else 'Disabled'}\n"
        f"• *Max Warnings:* {current_settings['max_warnings']}\n"
        f"• *Language:* {current_settings['language']}\n\n"
        f"Click buttons below to toggle settings."
    )
    
    await update.message.reply_text(
        settings_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    if not await is_admin(update, context):
        await update.message.reply_text("⛔ Admin only command")
        return
    
    chat_id = update.effective_chat.id
    stats = db.get_stats(chat_id)
    bot_info = get_bot_info()
    
    stats_text = (
        f"📊 *Moderation Statistics*\n\n"
        f"*Chat ID:* `{chat_id}`\n"
        f"*Total Actions:* {sum(stats.values())}\n"
        f"*Messages Deleted:* {stats.get('deleted', 0)}\n"
        f"*Users Warned:* {stats.get('warned', 0)}\n"
        f"*Users Banned:* {stats.get('banned', 0)}\n"
        f"*Users Muted:* {stats.get('muted', 0)}\n"
        f"*Users Kicked:* {stats.get('kicked', 0)}\n"
        f"*GBANNED Users:* {stats.get('total_gbans', 0)}\n"
        f"*Total Warnings:* {stats.get('total_warnings', 0)}\n"
        f"*Total Banned Users:* {stats.get('total_banned', 0)}\n"
        f"*Sudo Users:* {stats.get('sudo_users', 0)}\n"
        f"*Today's Actions:* {stats.get('today_actions', 0)}\n\n"
        
        f"*Bot Information:*\n"
        f"• Uptime: {bot_info.get('start_time', 'N/A')}\n"
        f"• Total Users: {bot_info.get('total_users', 0)}\n"
        f"• Disk Free: {bot_info.get('disk_free', 'N/A')}\n"
        f"• Temp Files: {bot_info.get('temp_files', 0)}\n"
        f"• Backups: {bot_info.get('backup_files', 0)}\n\n"
        
        f"*Settings:*\n"
    )
    
    # Add settings info
    settings = db.get_chat_settings(chat_id)
    for key, value in settings.items():
        if key != 'chat_id':
            key_name = key.replace('_', ' ').title()
            stats_text += f"• {key_name}: `{value}`\n"
    
    # Add keyboard for actions
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
        ],
        [
            InlineKeyboardButton("🌍 GBAN Stats", callback_data="gban_stats"),
            InlineKeyboardButton("👑 Sudo Stats", callback_data="sudo_stats")
        ],
        [
            InlineKeyboardButton("🗑️ Cleanup", callback_data="cleanup_files"),
            InlineKeyboardButton("💾 Backup", callback_data="backup_now")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ===== UPDATED BUTTON CALLBACK HANDLER =====

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    
    # Check permissions
    is_user_admin = await is_admin(update, context)
    is_user_sudo = await is_sudo(update, context)
    
    try:
        if data.startswith("toggle_"):
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            setting = data.replace("toggle_", "")
            current = db.get_chat_settings(chat_id)
            
            if setting in current:
                new_value = not current[setting]
                db.update_chat_settings(chat_id, **{setting: new_value})
                
                # Update message
                await settings_command_helper(query, chat_id)
        
        elif data == "save_settings":
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            await query.edit_message_text("✅ Settings saved successfully!")
        
        elif data == "cancel_settings":
            await query.edit_message_text("❌ Settings update cancelled.")
        
        elif data.startswith("gban_page_"):
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only action")
                return
            
            page = int(data.split("_")[2])
            await gbanlist_page_helper(query, page)
        
        elif data == "gban_stats":
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only action")
                return
            
            result = await gban_system.gban_stats(update, context)
            
            if result['success']:
                stats = result['stats']
                response = (
                    f"📊 *Global Ban Statistics*\n\n"
                    f"*Total GBANNED users:* {stats.get('total_gbans', 0)}\n"
                    f"*GBANS today:* {stats.get('gbans_today', 0)}\n"
                    f"*GBANS this week:* {stats.get('gbans_week', 0)}\n"
                )
                
                keyboard = [[InlineKeyboardButton("🌍 GBAN List", callback_data="gban_page_1")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    response,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error')}")
        
        elif data == "sudo_stats":
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only action")
                return
            
            result = await sudo_system.sudo_stats(update, context)
            
            if result['success']:
                stats = result['stats']
                response = (
                    f"📊 *Sudo Statistics*\n\n"
                    f"*Total Sudo users:* {stats.get('total_sudo', 0)}\n"
                    f"*From config:* {stats.get('config_sudo', 0)}\n"
                    f"*From database:* {stats.get('db_sudo', 0)}\n"
                )
                
                keyboard = [[InlineKeyboardButton("👑 Sudo List", callback_data="show_sudo_list")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    response,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error')}")
        
        elif data == "show_sudo_list":
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only action")
                return
            
            result = await sudo_system.sudo_list(update, context)
            
            if result['success']:
                response = f"👑 *Sudo Users List*\n\n"
                response += f"*Total Sudo users:* {result['total_sudo']}\n\n"
                
                for i, sudo_user in enumerate(result['sudo_users'][:10], 1):
                    response += (
                        f"{i}. *User:* {sudo_user.get('username', f'ID: {sudo_user['user_id']}')}\n"
                        f"   *ID:* `{sudo_user['user_id']}`\n"
                        f"   *Source:* {'Config' if sudo_user['source'] == 'config' else 'Database'}\n\n"
                    )
                
                await query.edit_message_text(
                    response,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            else:
                await query.edit_message_text(f"❌ Error: {result.get('error')}")
        
        elif data.startswith("suggest_gban_"):
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only - Use /gban command")
                return
            
            # Extract user_id and reason
            parts = data.split("_")
            if len(parts) >= 4:
                user_id_to_gban = int(parts[2])
                reason = "_".join(parts[3:])
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Yes, GBAN", callback_data=f"confirm_gban_{user_id_to_gban}_{reason}"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🌍 *Global Ban Suggestion*\n\n"
                    f"User ID: `{user_id_to_gban}`\n"
                    f"Reason: {reason}\n\n"
                    f"Do you want to GBAN this user instead?\n"
                    f"(This will ban them from ALL protected chats)",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        
        elif data.startswith("confirm_gban_"):
            if not is_user_sudo:
                await query.edit_message_text("👑 Sudo only action")
                return
            
            parts = data.split("_")
            if len(parts) >= 4:
                user_id_to_gban = int(parts[2])
                reason = "_".join(parts[3:])
                
                result = await gban_system.gban_user(update, context, user_id_to_gban, reason)
                
                if result['success']:
                    await query.edit_message_text(
                        f"✅ *User Globally Banned*\n\n"
                        f"User ID: `{user_id_to_gban}`\n"
                        f"Reason: {reason}\n"
                        f"Banned by: {query.from_user.mention_html()}",
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(f"❌ GBAN Failed: {result.get('error')}")
        
        elif data == "cancel_action":
            await query.edit_message_text("❌ Action cancelled.")
        
        # Existing handlers
        elif data == "refresh_stats":
            await stats_command_helper(query, chat_id)
        
        elif data == "open_settings":
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            await settings_command_helper(query, chat_id)
        
        elif data == "cleanup_files":
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            from utils import clean_temp_files
            clean_temp_files()
            await query.edit_message_text("✅ Temporary files cleaned successfully!")
        
        elif data == "backup_now" or data == "backup_db":
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            backup_path = backup_database()
            if backup_path:
                await query.edit_message_text(f"✅ Database backed up successfully!\n\nPath: `{backup_path}`", 
                                           parse_mode='Markdown')
            else:
                await query.edit_message_text("❌ Failed to backup database")
        
        elif data.startswith("confirm_ban_"):
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            parts = data.split("_")
            if len(parts) >= 4:
                user_id_to_ban = int(parts[2])
                reason = "_".join(parts[3:])
                
                success = await ActionManager.ban_user(
                    chat_id=chat_id,
                    user_id=user_id_to_ban,
                    reason=reason,
                    context=context
                )
                
                if success:
                    await query.edit_message_text(f"✅ User {user_id_to_ban} has been banned.")
                else:
                    await query.edit_message_text(f"❌ Failed to ban user {user_id_to_ban}.")
        
        elif data == "cancel_ban":
            await query.edit_message_text("❌ Ban cancelled.")
        
        elif data.startswith("warn_"):
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            parts = data.split("_")
            if len(parts) >= 3:
                user_id_to_warn = int(parts[1])
                reason = "_".join(parts[2:])
                
                result = await ActionManager.warn_user(
                    update=update,
                    context=context,
                    user_id=user_id_to_warn,
                    reason=reason,
                    warning_type="manual"
                )
                
                if result['success']:
                    await query.edit_message_text(f"✅ User {user_id_to_warn} warned successfully.")
                else:
                    await query.edit_message_text(f"❌ Failed to warn user {user_id_to_warn}.")
        
        elif data.startswith("delete_"):
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            message_id = int(data.split("_")[1])
            success = await ActionManager.delete_message(chat_id, message_id, context)
            
            if success:
                await query.edit_message_text("✅ Message deleted successfully.")
            else:
                await query.edit_message_text("❌ Failed to delete message.")
        
        elif data == "change_max_warnings":
            if not is_user_admin:
                await query.edit_message_text("⛔ Admin only action")
                return
            
            await query.edit_message_text(
                "Please send the new maximum warnings value (1-10):\n\n"
                "Example: `3`",
                parse_mode='Markdown'
            )
            # Store state for next message
            context.user_data['awaiting_max_warnings'] = True
            context.user_data['original_message_id'] = query.message.message_id
        
        elif data == "view_stats":
            await stats_command_helper(query, chat_id)
            
    except Exception as e:
        logger.error(f"Error in button callback: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")

# ===== HELPER FUNCTIONS =====

async def gbanlist_page_helper(query, page: int):
    """Helper for GBAN list pagination"""
    result = await gban_system.gban_list(query._bot.application, page)
    
    if not result['success']:
        await query.edit_message_text(f"❌ Error: {result.get('error')}")
        return
    
    if not result['gban_list']:
        await query.edit_message_text("📭 GBAN list is empty")
        return
    
    response = f"🌍 *Global Ban List - Page {page}/{result['total_pages']}*\n\n"
    response += f"*Total GBANNED users:* {result['total_gbans']}\n\n"
    
    for i, gban in enumerate(result['gban_list'], 1):
        username = gban.get('username', '') or gban.get('first_name', '')
        if gban.get('last_name'):
            username = f"{username} {gban['last_name']}"
        
        response += (
            f"{i}. *User:* {username or 'Unknown'}\n"
            f"   *ID:* `{gban['user_id']}`\n"
            f"   *Reason:* {gban['reason']}\n"
            f"   *Banned by:* `{gban['banned_by']}`\n"
            f"   *Date:* {gban['banned_at'][:19]}\n\n"
        )
    
    # Add pagination buttons
    keyboard = []
    row = []
    if page > 1:
        row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"gban_page_{page-1}"))
    row.append(InlineKeyboardButton("📊 Stats", callback_data="gban_stats"))
    if page < result['total_pages']:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"gban_page_{page+1}"))
    keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        parse_mode='Markdown',
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def settings_command_helper(query, chat_id):
    """Helper function to update settings message"""
    current_settings = db.get_chat_settings(chat_id)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"NSFW Filter: {'✅' if current_settings['enable_nsfw_filter'] else '❌'}",
                callback_data="toggle_nsfw"
            ),
            InlineKeyboardButton(
                f"Violence Filter: {'✅' if current_settings['enable_violence_filter'] else '❌'}",
                callback_data="toggle_violence"
            )
        ],
        [
            InlineKeyboardButton(
                f"Spam Filter: {'✅' if current_settings['enable_spam_filter'] else '❌'}",
                callback_data="toggle_spam"
            ),
            InlineKeyboardButton(
                f"GBAN Sync: {'✅' if current_settings['enable_gban_sync'] else '❌'}",
                callback_data="toggle_gban_sync"
            )
        ],
        [
            InlineKeyboardButton(
                f"Auto Delete: {'✅' if current_settings['auto_delete_messages'] else '❌'}",
                callback_data="toggle_auto_delete"
            ),
            InlineKeyboardButton(
                f"Warn Before Ban: {'✅' if current_settings['warn_before_ban'] else '❌'}",
                callback_data="toggle_warn_before_ban"
            )
        ],
        [
            InlineKeyboardButton(
                f"Max Warnings: {current_settings['max_warnings']}",
                callback_data="change_max_warnings"
            ),
            InlineKeyboardButton("📊 View Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("💾 Backup", callback_data="backup_db"),
            InlineKeyboardButton("🗑️ Cleanup", callback_data="cleanup_files")
        ],
        [
            InlineKeyboardButton("✅ Save", callback_data="save_settings"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_settings")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = (
        f"⚙️ *Bot Settings - Chat ID: `{chat_id}`*\n\n"
        f"Configure moderation settings for this group:\n\n"
        f"• *NSFW Filter:* {'Enabled' if current_settings['enable_nsfw_filter'] else 'Disabled'}\n"
        f"• *Violence Filter:* {'Enabled' if current_settings['enable_violence_filter'] else 'Disabled'}\n"
        f"• *Spam Filter:* {'Enabled' if current_settings['enable_spam_filter'] else 'Disabled'}\n"
        f"• *GBAN Sync:* {'Enabled' if current_settings['enable_gban_sync'] else 'Disabled'}\n"
        f"• *Auto Delete Messages:* {'Enabled' if current_settings['auto_delete_messages'] else 'Disabled'}\n"
        f"• *Warn Before Ban:* {'Enabled' if current_settings['warn_before_ban'] else 'Disabled'}\n"
        f"• *Max Warnings:* {current_settings['max_warnings']}\n"
        f"• *Language:* {current_settings['language']}\n\n"
        f"Click buttons below to toggle settings."
    )
    
    await query.edit_message_text(
        settings_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stats_command_helper(query, chat_id):
    """Helper function to update stats message"""
    stats = db.get_stats(chat_id)
    bot_info = get_bot_info()
    
    stats_text = (
        f"📊 *Moderation Statistics*\n\n"
        f"*Chat ID:* `{chat_id}`\n"
        f"*Total Actions:* {sum(stats.values())}\n"
        f"*Messages Deleted:* {stats.get('deleted', 0)}\n"
        f"*Users Warned:* {stats.get('warned', 0)}\n"
        f"*Users Banned:* {stats.get('banned', 0)}\n"
        f"*Users Muted:* {stats.get('muted', 0)}\n"
        f"*Users Kicked:* {stats.get('kicked', 0)}\n"
        f"*GBANNED Users:* {stats.get('total_gbans', 0)}\n"
        f"*Total Warnings:* {stats.get('total_warnings', 0)}\n"
        f"*Total Banned Users:* {stats.get('total_banned', 0)}\n"
        f"*Sudo Users:* {stats.get('sudo_users', 0)}\n"
        f"*Today's Actions:* {stats.get('today_actions', 0)}\n\n"
        
        f"*Bot Information:*\n"
        f"• Uptime: {bot_info.get('start_time', 'N/A')}\n"
        f"• Total Users: {bot_info.get('total_users', 0)}\n"
        f"• Disk Free: {bot_info.get('disk_free', 'N/A')}\n"
        f"• Temp Files: {bot_info.get('temp_files', 0)}\n"
        f"• Backups: {bot_info.get('backup_files', 0)}\n\n"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats"),
            InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
        ],
        [
            InlineKeyboardButton("🌍 GBAN Stats", callback_data="gban_stats"),
            InlineKeyboardButton("👑 Sudo Stats", callback_data="sudo_stats")
        ],
        [
            InlineKeyboardButton("🗑️ Cleanup", callback_data="cleanup_files"),
            InlineKeyboardButton("💾 Backup", callback_data="backup_now")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

# ===== MESSAGE HANDLERS (UPDATED FOR GBAN) =====

async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new chat members for GBAN checking"""
    await gban_system.check_gban_on_join(update, context)

# Existing message handlers remain the same...
