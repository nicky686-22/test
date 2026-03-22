#!/bin/bash
# SwarmIA Installation - Ultra Simple Version
# Works even when GitHub raw is cached

set -e

echo "🚀 SwarmIA Ultra Simple Installer"
echo "================================="

# Check root
if [[ $EUID -ne 0 ]]; then
    echo "⚠️  Need root: sudo bash $0"
    exit 1
fi

# Install dir
INSTALL_DIR="/opt/swarmia"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "📦 Installing dependencies..."
apt-get update
apt-get install -y python3 python3-pip git curl

echo "⬇️  Downloading SwarmIA..."
# Method 1: Direct download of essential files
mkdir -p src/core scripts

# Download core files
echo "  📥 Downloading core files..."
curl -s -L "https://api.github.com/repos/nicky686-22/SwarmIA/contents/src/core/main.py" \
  -H "Authorization: token YOUR_GITHUB_TOKEN_HERE" \
  | jq -r '.content' | base64 -d > src/core/main.py 2>/dev/null || true

curl -s -L "https://api.github.com/repos/nicky686-22/SwarmIA/contents/src/core/config.py" \
  -H "Authorization: token YOUR_GITHUB_TOKEN_HERE" \
  | jq -r '.content' | base64 -d > src/core/config.py 2>/dev/null || true

# If API fails, create minimal files
if [ ! -s "src/core/main.py" ]; then
    echo "  ⚠️  API failed, creating minimal main.py..."
    cat > src/core/main.py << 'EOF'
#!/usr/bin/env python3
"""
SwarmIA - Minimal Version
"""
import uvicorn
from fastapi import FastAPI

app = FastAPI(title="SwarmIA")

@app.get("/")
async def root():
    return {"message": "SwarmIA is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)
EOF
fi

echo "🐍 Installing Python packages..."
pip3 install fastapi uvicorn

echo "⚙️  Creating systemd service..."
cat > /etc/systemd/system/swarmia.service << 'EOF'
[Unit]
Description=SwarmIA AI System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/swarmia
ExecStart=/usr/bin/python3 /opt/swarmia/src/core/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable swarmia
systemctl start swarmia

echo "⏳ Waiting for service..."
sleep 3

if systemctl is-active --quiet swarmia; then
    echo "✅ SwarmIA is running!"
    IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "🌐 Access: http://$IP:3000"
    echo "🔧 Health: http://$IP:3000/health"
    echo ""
    echo "📊 Commands:"
    echo "  sudo systemctl status swarmia"
    echo "  sudo journalctl -u swarmia -f"
else
    echo "⚠️  Service didn't start automatically"
    echo "💡 Try: sudo systemctl start swarmia"
fi