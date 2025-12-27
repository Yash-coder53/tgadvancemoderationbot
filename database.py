import sqlite3
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db_path = Path("bot.db")
        self.lock = threading.RLock()
        self._init_db()
        self._initialized = True
        logger.info("Database initialized")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    warnings INTEGER DEFAULT 0,
                    is_banned BOOLEAN DEFAULT FALSE,
                    is_gbanned BOOLEAN DEFAULT FALSE,
                    gban_reason TEXT,
                    gbanned_by INTEGER,
                    gbanned_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # GBAN list table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gban_list (
                    user_id INTEGER PRIMARY KEY,
                    reason TEXT NOT NULL,
                    banned_by INTEGER NOT NULL,
                    banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # Warnings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS warnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    warning_type TEXT NOT NULL,
                    reason TEXT,
                    moderator_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
                )
            ''')
            
            # Moderated content table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS moderated_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    chat_id INTEGER,
                    user_id INTEGER,
                    content_type TEXT,
                    action_taken TEXT,
                    reason TEXT,
                    confidence REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Copyright claims table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS copyright_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    claimant_name TEXT,
                    claimant_email TEXT,
                    content_url TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    chat_id INTEGER PRIMARY KEY,
                    enable_nsfw_filter BOOLEAN DEFAULT TRUE,
                    enable_violence_filter BOOLEAN DEFAULT TRUE,
                    enable_spam_filter BOOLEAN DEFAULT TRUE,
                    enable_gban_sync BOOLEAN DEFAULT TRUE,
                    auto_delete_messages BOOLEAN DEFAULT TRUE,
                    warn_before_ban BOOLEAN DEFAULT TRUE,
                    max_warnings INTEGER DEFAULT 3,
                    language TEXT DEFAULT 'en'
                )
            ''')
            
            # Whitelist table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')
            
            # Sudo users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sudo_users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    added_by INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    permissions TEXT DEFAULT 'all'
                )
            ''')
            
            # Cache table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_warnings_user_id ON warnings(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_warnings_chat_id ON warnings(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_moderated_content_user_id ON moderated_content(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_moderated_content_chat_id ON moderated_content(chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_user_chat ON whitelist(user_id, chat_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_gban_list_active ON gban_list(is_active)')
            
            conn.commit()
            conn.close()
    
    def add_user(self, user_id: int, username: str = "", first_name: str = "", last_name: str = ""):
        """Add or update user"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, datetime.now()))
                
                conn.commit()
                logger.debug(f"User {user_id} added/updated")
            except Exception as e:
                logger.error(f"Error adding user {user_id}: {e}")
                conn.rollback()
            finally:
                conn.close()
    
    # GBAN METHODS
    def add_to_gban(self, user_id: int, reason: str, banned_by: int) -> bool:
        """Add user to global ban list"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO gban_list 
                    (user_id, reason, banned_by, is_active)
                    VALUES (?, ?, ?, TRUE)
                ''', (user_id, reason, banned_by))
                
                # Update user record
                cursor.execute('''
                    UPDATE users 
                    SET is_gbanned = TRUE, gban_reason = ?, gbanned_by = ?, gbanned_at = ?
                    WHERE user_id = ?
                ''', (reason, banned_by, datetime.now(), user_id))
                
                conn.commit()
                logger.info(f"User {user_id} added to GBAN list by {banned_by}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding user {user_id} to GBAN: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def remove_from_gban(self, user_id: int) -> bool:
        """Remove user from global ban list"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    UPDATE gban_list 
                    SET is_active = FALSE 
                    WHERE user_id = ? AND is_active = TRUE
                ''', (user_id,))
                
                # Update user record
                cursor.execute('''
                    UPDATE users 
                    SET is_gbanned = FALSE, gban_reason = NULL, gbanned_by = NULL, gbanned_at = NULL
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"User {user_id} removed from GBAN list")
                
                return success
                
            except Exception as e:
                logger.error(f"Error removing user {user_id} from GBAN: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def is_user_gbanned(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """Check if user is globally banned"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT reason FROM gban_list 
                    WHERE user_id = ? AND is_active = TRUE
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return True, result['reason']
                return False, None
                
            except Exception as e:
                logger.error(f"Error checking GBAN status for user {user_id}: {e}")
                return False, None
            finally:
                conn.close()
    
    def get_gban_list(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get global ban list"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT g.*, u.username, u.first_name, u.last_name 
                    FROM gban_list g
                    LEFT JOIN users u ON g.user_id = u.user_id
                    WHERE g.is_active = TRUE
                    ORDER BY g.banned_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
                
                return [dict(row) for row in cursor.fetchall()]
                
            except Exception as e:
                logger.error(f"Error getting GBAN list: {e}")
                return []
            finally:
                conn.close()
    
    def get_gban_stats(self) -> Dict[str, int]:
        """Get GBAN statistics"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                stats = {}
                
                # Total GBANs
                cursor.execute('SELECT COUNT(*) FROM gban_list WHERE is_active = TRUE')
                stats['total_gbans'] = cursor.fetchone()[0]
                
                # GBANs today
                cursor.execute('''
                    SELECT COUNT(*) FROM gban_list 
                    WHERE is_active = TRUE AND DATE(banned_at) = DATE('now')
                ''')
                stats['gbans_today'] = cursor.fetchone()[0]
                
                # GBANs this week
                cursor.execute('''
                    SELECT COUNT(*) FROM gban_list 
                    WHERE is_active = TRUE AND banned_at >= DATE('now', '-7 days')
                ''')
                stats['gbans_week'] = cursor.fetchone()[0]
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting GBAN stats: {e}")
                return {}
            finally:
                conn.close()
    
    # SUDO METHODS
    def is_sudo_user(self, user_id: int) -> bool:
        """Check if user is sudo"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT 1 FROM sudo_users WHERE user_id = ?', (user_id,))
                return cursor.fetchone() is not None
                
            except Exception as e:
                logger.error(f"Error checking sudo status for user {user_id}: {e}")
                return False
            finally:
                conn.close()
    
    def add_sudo_user(self, user_id: int, username: str = "", added_by: int = 0) -> bool:
        """Add sudo user"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO sudo_users (user_id, username, added_by)
                    VALUES (?, ?, ?)
                ''', (user_id, username, added_by))
                
                conn.commit()
                logger.info(f"User {user_id} added as sudo by {added_by}")
                return True
                
            except Exception as e:
                logger.error(f"Error adding sudo user {user_id}: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def remove_sudo_user(self, user_id: int) -> bool:
        """Remove sudo user"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('DELETE FROM sudo_users WHERE user_id = ?', (user_id,))
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"User {user_id} removed from sudo")
                
                return success
                
            except Exception as e:
                logger.error(f"Error removing sudo user {user_id}: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()
    
    def get_sudo_users(self) -> List[Dict]:
        """Get all sudo users"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT s.*, u.first_name, u.last_name 
                    FROM sudo_users s
                    LEFT JOIN users u ON s.user_id = u.user_id
                    ORDER BY s.added_at
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
            except Exception as e:
                logger.error(f"Error getting sudo users: {e}")
                return []
            finally:
                conn.close()
    
    # Existing methods (updated for GBAN integration)
    def add_warning(self, user_id: int, chat_id: int, warning_type: str, 
                   reason: str, moderator_id: int) -> int:
        """Add warning for user"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Check if user is GBANNED
                cursor.execute('SELECT 1 FROM gban_list WHERE user_id = ? AND is_active = TRUE', (user_id,))
                if cursor.fetchone():
                    logger.info(f"User {user_id} is GBANNED, skipping warning")
                    return 999  # Special code for GBANNED users
                
                # Add warning
                cursor.execute('''
                    INSERT INTO warnings 
                    (user_id, chat_id, warning_type, reason, moderator_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, chat_id, warning_type, reason, moderator_id))
                
                # Update user warning count
                cursor.execute('''
                    UPDATE users 
                    SET warnings = warnings + 1 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                
                # Get current warning count
                cursor.execute('SELECT warnings FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                warnings = result['warnings'] if result else 0
                
                logger.info(f"Warning added for user {user_id}. Total warnings: {warnings}")
                return warnings
                
            except Exception as e:
                logger.error(f"Error adding warning for user {user_id}: {e}")
                conn.rollback()
                return 0
            finally:
                conn.close()
    
    def is_user_whitelisted(self, user_id: int, chat_id: int) -> bool:
        """Check if user is whitelisted"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT 1 FROM whitelist 
                    WHERE user_id = ? AND chat_id = ?
                ''', (user_id, chat_id))
                
                return cursor.fetchone() is not None
                
            except Exception as e:
                logger.error(f"Error checking whitelist for user {user_id}: {e}")
                return False
            finally:
                conn.close()
    
    def get_chat_settings(self, chat_id: int) -> Dict:
        """Get chat settings"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT * FROM settings WHERE chat_id = ?', (chat_id,))
                result = cursor.fetchone()
                
                if result:
                    settings = dict(result)
                else:
                    # Default settings
                    settings = {
                        'chat_id': chat_id,
                        'enable_nsfw_filter': True,
                        'enable_violence_filter': True,
                        'enable_spam_filter': True,
                        'enable_gban_sync': True,
                        'auto_delete_messages': True,
                        'warn_before_ban': True,
                        'max_warnings': 3,
                        'language': 'en'
                    }
                    # Save default settings
                    cursor.execute('''
                        INSERT INTO settings 
                        (chat_id, enable_nsfw_filter, enable_violence_filter, enable_spam_filter,
                         enable_gban_sync, auto_delete_messages, warn_before_ban, max_warnings, language)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', tuple(settings.values()))
                    conn.commit()
                
                return settings
                
            except Exception as e:
                logger.error(f"Error getting settings for chat {chat_id}: {e}")
                # Return default settings
                return {
                    'chat_id': chat_id,
                    'enable_nsfw_filter': True,
                    'enable_violence_filter': True,
                    'enable_spam_filter': True,
                    'enable_gban_sync': True,
                    'auto_delete_messages': True,
                    'warn_before_ban': True,
                    'max_warnings': 3,
                    'language': 'en'
                }
            finally:
                conn.close()
    
    def update_chat_settings(self, chat_id: int, **kwargs):
        """Update chat settings"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                # Get current settings
                current = self.get_chat_settings(chat_id)
                
                # Update with new values
                for key, value in kwargs.items():
                    if key in current and key != 'chat_id':
                        current[key] = value
                
                # Update database
                cursor.execute('''
                    INSERT OR REPLACE INTO settings 
                    (chat_id, enable_nsfw_filter, enable_violence_filter, enable_spam_filter,
                     enable_gban_sync, auto_delete_messages, warn_before_ban, max_warnings, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chat_id,
                    current['enable_nsfw_filter'],
                    current['enable_violence_filter'],
                    current['enable_spam_filter'],
                    current['enable_gban_sync'],
                    current['auto_delete_messages'],
                    current['warn_before_ban'],
                    current['max_warnings'],
                    current['language']
                ))
                
                conn.commit()
                logger.info(f"Settings updated for chat {chat_id}")
                
            except Exception as e:
                logger.error(f"Error updating settings for chat {chat_id}: {e}")
                conn.rollback()
            finally:
                conn.close()
    
    def get_stats(self, chat_id: Optional[int] = None) -> Dict:
        """Get moderation statistics"""
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            try:
                stats = {}
                
                if chat_id:
                    # Chat-specific stats
                    cursor.execute('''
                        SELECT action_taken, COUNT(*) as count 
                        FROM moderated_content 
                        WHERE chat_id = ? 
                        GROUP BY action_taken
                    ''', (chat_id,))
                else:
                    # Global stats
                    cursor.execute('''
                        SELECT action_taken, COUNT(*) as count 
                        FROM moderated_content 
                        GROUP BY action_taken
                    ''')
                
                for row in cursor.fetchall():
                    stats[row['action_taken']] = row['count']
                
                # Get GBAN stats
                gban_stats = self.get_gban_stats()
                stats.update(gban_stats)
                
                # Get total warnings
                cursor.execute('SELECT COUNT(*) FROM warnings')
                stats['total_warnings'] = cursor.fetchone()[0]
                
                # Get total banned users
                cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = TRUE')
                stats['total_banned'] = cursor.fetchone()[0]
                
                # Get total users
                cursor.execute('SELECT COUNT(*) FROM users')
                stats['total_users'] = cursor.fetchone()[0]
                
                # Get sudo users count
                cursor.execute('SELECT COUNT(*) FROM sudo_users')
                stats['sudo_users'] = cursor.fetchone()[0]
                
                # Get today's actions
                cursor.execute('''
                    SELECT COUNT(*) FROM moderated_content 
                    WHERE DATE(created_at) = DATE('now')
                ''')
                stats['today_actions'] = cursor.fetchone()[0]
                
                return stats
                
            except Exception as e:
                logger.error(f"Error getting stats: {e}")
                return {}
            finally:
                conn.close()
    
    def backup_database(self) -> str:
        """Create database backup"""
        backup_path = Path("backup") / f"bot_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        with self.lock:
            try:
                # Close any existing connections
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                conn.close()
                
                # Copy database file
                import shutil
                shutil.copy2(self.db_path, backup_path)
                
                logger.info(f"Database backed up to {backup_path}")
                return str(backup_path)
                
            except Exception as e:
                logger.error(f"Error backing up database: {e}")
                return ""

# Create global database instance
db = Database()
