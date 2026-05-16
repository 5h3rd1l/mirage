#!/bin/bash
# ── Mirage VPN Server Deployment Script ──
# Run this on the EC2 instance (13.63.54.237)
# Usage: bash deploy_server.sh

set -e

echo "============================================"
echo "  Mirage VPN Server — Deploy"
echo "============================================"

# Kill any existing server processes
echo "[*] Stopping existing servers..."
sudo fuser -k 5000/tcp 2>/dev/null || true
sudo fuser -k 5001/udp 2>/dev/null || true
sleep 1

# Create vpn-server directory
mkdir -p ~/vpn-server

# Copy the server script (assumes tun_server.py is in the same dir as this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/tun_server.py" ]; then
    cp "$SCRIPT_DIR/tun_server.py" ~/vpn-server/tun_server.py
    echo "[+] Copied tun_server.py to ~/vpn-server/"
elif [ -f ~/vpn-server/tun_server.py ]; then
    echo "[*] Using existing ~/vpn-server/tun_server.py"
else
    echo "[-] ERROR: tun_server.py not found!"
    exit 1
fi

# Install dependencies
echo "[*] Ensuring dependencies..."
pip3 install cryptography --break-system-packages 2>/dev/null || pip3 install cryptography

# Start server in a screen session
echo "[*] Starting server in screen session 'mirage'..."
screen -dmS mirage sudo python3 ~/vpn-server/tun_server.py
sleep 2

# Verify it's running
if sudo fuser 5000/tcp >/dev/null 2>&1 && sudo fuser 5001/udp >/dev/null 2>&1; then
    echo "[+] Server is running!"
    echo "    TCP auth:  port 5000"
    echo "    UDP tunnel: port 5001"
    echo ""
    echo "To view logs:   screen -r mirage"
    echo "To detach:      Ctrl+A then D"
else
    echo "[-] Server may not have started correctly."
    echo "    Check: screen -r mirage"
fi
