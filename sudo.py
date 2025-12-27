"""
Sudo System - Superuser permissions
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import config
from database import db
from utils import is_admin

logger = logging.getLogger(__name__)

class SudoSystem:
    """Sudo System Manager"""
    
    @staticmethod
    def is_sudo(user_id: int) -> bool:
        """Check if user is sudo (from config or database)"""
        # Check config first
        if user_id in config.SUDO_IDS:
            return True
        
        # Check database
        return db.is_sudo_user(user_id)
    
    @staticmethod
    async def add_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE,
                      user_id: int) -> Dict:
        """Add user to sudo"""
        try:
            # Check if caller is sudo
            caller_id = update.effective_user.id
            if not SudoSystem.is_sudo(caller_id):
                return {'success': False, 'error': 'Only sudo users can add sudo users'}
            
            # Check if user is already sudo
            if SudoSystem.is_sudo(user_id):
                return {'success': False, 'error': 'User is already sudo'}
            
            # Get user info
            user_info = ""
            try:
                user = await context.bot.get_chat(user_id)
                user_info = f"{user.first_name} (@{user.username})" if user.username else user.first_name
                
                # Add to database
                success = db.add_sudo_user(
                    user_id=user_id,
                    username=user.username or "",
                    added_by=caller_id
                )
                
                if not success:
                    return {'success': False, 'error': 'Failed to add to sudo database'}
                
            except Exception as e:
                logger.error(f"Error getting user info for sudo: {e}")
                # Still try to add with limited info
                db.add_sudo_user(user_id=user_id, added_by=caller_id)
            
            result = {
                'success': True,
                'user_id': user_id,
                'user_info': user_info,
                'added_by': caller_id,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ User {user_id} added as sudo by {caller_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error adding sudo user: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def remove_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE,
                         user_id: int) -> Dict:
        """Remove user from sudo"""
        try:
            # Check if caller is sudo
            caller_id = update.effective_user.id
            if not SudoSystem.is_sudo(caller_id):
                return {'success': False, 'error': 'Only sudo users can remove sudo users'}
            
            # Check if user is sudo
            if not SudoSystem.is_sudo(user_id):
                return {'success': False, 'error': 'User is not sudo'}
            
            # Cannot remove yourself
            if user_id == caller_id:
                return {'success': False, 'error': 'You cannot remove yourself from sudo'}
            
            # Remove from database
            success = db.remove_sudo_user(user_id)
            
            if not success:
                return {'success': False, 'error': 'Failed to remove from sudo database'}
            
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
                'removed_by': caller_id,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ User {user_id} removed from sudo by {caller_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error removing sudo user: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    async def sudo_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """Get list of all sudo users"""
        try:
            # Get sudo users from database
            db_sudo_users = db.get_sudo_users()
            
            # Combine with config sudo users
            all_sudo_users = []
            
            # Add config sudo users
            for sudo_id in config.SUDO_IDS:
                user_info = ""
                try:
                    user = await context.bot.get_chat(sudo_id)
                    user_info = f"{user.first_name} (@{user.username})" if user.username else user.first_name
                except:
                    user_info = f"User {sudo_id}"
                
                all_sudo_users.append({
                    'user_id': sudo_id,
                    'username': user_info,
                    'source': 'config',
                    'added_by': 'system'
                })
            
            # Add database sudo users
            for sudo_user in db_sudo_users:
                all_sudo_users.append({
                    'user_id': sudo_user['user_id'],
                    'username': sudo_user['username'] or f"User {sudo_user['user_id']}",
                    'first_name': sudo_user.get('first_name', ''),
                    'last_name': sudo_user.get('last_name', ''),
                    'source': 'database',
                    'added_by': sudo_user['added_by'],
                    'added_at': sudo_user['added_at']
                })
            
            result = {
                'success': True,
                'total_sudo': len(all_sudo_users),
                'sudo_users': all_sudo_users,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting sudo list: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_sudo_permissions(user_id: int) -> List[str]:
        """Get sudo user permissions"""
        if not SudoSystem.is_sudo(user_id):
            return []
        
        # Default permissions for sudo users
        permissions = [
            'all',  # Full access
            'gban',  # Global ban
            'ungban',  # Remove global ban
            'add_sudo',  # Add sudo users
            'remove_sudo',  # Remove sudo users
            'broadcast',  # Broadcast messages
            'eval',  # Execute code (dangerous!)
            'shell',  # Execute shell commands
            'db_query',  # Direct database access
            'restart',  # Restart bot
            'update',  # Update bot
            'maintenance'  # Maintenance mode
        ]
        
        return permissions
    
    @staticmethod
    async def sudo_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Dict:
        """Get sudo statistics"""
        try:
            sudo_list_result = await SudoSystem.sudo_list(update, context)
            
            if not sudo_list_result['success']:
                return sudo_list_result
            
            stats = {
                'total_sudo': sudo_list_result['total_sudo'],
                'config_sudo': len(config.SUDO_IDS),
                'db_sudo': len([u for u in sudo_list_result['sudo_users'] if u['source'] == 'database']),
                'timestamp': datetime.now().isoformat()
            }
            
            result = {
                'success': True,
                'stats': stats
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting sudo stats: {e}")
            return {'success': False, 'error': str(e)}

# Global sudo instance
sudo_system = SudoSystem()
