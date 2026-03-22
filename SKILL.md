# SwarmIA Skill for OpenClaw

Installs and manages SwarmIA - Enhanced AI Assistant System

## Description

SwarmIA is an "enhanced AI assistant system" that is "brutal in every sense" compared to OpenClaw. It features:

- **Priority-based task processing** with CRITICAL priority for user messages
- **WhatsApp & Telegram integration** with independent APIs
- **Dual AI support**: DeepSeek API and Llama local models
- **Agents that complete tasks fully** without leaving things half-done
- **Elegant dashboard** with mandatory password change
- **Auto-update system** from GitHub
- **Aggressive methods** for system access (SSH, remote access)

## Installation

### As OpenClaw Skill
```bash
# Install via clawhub
clawhub install nicky686-22/SwarmIA

# Or manually
cd ~/.openclaw/skills
git clone https://github.com/nicky686-22/SwarmIA.git
```

### Standalone Installation
```bash
# Linux
curl -sSL https://raw.githubusercontent.com/nicky686-22/SwarmIA/main/scripts/install.sh | sudo bash

# Windows
# Download install.bat and run as Administrator
```

## Usage

### OpenClaw Commands
```
/swarmia install      - Install SwarmIA system
/swarmia start        - Start SwarmIA service
/swarmia stop         - Stop SwarmIA service
/swarmia status       - Check SwarmIA status
/swarmia update       - Check for updates
/swarmia dashboard    - Open dashboard in browser
/swarmia config       - Show configuration
/swarmia logs         - Show recent logs
/swarmia backup       - Create backup
/swarmia restore      - Restore from backup
/swarmia uninstall    - Uninstall SwarmIA
```

### Direct Access
After installation, access:
- Dashboard: `http://[YOUR_IP]:3000`
- Default credentials: admin/admin (change immediately!)
- API Docs: `http://[YOUR_IP]:3000/docs`

## Features

### 🚀 Enhanced Performance
- **CRITICAL priority** for user messages (never queued)
- **Agents complete tasks fully** (no half-done work)
- **Real-time monitoring** with detailed statistics
- **Auto-scaling** based on load

### 🔧 Aggressive System Access
- **SSH integration** for remote system management
- **Multiple access methods** (Web, API, CLI, SSH)
- **System command execution** with elevated privileges
- **File system access** with full permissions
- **Network scanning** and device discovery
- **Service management** (start/stop/restart services)

### 🤖 Dual AI Support
- **DeepSeek API** (requires token)
- **Llama local models** (GGUF format)
- **Model switching** on the fly
- **Context management** with conversation history

### 📱 Communication
- **WhatsApp Business API** integration
- **Telegram Bot API** integration
- **Multi-user support** with permissions
- **Message queuing** with priority
- **Media support** (images, documents, audio)

### 🛡️ Security
- **JWT authentication** with refresh tokens
- **Mandatory password change** on first login
- **IP whitelisting** for dashboard access
- **Rate limiting** and DDoS protection
- **Activity logging** with audit trails

### 🔄 Auto Updates
- **GitHub update checking** every 24 hours
- **One-click updates** from dashboard
- **Rollback capability** if update fails
- **Changelog display** for each version

## Configuration

### AI Configuration
```yaml
ai:
  default_provider: "deepseek"  # or "llama"
  deepseek:
    api_key: "your-deepseek-token"
    model: "deepseek-chat"
  llama:
    model_path: "/path/to/model.gguf"
    model_name: "My Local Model"
```

### Communication Configuration
```yaml
whatsapp:
  enabled: true
  provider: "twilio"
  account_sid: "your-account-sid"
  auth_token: "your-auth-token"
  from_number: "+1234567890"

telegram:
  enabled: true
  bot_token: "your-bot-token"
  allowed_users: ["user_id_1", "user_id_2"]
```

### Aggressive Methods Configuration
```yaml
aggressive_methods:
  enabled: true
  ssh:
    enabled: true
    username: "swarmia"
    key_path: "/etc/swarmia/ssh_key"
  system_commands:
    enabled: true
    allowed_commands: ["systemctl", "apt", "yum", "pacman"]
  file_access:
    enabled: true
    allowed_paths: ["/home", "/var/log", "/etc/swarmia"]
```

## File Structure

```
SwarmIA/
├── SKILL.md                    # This file
├── README.md                   # Project README
├── LICENSE                     # MIT License
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
├── scripts/
│   ├── install.sh             # Linux installer
│   └── install.bat            # Windows installer
├── src/
│   ├── core/
│   │   ├── main.py            # Main entry point
│   │   ├── config.py          # Configuration system
│   │   ├── supervisor.py      # Agent supervisor
│   │   └── updater.py         # Update system
│   ├── ai/
│   │   ├── deepseek.py        # DeepSeek API handler
│   │   └── llama.py           # Llama local handler
│   ├── agents/
│   │   ├── chat.py            # Chat agent
│   │   └── aggressive.py      # Aggressive methods agent
│   ├── gateway/
│   │   └── communication.py   # WhatsApp/Telegram gateway
│   └── ui/
│       ├── server.py          # FastAPI server
│       ├── templates/         # HTML templates
│       └── static/            # CSS/JS files
└── docs/                      # Documentation
```

## Development

### Prerequisites
- Python 3.8+
- Node.js 14+ (for some features)
- Git
- OpenClaw (for skill installation)

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/nicky686-22/SwarmIA.git
cd SwarmIA

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m src.core.main --dev
```

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_chat_agent.py -v
```

## Troubleshooting

### Common Issues

1. **Port 3000 already in use**
   ```bash
   # Change port in config
   swarmia config set server.port 3001
   ```

2. **Dashboard not accessible**
   ```bash
   # Check firewall
   sudo ufw allow 3000/tcp
   # or
   sudo firewall-cmd --add-port=3000/tcp --permanent
   ```

3. **AI not responding**
   ```bash
   # Check AI configuration
   swarmia config show ai
   # Test connection
   swarmia test ai
   ```

4. **Update failed**
   ```bash
   # Restore from backup
   swarmia restore latest
   # Manual update
   cd /opt/swarmia
   git pull origin main
   ```

### Logs Location
- Main logs: `/opt/swarmia/logs/swarmia.log`
- Supervisor logs: `/opt/swarmia/logs/supervisor.log`
- Agent logs: `/opt/swarmia/logs/agent_*.log`
- Update logs: `/opt/swarmia/logs/updater.log`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- GitHub Issues: https://github.com/nicky686-22/SwarmIA/issues
- Documentation: https://github.com/nicky686-22/SwarmIA/docs
- OpenClaw Discord: https://discord.gg/clawd

## Changelog

### v1.0.0 (2026-03-22)
- Initial release
- Complete SwarmIA system
- Dual AI support (DeepSeek + Llama)
- WhatsApp/Telegram integration
- Elegant dashboard
- Auto-update system
- Aggressive methods for system access
- OpenClaw skill integration