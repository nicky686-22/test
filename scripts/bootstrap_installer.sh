#!/bin/bash
# Bootstrap installer for SwarmIA
# Downloads the full interactive installer and runs it

set -e

echo "🚀 SwarmIA Bootstrap Installer"
echo "==============================="
echo ""

# Download the full installer
echo "📥 Downloading SwarmIA installer..."
curl -sSL https://raw.githubusercontent.com/nicky686-22/test/main/scripts/full_installer.sh -o /tmp/swarmia_full_installer.sh

# Make it executable
chmod +x /tmp/swarmia_full_installer.sh

echo "✅ Installer downloaded"
echo ""
echo "🔧 Running interactive installer..."
echo ""

# Run the installer
sudo /tmp/swarmia_full_installer.sh
