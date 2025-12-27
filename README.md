# 🤖 Telegram Moderation Bot v2.0

**Advanced Content Moderation Bot with GBAN & Sudo Systems**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Termux](https://img.shields.io/badge/Termux-Compatible-brightgreen.svg)

A powerful, feature-rich moderation bot for Telegram groups with AI-based content detection, global banning system, and superuser permissions.

## ✨ Features

### 🛡️ **Content Detection**
- **NSFW Detection** - AI-powered image analysis
- **Violence Detection** - Identify violent content
- **Spam Protection** - Intelligent spam filtering
- **Text Moderation** - Inappropriate language detection
- **Copyright Monitoring** - Duplicate content detection

### 🌍 **Global Ban System (GBAN)**
- Ban users across all protected chats
- Real-time GBAN sync
- GBAN list management
- Auto-ban on join
- GBAN statistics

### 👑 **Sudo System**
- Superuser permissions
- Full command access
- User management
- System commands
- Broadcast functionality

### ⚡ **Moderation Tools**
- Warning system (3-strike rule)
- Temporary/Permanent bans
- User muting/kicking
- Whitelist/Blacklist
- Appeal system
- Report system

### 📊 **Management**
- Real-time statistics
- Configurable settings
- Database backups
- Logging system
- Auto-cleanup

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Termux (for Android) or Linux/Mac

### Installation

#### **On Termux (Android):**
```bash
# Update packages
pkg update && pkg upgrade -y

# Install dependencies
pkg install python python-pip git ffmpeg wget -y

# Clone repository
git clone https://github.com/yourusername/telegram-moderation-bot.git
cd telegram-moderation-bot

# Make executable
chmod +x start_bot.sh

# Configure bot
nano .env
# Add your BOT_TOKEN, ADMIN_IDS, SUDO_IDS

# Start bot
./start_bot.sh
```

#### **On Linux/Mac:**
```bash
# Clone repository
git clone https://github.com/yourusername/telegram-moderation-bot.git
cd telegram-moderation-bot

# Install Python dependencies
pip install -r requirements.txt

# Configure bot
cp .env.example .env
nano .env
# Add your BOT_TOKEN, ADMIN_IDS, SUDO_IDS

# Start bot
python3 main.py
```

## ⚙️ Configuration

Edit `.env` file:

```env
# Required Settings
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
SUDO_IDS=123456789

# Optional Settings
REPORT_CHANNEL_ID=-1001234567890
DATABASE_URL=sqlite:///bot.db
ENABLE_GBAN=true
ENABLE_NSFW_DETECTION=true
ENABLE_VIOLENCE_DETECTION=true
ENABLE_SPAM_DETECTION=true
```

### Getting Your Bot Token:
1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Paste it in `.env` file

### Getting Your User ID:
1. Open Telegram, search for `@userinfobot`
2. Send `/start`
3. Copy your numeric ID
4. Add it to `ADMIN_IDS` or `SUDO_IDS` in `.env`

## 🤖 Bot Setup

1. **Add bot to your group**
2. **Make bot admin with permissions:**
   - Delete messages
   - Ban users
   - Invite users via link
   - Pin messages
   - Manage chat

3. **Configure settings:**
   ```bash
   /settings
   ```
   - Toggle NSFW/Violence/Spam filters
   - Configure GBAN sync
   - Set warning limits
   - Adjust auto-delete settings

## 📋 Command Reference

### 👑 **Sudo Commands** (Full Access)
| Command | Description | Example |
|---------|-------------|---------|
| `/gban <id> <reason>` | Global ban user | `/gban 123456 Spamming` |
| `/ungban <id>` | Remove global ban | `/ungban 123456` |
| `/gbanlist` | List GBANNED users | `/gbanlist` |
| `/gbanstats` | GBAN statistics | `/gbanstats` |
| `/addsudo <id>` | Add sudo user | `/addsudo 987654` |
| `/delsudo <id>` | Remove sudo user | `/delsudo 987654` |
| `/sudolist` | List sudo users | `/sudolist` |
| `/sudostats` | Sudo statistics | `/sudostats` |
| `/shell <cmd>` | Execute shell command | `/shell pwd` |
| `/eval <code>` | Evaluate Python code | `/eval 2+2` |
| `/broadcast <msg>` | Broadcast message | `/broadcast Hello` |
| `/restart` | Restart bot | `/restart` |
| `/update` | Update bot | `/update` |

### ⚡ **Admin Commands** (Group Moderation)
| Command | Description | Example |
|---------|-------------|---------|
| `/warn <id> <reason>` | Warn user | `/warn 123456 Spam` |
| `/ban <id> <reason>` | Ban user | `/ban 123456 Rules` |
| `/mute <id> <time> <reason>` | Mute user | `/mute 123456 3600 Flood` |
| `/kick <id> <reason>` | Kick user | `/kick 123456 Spam` |
| `/whitelist <id>` | Whitelist user | `/whitelist 123456` |
| `/unwhitelist <id>` | Remove whitelist | `/unwhitelist 123456` |
| `/settings` | Configure bot | `/settings` |
| `/stats` | View statistics | `/stats` |
| `/backup` | Backup database | `/backup` |
| `/cleanup` | Clean files | `/cleanup` |

### 👤 **User Commands**
| Command | Description | Example |
|---------|-------------|---------|
| `/report <reason>` | Report message | `/report Spam` |
| `/appeal` | Appeal warning | `/appeal` |
| `/help` | Show help | `/help` |
| `/start` | Start bot | `/start` |

## 📁 Project Structure

```
telegram-moderation-bot/
├── main.py                  # Main bot file
├── config.py               # Configuration
├── database.py            # Database models
├── moderator.py           # Content moderation AI
├── handlers.py           # Bot command handlers
├── actions.py            # Action management
├── utils.py              # Utilities
├── gban.py              # Global Ban System
├── sudo.py              # Sudo System
├── requirements.txt      # Dependencies
├── .env                 # Environment variables
├── start_bot.sh         # Startup script
├── models/              # ML models directory
│   ├── __init__.py
│   └── nsfw_detector.py
├── logs/                # Logs directory
└── backup/              # Database backups
```

## 🔧 Technical Details

### Database
- **SQLite** for simplicity (default)
- **PostgreSQL** supported
- Automatic backups
- Database migration support

### AI Models
- TensorFlow/Keras for image analysis
- Rule-based fallback systems
- Customizable thresholds
- Model training support

### Security Features
- Command validation
- Rate limiting
- Permission checking
- Input sanitization
- Safe execution sandbox

### Performance
- Asynchronous operations
- Connection pooling
- Caching system
- Efficient database queries

## 🚀 Deployment

### Termux (Android)
```bash
# Run in background with tmux
pkg install tmux -y
tmux new -s bot
./start_bot.sh
# Detach: Ctrl+B, then D
# Reattach: tmux attach -t bot
```

### Linux/Mac (Production)
```bash
# Use systemd service
sudo nano /etc/systemd/system/telegram-bot.service

# Service file content:
[Unit]
Description=Telegram Moderation Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### Docker (Advanced)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "main.py"]
```

## 📊 Monitoring & Maintenance

### Daily Tasks
```bash
# Check logs
tail -f logs/bot_*.log

# Check database size
ls -lh bot.db

# Clean temp files
rm -rf temp_files/*

# Backup database
cp bot.db backup/bot_$(date +%Y%m%d_%H%M%S).db
```

### Weekly Tasks
```bash
# Update packages
pip install --upgrade -r requirements.txt

# Optimize database
sqlite3 bot.db "VACUUM;"

# Clear old logs
find logs/ -name "*.log" -mtime +30 -delete
```

## 🐛 Troubleshooting

### Common Issues

#### **Bot not responding:**
```bash
# Check if bot is running
ps aux | grep python

# Check logs
tail -100 logs/bot_*.log

# Restart bot
pkill -f "python3 main.py"
./start_bot.sh
```

#### **"Module not found" error:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### **"Bot token invalid" error:**
1. Regenerate token from @BotFather
2. Update `.env` file
3. Restart bot

#### **Cannot delete messages:**
- Ensure bot is admin
- Check bot permissions
- Bot needs "Delete messages" permission

#### **Termux memory issues:**
```bash
# Clear cache
pkg clean

# Restart Termux
exit

# Check storage
df -h
```

### Logs Location
- Main logs: `logs/bot_YYYYMMDD.log`
- Error logs: Check console output
- Debug logs: Enable debug mode in config

## 🔒 Security Best Practices

1. **Never share your bot token**
2. **Use strong admin passwords**
3. **Regularly update dependencies**
4. **Monitor bot activities**
5. **Backup database regularly**
6. **Use separate bots for testing/production**
7. **Implement rate limiting**
8. **Audit logs regularly**

## 📈 Statistics & Analytics

The bot provides comprehensive statistics:
- Total moderation actions
- User warnings/bans
- GBAN statistics
- System performance
- Storage usage
- Active users

Access via: `/stats` (admin) or `/gbanstats` (sudo)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Development Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Format code
black .
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for educational and legitimate moderation purposes only. Users are responsible for:

1. Complying with Telegram's Terms of Service
2. Following local laws and regulations
3. Using the bot ethically and responsibly
4. Reporting illegal content to authorities

The developers are not responsible for misuse of this software.

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/telegram-moderation-bot/issues)
- **Documentation:** [Wiki](https://github.com/yourusername/telegram-moderation-bot/wiki)
- **Community:** Telegram Group (link in bot description)

## 🌟 Features Roadmap

- [x] Basic moderation
- [x] GBAN system
- [x] Sudo system
- [x] AI content detection
- [ ] Web dashboard
- [ ] Multi-language support
- [ ] API integration
- [ ] Cloud deployment
- [ ] Mobile app

## 📞 Contact

For questions, support, or contributions:
- **Email:** heartbanop12@gmail.com
- **Telegram:** @infinite_sikandar
- **GitHub:** [INFINITE SIKANDER](https://github.com/Yash-coder53)
- **Telegram Group:** [Legends](https://t.me/thefriendshiphub)
---

**Made with ❤️ by the Telegram Legends Team**

*Last updated: December 2025*
