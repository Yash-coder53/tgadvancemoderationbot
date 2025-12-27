"""
Global Ban (GBAN) System
Allows banning users across all chats where bot is admin
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from config import config
from database import db
from utils import is_admin

logger = logging.getLogger(__name__)

class GBanSystem:
    """Global Ban System Manager"""
    
    @staticmethod
    async def gban_user(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       user_id: int, reason: str) -> Dict:
        """Globally ban a user"""
        try:
            # Check if user is trying to GBAN themselves
            if user_id == update.effective_user.id:
                return {'success': False, 'error': 'You cannot GBAN yourself'}
            
            # Check if user is already GBANNED
            is_gbanned, existing_reason = db.is_user_gbanned(user_id)
            if is_gbanned:
                return {'success': False, 'error': f'User is already GBANNED. Reason: {existing_reason}'}
            
            # Get user info
            user_info = ""
            try:
                user = await context.bot.get_chat(user_id)
                user_info = f"{user.first_name} (@{user.username})" if user.username else user.first_name
            except:
                user_info = f"User {user_id}"
            
            # Add to GBAN list
            success = db.add_to_gban(
                user_id=user_id,
                reason=reason,
                banned_by=update.effective_user.id
            )
            
            if not success:
                return {'success': False, 'error': 'Failed to add to GBAN database'}
            
            # Ban user from all known chats
            banned_chats = await GBanSystem._ban_from_all_chats(user_id, context, reason)
            
            result = {
                'success': True,
                'user_id': user_id,
                'user_info': user_info,
                'reason': reason,
                'banned_by': update.effective_user.id,
                'banned_chats': banned_chats,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ User {user_id} GBANNED by {update.effective_user.id}. Reason: {reason}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in GBAN: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def ungban_user(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_id: int) -> Dict:
        """Remove user from global ban"""
        try:
            # Check if user is GBANNED
            is_gbanned, reason = db.is_user_gbanned(user_id)
            if not is_gbanned:
                return {'success': False, 'error': 'User is not GBANNED'}
            
            # Remove from GBAN list
            success = db.remove_from_gban(user_id)
            
            if not success:
                return {'success': False, 'error': 'Failed to remove from GBAN database'}
            
            # Unban user from all known chats
            unbanned_chats = await GBanSystem._unban_from_all_chats(user_id, context)
            
            # Get user info
            user_info = ""
            try:
                user = await context.bot.get_chat(user_id)
                user_info = f"{user.first_name} (@{user.username})" if user.username else user.first_name
            except:
                user_info = f"User {user_id}"
            
            result = {
                'success': True,
                'user_id': user_id,
                'user_info': user_info,
                'removed_by': update.effective_user.id,
                'unbanned_chats': unbanned_chats,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ User {user_id} UNGBANNED by {update.effective_user.id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in UNGBAN: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def _ban_from_all_chats(user_id: int, context: ContextTypes.DEFAULT_TYPE, 
                                reason: str) -> List[int]:
        """Ban user from all chats where bot is admin"""
        banned_chats = []
        
        # Note: Telegram Bot API doesn't provide a way to get all chats
        # where bot is admin. This would need to be implemented with
        # a database of known chats.
        
        # For now, we'll just log it and implement the ban when user
        # tries to join a chat where bot is admin
        
        logger.info(f"User {user_id} added to GBAN list. Will be banned from chats on join.")
        return banned_chats
    
    @staticmethod
    async def _unban_from_all_chats(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[int]:
        """Unban user from all chats"""
        unbanned_chats = []
        
        # Similar to ban, we need a list of chats
        # For now, just log
        
        logger.info(f"User {user_id} removed from GBAN list.")
        return unbanned_chats
    
    @staticmethod
    async def check_gban_on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check if joining user is GBANNED"""
        try:
            # Check if it's a new chat member
            if not update.message or not update.message.new_chat_members:
                return
            
            chat_id = update.effective_chat.id
            
            # Check if GBAN sync is enabled for this chat
            settings = db.get_chat_settings(chat_id)
            if not settings.get('enable_gban_sync', True):
                return
            
            for new_member in update.message.new_chat_members:
                user_id = new_member.id
                
                # Check if user is GBANNED
                is_gbanned, reason = db.is_user_gbanned(user_id)
                
                if is_gbanned:
                    # Ban the user
                    try:
                        await context.bot.ban_chat_member(
                            chat_id=chat_id,
                            user_id=user_id,
                            until_date=None
                        )
                        
                        # Send notification
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🚫 *GBANNED User Detected*\n\n"
                                 f"User: {new_member.mention_html()}\n"
                                 f"ID: `{user_id}`\n"
                                 f"Reason: {reason}\n\n"
                                 f"This user is globally banned from all protected chats.",
                            parse_mode='HTML'
                        )
                        
                        logger.info(f"✅ GBANNED user {user_id} banned from chat {chat_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to ban GBANNED user {user_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error checking GBAN on join: {e}")
    
    @staticmethod
    async def gban_list(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       page: int = 1) -> Dict:
        """Get GBAN list with pagination"""
        try:
            limit = 10
            offset = (page - 1) * limit
            
            gban_list = db.get_gban_list(limit=limit, offset=offset)
            total_gbans = db.get_gban_stats().get('total_gbans', 0)
            total_pages = (total_gbans + limit - 1) // limit
            
            result = {
                'success': True,
                'page': page,
                'total_pages': total_pages,
                'total_gbans': total_gbans,
                'gban_list': gban_list
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting GBAN list: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def gban_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """Get GBAN statistics"""
        try:
            stats = db.get_gban_stats()
            
            result = {
                'success': True,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting GBAN stats: {e}")
            return {'success': False, 'error': str(e)}

# Global GBAN instance
gban_system = GBanSystem()
