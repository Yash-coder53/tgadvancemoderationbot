import os
import logging
import hashlib
import asyncio
import time
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import shutil
import subprocess

from telegram import Update
from telegram.ext import ContextTypes

from config import config
from sudo import SudoSystem

logger = logging.getLogger(__name__)

# Global cache for rate limiting
user_cooldown: Dict[int, float] = {}
group_cooldown: Dict[int, float] = {}

async def download_file(file_id: str, bot, filename: Optional[str] = None) -> Optional[str]:
    """Download file from Telegram to temporary location"""
    try:
        # Get file info
        file = await bot.get_file(file_id)
        
        # Generate unique filename if not provided
        if not filename:
            file_ext = "jpg"  # Default extension
            if hasattr(file, 'file_path') and file.file_path:
                file_ext = file.file_path.split('.')[-1] if '.' in file.file_path else 'jpg'
            
            filename = f"{file_id}_{int(time.time())}.{file_ext}"
        
        # Create temp file path
        temp_path = config.TEMP_DIR / filename
        
        # Download file
        await file.download_to_drive(temp_path)
        
        logger.debug(f"✅ Downloaded file {file_id} to {temp_path}")
        return str(temp_path)
        
    except Exception as e:
        logger.error(f"❌ Failed to download file {file_id}: {e}")
        return None

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin in the chat"""
    try:
        user_id = update.effective_user.id
        
        # Check if user is sudo (sudo users have admin rights everywhere)
        if SudoSystem.is_sudo(user_id):
            return True
        
        # Check if user is in config admin list
        if user_id in config.ADMIN_IDS:
            return True
        
        # For groups, check Telegram admin status
        if update.effective_chat.type in ['group', 'supergroup']:
            try:
                admins = await update.effective_chat.get_administrators()
                for admin in admins:
                    if admin.user.id == user_id:
                        return True
            except Exception as e:
                logger.error(f"Error getting admins: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False

async def is_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is sudo"""
    try:
        user_id = update.effective_user.id
        return SudoSystem.is_sudo(user_id)
    except Exception as e:
        logger.error(f"Error checking sudo status: {e}")
        return False

def format_bytes(size: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def format_time(seconds: int) -> str:
    """Format seconds to human readable time"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"

def check_cooldown(user_id: int, cooldown_seconds: int = 30) -> bool:
    """Check if user is in cooldown period"""
    current_time = time.time()
    
    if user_id in user_cooldown:
        last_action = user_cooldown[user_id]
        if current_time - last_action < cooldown_seconds:
            return False
    
    user_cooldown[user_id] = current_time
    return True

def check_group_cooldown(chat_id: int, cooldown_seconds: int = 10) -> bool:
    """Check if group is in cooldown period"""
    current_time = time.time()
    
    if chat_id in group_cooldown:
        last_action = group_cooldown[chat_id]
        if current_time - last_action < cooldown_seconds:
            return False
    
    group_cooldown[chat_id] = current_time
    return True

def clean_temp_files(max_age_hours: int = 1):
    """Clean old temporary files"""
    current_time = time.time()
    
    for file_path in config.TEMP_DIR.glob("*"):
        try:
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_hours * 3600:
                file_path.unlink()
                logger.debug(f"Cleaned temp file: {file_path.name}")
        except Exception as e:
            logger.error(f"Error cleaning temp file {file_path}: {e}")

def calculate_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return ""

def backup_database():
    """Create database backup"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = config.BACKUP_DIR / f"bot_backup_{timestamp}.db"
        
        shutil.copy2("bot.db", backup_file)
        
        # Keep only last 7 backups
        backups = sorted(config.BACKUP_DIR.glob("bot_backup_*.db"))
        if len(backups) > 7:
            for old_backup in backups[:-7]:
                old_backup.unlink()
        
        logger.info(f"✅ Database backed up to {backup_file.name}")
        return str(backup_file)
        
    except Exception as e:
        logger.error(f"❌ Failed to backup database: {e}")
        return None

async def schedule_cleanup():
    """Schedule periodic cleanup tasks"""
    while True:
        try:
            # Clean temp files every hour
            clean_temp_files()
            
            # Backup database every 6 hours
            current_hour = datetime.now().hour
            if current_hour % 6 == 0:
                backup_database()
            
            # Clear old cooldown entries
            current_time = time.time()
            global user_cooldown, group_cooldown
            
            user_cooldown = {k: v for k, v in user_cooldown.items() 
                           if current_time - v < 3600}
            group_cooldown = {k: v for k, v in group_cooldown.items() 
                            if current_time - v < 3600}
            
            await asyncio.sleep(3600)  # Run every hour
            
        except Exception as e:
            logger.error(f"Error in cleanup scheduler: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

def get_bot_info() -> Dict[str, Any]:
    """Get bot information and statistics"""
    from database import db
    
    try:
        stats = db.get_stats()
        disk_usage = shutil.disk_usage(".")
        
        info = {
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_users": stats.get("total_users", 0),
            "total_warnings": stats.get("total_warnings", 0),
            "total_banned": stats.get("total_banned", 0),
            "total_gbans": stats.get("total_gbans", 0),
            "sudo_users": stats.get("sudo_users", 0),
            "today_actions": stats.get("today_actions", 0),
            "disk_free": format_bytes(disk_usage.free),
            "disk_used": format_bytes(disk_usage.used),
            "disk_total": format_bytes(disk_usage.total),
            "temp_files": len(list(config.TEMP_DIR.glob("*"))),
            "backup_files": len(list(config.BACKUP_DIR.glob("*.db")))
        }
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        return {}

async def execute_shell(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute shell command (sudo only)"""
    try:
        # Security check - only allow safe commands
        dangerous_commands = ['rm -rf', 'format', 'dd', 'mkfs', 'shutdown', 'reboot', 'halt']
        for dangerous in dangerous_commands:
            if dangerous in command.lower():
                return {
                    'success': False,
                    'error': f'Dangerous command blocked: {dangerous}',
                    'output': '',
                    'return_code': 1
                }
        
        # Execute command
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                'success': process.returncode == 0,
                'return_code': process.returncode,
                'output': stdout.decode('utf-8', errors='ignore'),
                'error': stderr.decode('utf-8', errors='ignore')
            }
            
        except asyncio.TimeoutError:
            process.kill()
            return {
                'success': False,
                'error': f'Command timed out after {timeout} seconds',
                'output': '',
                'return_code': -1
            }
            
    except Exception as e:
        logger.error(f"Error executing shell command: {e}")
        return {
            'success': False,
            'error': str(e),
            'output': '',
            'return_code': -1
        }

async def eval_python(code: str, timeout: int = 10) -> Dict[str, Any]:
    """Evaluate Python code (sudo only) - DANGEROUS!"""
    try:
        # Security checks
        dangerous_modules = ['os', 'sys', 'subprocess', 'shutil', 'socket', 'importlib']
        dangerous_keywords = ['__import__', 'eval', 'exec', 'compile', 'open', 'file']
        
        for module in dangerous_modules:
            if f'import {module}' in code or f'from {module}' in code:
                return {
                    'success': False,
                    'error': f'Import of dangerous module blocked: {module}',
                    'result': None
                }
        
        for keyword in dangerous_keywords:
            if keyword in code:
                return {
                    'success': False,
                    'error': f'Dangerous keyword blocked: {keyword}',
                    'result': None
                }
        
        # Execute in isolated namespace
        namespace = {
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'bool': bool,
                'type': type,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round
            }
        }
        
        # Execute with timeout
        async def execute():
            try:
                exec(f"result = {code}" if not code.strip().startswith((' ', '\t', '\n')) else code, namespace)
                return namespace.get('result', 'No result')
            except Exception as e:
                return f"Error: {str(e)}"
        
        result = await asyncio.wait_for(execute(), timeout=timeout)
        
        return {
            'success': True,
            'result': str(result),
            'error': None
        }
        
    except asyncio.TimeoutError:
        return {
            'success': False,
            'error': f'Code execution timed out after {timeout} seconds',
            'result': None
        }
    except Exception as e:
        logger.error(f"Error evaluating Python code: {e}")
        return {
            'success': False,
            'error': str(e),
            'result': None
        }
