#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║    🤖 Telegram Moderation Bot v2.0              ║"
    echo "║    🚀 Advanced Content Moderator + GBAN + Sudo  ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running on Termux
check_termux() {
    if [ -d "/data/data/com.termux" ]; then
        echo -e "${YELLOW}📱 Termux environment detected${NC}"
        return 0
    else
        echo -e "${YELLOW}💻 Non-Termux environment detected${NC}"
        return 1
    fi
}

# Install dependencies for Termux
install_termux_deps() {
    echo -e "${YELLOW}🔄 Updating Termux packages...${NC}"
    pkg update -y && pkg upgrade -y
    
    echo -e "${YELLOW}📦 Installing required packages...${NC}"
    pkg install -y python python-pip git ffmpeg wget curl
    
    # Install redis if not installed
    if ! command -v redis-server &> /dev/null; then
        echo -e "${YELLOW}🔴 Installing Redis...${NC}"
        pkg install -y redis
    fi
    
    # Start Redis if not running
    if ! pgrep -x "redis-server" > /dev/null; then
        echo -e "${YELLOW}🔴 Starting Redis server...${NC}"
        redis-server --daemonize yes
        sleep 2
        echo -e "${GREEN}✅ Redis started${NC}"
    else
        echo -e "${GREEN}✅ Redis is already running${NC}"
    fi
    
    echo -e "${GREEN}✅ Termux dependencies installed${NC}"
}

# Install Python dependencies
install_python_deps() {
    echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
    
    # Check Python version
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo -e "${BLUE}Python version: $python_version${NC}"
    
    # Create virtual environment if not exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}🔧 Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
    
    # Upgrade pip
    echo -e "${YELLOW}⬆️ Upgrading pip...${NC}"
    pip install --upgrade pip
    
    # Install requirements
    echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ Python dependencies installed${NC}"
}

# Check configuration
check_config() {
    echo -e "${YELLOW}🔧 Checking configuration...${NC}"
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ Error: .env file not found!${NC}"
        echo -e "${YELLOW}📝 Creating .env file...${NC}"
        
        # Create .env from template
        cat > .env << 'EOF'
# Telegram Bot Token (REQUIRED - Get from @BotFather)
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Admin User IDs (comma separated, REQUIRED)
ADMIN_IDS=123456789,987654321

# Sudo User IDs (comma separated, full access)
SUDO_IDS=123456789

# Report Channel ID (optional - for forwarding reports)
REPORT_CHANNEL_ID=

# Database URL (sqlite is recommended for Termux)
DATABASE_URL=sqlite:///bot.db

# Redis URL (optional, for caching)
REDIS_URL=redis://localhost:6379/0

# Moderation Thresholds (0.0 to 1.0)
NSFW_THRESHOLD=0.85
VIOLENCE_THRESHOLD=0.80
SPAM_THRESHOLD=5

# Cooldown Settings (seconds)
USER_WARN_COOLDOWN=300
AUTO_DELETE_DELAY=60

# GBAN Settings
ENABLE_GBAN=true
GBAN_SYNC_INTERVAL=300  # 5 minutes

# Features (true/false)
ENABLE_NSFW_DETECTION=true
ENABLE_VIOLENCE_DETECTION=true
ENABLE_SPAM_DETECTION=true

# Maximum warnings before ban
MAX_WARNINGS=3

# Drop pending updates on startup
DROP_PENDING_UPDATES=true

# Security - Allow sudo commands (shell, eval, etc.)
ALLOW_SUDO_COMMANDS=true
EOF
        
        echo -e "${YELLOW}⚠️ Please edit .env file and add your BOT_TOKEN${NC}"
        echo -e "${YELLOW}📝 Use: nano .env${NC}"
        exit 1
    fi
    
    # Check if BOT_TOKEN is set
    if grep -q "BOT_TOKEN=YOUR_BOT_TOKEN_HERE" .env; then
        echo -e "${RED}❌ Error: Please set your BOT_TOKEN in .env file${NC}"
        echo -e "${YELLOW}📝 Get token from @BotFather on Telegram${NC}"
        exit 1
    fi
    
    # Check if ADMIN_IDS are set
    if grep -q "ADMIN_IDS=" .env && ! grep -q "ADMIN_IDS=$" .env; then
        echo -e "${GREEN}✅ Admin IDs configured${NC}"
    else
        echo -e "${YELLOW}⚠️ Warning: No ADMIN_IDS configured${NC}"
    fi
    
    # Check if SUDO_IDS are set
    if grep -q "SUDO_IDS=" .env && ! grep -q "SUDO_IDS=$" .env; then
        echo -e "${CYAN}👑 Sudo IDs configured${NC}"
    else
        echo -e "${YELLOW}⚠️ Warning: No SUDO_IDS configured${NC}"
    fi
    
    echo -e "${GREEN}✅ Configuration check passed${NC}"
}

# Create necessary directories
create_directories() {
    echo -e "${YELLOW}📁 Creating directories...${NC}"
    
    mkdir -p temp_files logs backup models
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Initialize database
init_database() {
    echo -e "${YELLOW}🗄️ Initializing database...${NC}"
    
    # Run Python script to init database
    python3 -c "
import sys
sys.path.insert(0, '.')
from database import db
print('✅ Database initialized successfully')
print('✅ GBAN system ready')
print('✅ Sudo system ready')
"
    
    echo -e "${GREEN}✅ Database ready${NC}"
}

# Start the bot
start_bot() {
    echo -e "${GREEN}🚀 Starting Telegram Moderation Bot...${NC}"
    echo -e "${CYAN}🌍 GBAN System: Enabled${NC}"
    echo -e "${PURPLE}👑 Sudo System: Enabled${NC}"
    echo -e "${YELLOW}⏳ This may take a few seconds...${NC}"
    echo -e "${BLUE}──────────────────────────────────────${NC}"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run the bot
    python3 main.py
}

# Main function
main() {
    print_banner
    
    # Check if running on Termux
    if check_termux; then
        install_termux_deps
    fi
    
    # Install Python dependencies
    install_python_deps
    
    # Check configuration
    check_config
    
    # Create directories
    create_directories
    
    # Initialize database
    init_database
    
    # Start the bot
    start_bot
    
    # Deactivate virtual environment on exit
    deactivate
}

# Run main function
main
