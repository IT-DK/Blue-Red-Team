#!/bin/bash
# =============================================================================
# install_tulip.sh
# =============================================================================
# Description:
#   This script installs and configures Tulip - a flow analyzer for CTF
#   Attack/Defence competitions. Run this on the Custom Machine only.
#
# What this script does:
#   1. Installs Docker and Docker Compose.
#   2. Clones the Tulip repository from GitHub.
#   3. Creates the data directory for incoming PCAP/eve.json files.
#   4. Configures the .env file.
#   5. Starts the Tulip Docker stack.
#
# Network Context (OCF26 CyberLegion):
#   - Custom Machine IP: 172.28.0.200 (internal) / 10.10.[team].200 (GAMENET)
#   - Tulip UI: Accessible on port 3000 (default).
#   - Incoming logs from game machines are stored in /opt/tulip_data/incoming/
#
# Usage:
#   sudo ./install_tulip.sh [TEAM_NUMBER]
#
# Example:
#   sudo ./install_tulip.sh 05
#
# Dependencies:
#   - Debian/Ubuntu based OS.
#   - Internet access to clone GitHub repo.
#
# Author: Auto-generated for CyberLegion CTF
# =============================================================================

set -e

TEAM_NUMBER="$1"
TULIP_DIR="/opt/tulip"
DATA_DIR="/opt/tulip_data"

if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root" 
   exit 1
fi

echo "=============================================="
echo "[+] Tulip Installation for CTF"
echo "    Custom Machine: $(hostname)"
echo "=============================================="

# =============================================================================
# 1. INSTALL DOCKER
# =============================================================================
echo "[-] Installing Docker & Docker Compose..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y git docker.io docker-compose-v2 curl

# Enable Docker
systemctl enable docker
systemctl start docker

# =============================================================================
# 2. PREPARE DATA DIRECTORIES
# =============================================================================
echo "[-] Creating data directories..."
mkdir -p "$DATA_DIR/incoming"
mkdir -p "$DATA_DIR/suricata/log"
mkdir -p "$DATA_DIR/suricata/lib/rules"
mkdir -p "$DATA_DIR/suricata/etc"
chmod -R 777 "$DATA_DIR"

# =============================================================================
# 3. CLONE TULIP
# =============================================================================
if [ -d "$TULIP_DIR" ]; then
    echo "[.] Tulip directory exists. Pulling latest..."
    cd "$TULIP_DIR"
    git pull
else
    echo "[-] Cloning Tulip..."
    git clone https://github.com/OpenAttackDefenseTools/tulip.git "$TULIP_DIR"
fi

cd "$TULIP_DIR"

# =============================================================================
# 4. CONFIGURE ENVIRONMENT
# =============================================================================
echo "[-] Configuring .env..."

cp .env.example .env

# Set traffic directory
sed -i "s|TRAFFIC_DIR_HOST=.*|TRAFFIC_DIR_HOST=$DATA_DIR/incoming|" .env

# Set Suricata directory (for Tulip's internal Suricata container, if used)
sed -i "s|SURICATA_DIR_HOST=.*|SURICATA_DIR_HOST=$DATA_DIR/suricata|" .env

echo "[+] .env configured:"
grep -E "TRAFFIC_DIR_HOST|SURICATA_DIR_HOST" .env

# =============================================================================
# 5. CONFIGURE SERVICES (If team number provided)
# =============================================================================
if [ -n "$TEAM_NUMBER" ]; then
    echo "[-] Configuring services for Team $TEAM_NUMBER..."
    
    VM_IP="10.10.$TEAM_NUMBER.1"
    
    # Update configurations.py with team-specific services
    cat <<EOF > services/api/configurations.py
# Auto-generated configuration for Team $TEAM_NUMBER
# Edit this file to add your services as they are discovered.

vm_ip = "$VM_IP"

# Add your services here. Example:
services = [
    {"ip": "10.10.$TEAM_NUMBER.105", "port": 80, "name": "***"},
    {"ip": "10.10.$TEAM_NUMBER.103", "port": 8443, "name": "***"},
    {"ip": "10.10.$TEAM_NUMBER.112", "port": 80, "name": "***"},
    {"ip": "10.10.$TEAM_NUMBER.107", "port": 80, "name": "***"}
]
EOF
    echo "[+] Configuration template created. Edit services/api/configurations.py to add services."
fi

# =============================================================================
# 6. START TULIP
# =============================================================================
echo "[-] Building and starting Tulip..."
docker compose up -d --build

# =============================================================================
# 7. SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "[+] Tulip Installation Complete!"
echo "=============================================="
echo ""
echo "Tulip UI: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "  1. Configure services in: $TULIP_DIR/services/api/configurations.py"
echo "     Then run: docker compose up --build -d api"
echo ""
echo "  2. Ensure game machines can rsync to this server:"
echo "     - Add their SSH public keys to: /root/.ssh/authorized_keys"
echo "     - Create directories: mkdir -p $DATA_DIR/incoming/<hostname>"
echo ""
echo "Incoming Logs Directory: $DATA_DIR/incoming/"
echo "  (Tulip uses inotify to watch for new files automatically)"
echo ""
