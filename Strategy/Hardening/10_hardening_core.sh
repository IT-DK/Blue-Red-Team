#!/bin/ba h
# 10_hardening_core.sh
# Comprehensive System Hardening & Audit Script
# Usage: sudo ./10_hardening_core.sh "YOUR_SSH_PUBLIC_KEY_STRING" [TULIP_SERVER_IP]
# Example: sudo ./10_hardening_core.sh "ssh-rsa AAAAB3..." 10.10.team.200

PUB_KEY="$1"
TULIP_IP="$2"
BACKUP_USER="sysadmin"
AUDIT_DIR="/var/log/audit_dumps"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HOSTNAME=$(hostname)
AUDIT_FILE="$AUDIT_DIR/audit_report_${HOSTNAME}_${TIMESTAMP}.txt"

if [ -z "$PUB_KEY" ]; then
    echo "[!] ERROR: No SSH Public Key provided."
    echo "Usage: sudo ./10_hardening_core.sh \"ssh-rsa ...\" [TULIP_SERVER_IP]"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root" 
   exit 1
fi

echo "[+] Starting Hardening on $HOSTNAME..."

# ==============================================================================
# 1. IAM & ACCESS CONTROL
# ==============================================================================
echo "[-] [IAM] Creating Backup User: $BACKUP_USER..."
if id "$BACKUP_USER" &>/dev/null; then
    echo "    User $BACKUP_USER already exists."
else
    useradd -m -s /bin/bash "$BACKUP_USER"
    usermod -aG sudo "$BACKUP_USER"
    # Ensure sudoers doesn't require pass for this user (optional, helps in automation)
    echo "$BACKUP_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-cloud-init-users
    echo "    User $BACKUP_USER created."
fi

echo "[-] [IAM] Setting up SSH Keys..."
mkdir -p /home/$BACKUP_USER/.ssh
echo "$PUB_KEY" >> /home/$BACKUP_USER/.ssh/authorized_keys
chown -R $BACKUP_USER:$BACKUP_USER /home/$BACKUP_USER/.ssh
chmod 700 /home/$BACKUP_USER/.ssh
chmod 600 /home/$BACKUP_USER/.ssh/authorized_keys

echo "[-] [IAM] Hardening SSH Config..."
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak_$TIMESTAMP
# Apply sed replacements
sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
# Ensure PubkeyAuth is on
sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
# Restart SSH
service ssh restart
echo "    SSH Hardened. Root Login and Password Auth DISABLED."

# ==============================================================================
# 2. AUDIT & RECONNAISSANCE
# ==============================================================================
echo "[-] [AUDIT] Generating Single Report: $AUDIT_FILE..."
mkdir -p "$AUDIT_DIR"
touch "$AUDIT_FILE"
chmod 600 "$AUDIT_FILE"

log_header() {
    echo "" >> "$AUDIT_FILE"
    echo "================================================================================" >> "$AUDIT_FILE"
    echo ">>> $1" >> "$AUDIT_FILE"
    echo "================================================================================" >> "$AUDIT_FILE"
}

log_header "SYSTEM INFO"
uname -a >> "$AUDIT_FILE"
hostname -I >> "$AUDIT_FILE"

log_header "USERS (/etc/passwd)"
cat /etc/passwd >> "$AUDIT_FILE"

log_header "GROUPS (/etc/group)"
cat /etc/group >> "$AUDIT_FILE"

log_header "SUDOERS"
cat /etc/sudoers >> "$AUDIT_FILE"
grep -r . /etc/sudoers.d/ >> "$AUDIT_FILE" 2>/dev/null

log_header "RUNNING PROCESSES (ps aux)"
ps aux >> "$AUDIT_FILE"

log_header "NETWORK LISTENERS (ss -tulnp)"
ss -tulnp >> "$AUDIT_FILE"

log_header "CRON JOBS (All Users)"
for user in $(cut -f1 -d: /etc/passwd); do
    crontab -u $user -l 2>/dev/null | grep -v "^#" | while read line; do
        if [ ! -z "$line" ]; then
            echo "USER: $user | CMD: $line" >> "$AUDIT_FILE"
        fi
    done
done
ls -la /etc/cron* >> "$AUDIT_FILE"

echo "    Audit Saved to $AUDIT_FILE"

# ==============================================================================
# 3. SYSTEM MAINTENANCE
# ==============================================================================
echo "[-] [SYSTEM] Updating Package Lists & Upgrading..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -y -q

# ==============================================================================
# 4. MONITORING SETUP (Suricata + TCPdump + Tulip Shipping)
# ==============================================================================
if [ -z "$TULIP_IP" ]; then
    echo "[!] WARNING: No Tulip Server IP provided. Skipping Log Shipping setup."
else
    echo "[-] [MONITORING] Installing Suricata, TCPdump, jq, rsync..."
    apt-get install -y suricata tcpdump jq rsync

    echo "[-] [MONITORING] Configuring Suricata..."
    systemctl stop suricata
    cp /etc/suricata/suricata.yaml /etc/suricata/suricata.yaml.bak
    systemctl enable suricata
    systemctl start suricata

    echo "[-] [MONITORING] Setting up TCPdump (Rotating)..."
    mkdir -p /var/log/pcaps
    # tcpdump ring buffer: 60s chunks, keep 10
    nohup tcpdump -i any -G 60 -W 10 -w "/var/log/pcaps/capture_%H%M%S.pcap" not port 22 > /dev/null 2>&1 &

    echo "[-] [MONITORING] Setting up Log Shipping to $TULIP_IP..."
    REMOTE_USER="root"
    REMOTE_PATH="/opt/tulip_data/incoming/$HOSTNAME"
    
    # Create Shipping Script
    cat <<EOF > /usr/local/bin/ship_logs.sh
#!/bin/bash
# Sync Eve JSON
rsync -avz --timeout=10 -e "ssh -o StrictHostKeyChecking=no" /var/log/suricata/eve.json \$REMOTE_USER@$TULIP_IP:\$REMOTE_PATH/eve.json
# Sync PCAPs
rsync -avz --timeout=10 -e "ssh -o StrictHostKeyChecking=no" /var/log/pcaps/*.pcap \$REMOTE_USER@$TULIP_IP:\$REMOTE_PATH/
EOF
    chmod +x /usr/local/bin/ship_logs.sh

    # Crontab
    if ! crontab -l | grep -q "ship_logs.sh"; then
        (crontab -l 2>/dev/null; echo "* * * * * /usr/local/bin/ship_logs.sh >> /var/log/ship_logs.log 2>&1") | crontab -
    fi
    
    echo "    Log Shipping Configured. Ensure your Public Key is on the Tulip Server!"
fi

echo "[+] Hardening Complete!"
echo "    - Verified User: $BACKUP_USER"
echo "    - SSH: Key Only, No Root"
echo "    - Audit File: $AUDIT_FILE"

