#!/bin/bash
# =============================================================================
# install_suricata.sh
# =============================================================================
# Description:
#   This script installs and configures Suricata IDS on a CTF game machine.
#   It is designed to work with the Tulip flow analyzer for centralized
#   traffic analysis.
#
# What this script does:
#   1. Installs Suricata and dependencies (tcpdump, rsync, jq).
#   2. Configures Suricata to output alerts to eve.json (for Tulip).
#   3. Sets up a rotating tcpdump capture on the GAMENET interface (eth0).
#   4. Configures an rsync cron job to ship logs to the Tulip server.
#   5. Creates basic detection rules for common CTF attacks.
#
# Network Context (OCF26 CyberLegion):
#   - Internal IP: 172.28.0.X (eth1) - Team's internal network.
#   - External IP: 10.10.[team].X (eth0) - GAMENET, where attacks occur.
#   - Suricata MUST listen on eth0 to capture attack traffic.
#   - GAMENET_UP must be executed before eth0 is active.
#
# Usage:
#   sudo ./install_suricata.sh <TULIP_SERVER_IP>
#
# Example:
#   sudo ./install_suricata.sh 172.28.0.200
#
# Dependencies:
#   - Debian/Ubuntu based OS.
#   - SSH key must be configured on the Tulip server for rsync.
#
# Author: Auto-generated for CyberLegion CTF
# =============================================================================

set -e

TULIP_IP="$1"
SURICATA_LOG_DIR="/var/log/suricata"
PCAP_DIR="/var/log/pcaps"
RULES_DIR="/etc/suricata/rules"
MY_HOSTNAME=$(hostname)
MY_IP=$(hostname -I | awk '{print $1}')

# --- Input Validation ---
if [ -z "$TULIP_IP" ]; then
    echo "[!] ERROR: No Tulip Server IP provided."
    echo "Usage: sudo ./install_suricata.sh <TULIP_IP>"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root" 
   exit 1
fi

echo "=============================================="
echo "[+] Suricata Installation for CTF"
echo "    Target Machine: $MY_HOSTNAME ($MY_IP)"
echo "    Tulip Server:   $TULIP_IP"
echo "=============================================="

# =============================================================================
# 1. INSTALL PACKAGES
# =============================================================================
echo "[-] Installing Suricata, tcpdump, rsync, jq..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y suricata tcpdump rsync jq

# =============================================================================
# 2. CONFIGURE SURICATA
# =============================================================================
echo "[-] Configuring Suricata..."

# Stop Suricata before modifying config
systemctl stop suricata 2>/dev/null || true

# Backup original config
cp /etc/suricata/suricata.yaml /etc/suricata/suricata.yaml.bak

# Ensure rules directory exists
mkdir -p "$RULES_DIR"

# --- Copy OCF26 Rules ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
RULES_FILE="ocf26_rules.rules"

if [ -f "$SCRIPT_DIR/$RULES_FILE" ]; then
    echo "[-] Copying $RULES_FILE to $RULES_DIR..."
    cp "$SCRIPT_DIR/$RULES_FILE" "$RULES_DIR/$RULES_FILE"
else
    echo "[!] WARNING: $RULES_FILE not found in $SCRIPT_DIR!"
    echo "    Using empty rules file. Please copy rules manually."
    touch "$RULES_DIR/$RULES_FILE"
fi

# Add our rules file to suricata.yaml if not already present
# tu jest blad - nie mozna w ten sposob dodac
if ! grep -q "$RULES_FILE" /etc/suricata/suricata.yaml; then
    # Append to rule-files section (simple approach)
    # poprawic echo "  - /etc/suricata/rules/$RULES_FILE" >> /etc/suricata/suricata.yaml
fi

# Enable and start Suricata on eth0 (GAMENET interface)
# Note: eth0 might be down initially. Suricata will start listening when GAMENET_UP is executed.
sed -i 's/af-packet:.*/af-packet:\n  - interface: eth0/' /etc/suricata/suricata.yaml 2>/dev/null || true
systemctl enable suricata
systemctl start suricata || echo "[!] Suricata may fail to start if eth0 is down. Run GAMENET_UP first."

# =============================================================================
# 3. CONFIGURE TCPDUMP (Rotating Capture)
# =============================================================================
echo "[-] Setting up TCPdump for rotating PCAP capture..."
mkdir -p "$PCAP_DIR"

# Kill any existing tcpdump
pkill tcpdump 2>/dev/null || true

# Start tcpdump on eth0:
# -G 60: Rotate every 60 seconds
# -W 20: Keep 20 files max (~20 minutes of history)
# not port 22: Exclude SSH traffic (our management)
nohup tcpdump -i eth0 -G 60 -W 20 -Z root -w "$PCAP_DIR/capture_%Y%m%d_%H%M%S.pcap" not port 22 > /dev/null 2>&1 &
echo "[+] TCPdump started (PID: $!)."

# =============================================================================
# 4. CONFIGURE LOG SHIPPING TO TULIP
# =============================================================================
echo "[-] Configuring log shipping to Tulip ($TULIP_IP)..."

REMOTE_USER="debian"
REMOTE_PATH="/opt/tulip_data/incoming/$MY_HOSTNAME"

# Create shipping script
cat <<EOF > /usr/local/bin/ship_to_tulip.sh
#!/bin/bash
# Ship Suricata eve.json and PCAPs to Tulip Server

# Sync Eve JSON (Suricata Alerts)
rsync -avz --timeout=10  --chmod=775 -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5" \\
    $SURICATA_LOG_DIR/eve.json \\
    $REMOTE_USER@$TULIP_IP:$REMOTE_PATH/ 2>/dev/null || true

# Sync PCAPs (completed files only)
rsync -avz --timeout=10  --chmod=775 -e "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5" \\
    --include='*.pcap' --exclude='*' \\
    $PCAP_DIR/ \\
    $REMOTE_USER@$TULIP_IP:$REMOTE_PATH/ 2>/dev/null || true
EOF

chmod +x /usr/local/bin/ship_to_tulip.sh

# Add cron job (run every minute)
if ! crontab -l 2>/dev/null | grep -q "ship_to_tulip.sh"; then
    (crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/ship_to_tulip.sh >> /var/log/ship_to_tulip.log 2>&1") | crontab -
    echo "[+] Cron job added for log shipping."
else
    echo "[.] Cron job already exists."
fi

# =============================================================================
# 5. SUMMARY
# =============================================================================
echo ""
echo "=============================================="
echo "[+] Suricata Installation Complete!"
echo "=============================================="
echo ""
echo "IMPORTANT NEXT STEPS:"
echo "  1. Ensure eth0 is UP: Run 'GAMENET_UP' on this machine."
echo "  2. Add this machine's SSH key to the Tulip server:"
echo "     On this machine: cat /root/.ssh/id_rsa.pub"
echo "     On Tulip server: echo '<KEY>' >> /root/.ssh/authorized_keys"
echo ""
echo "Logs:"
echo "  - Suricata Alerts: $SURICATA_LOG_DIR/eve.json"
echo "  - PCAP Files:      $PCAP_DIR/"
echo "  - Shipping Log:    /var/log/ship_to_tulip.log"
echo ""
echo "Rules File: $RULES_DIR/$RULES_FILE"
echo "  (Edit to add custom attack signatures.)"
echo ""
