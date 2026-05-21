# Suricata Installation & Configuration Guide

This document describes how to install and configure Suricata IDS on CTF game machines to work with the Tulip flow analyzer.

## Overview

**Suricata** is an Intrusion Detection System (IDS) that analyzes network traffic and generates alerts based on predefined rules. In our CTF setup:

1. **Suricata runs on each game machine** (e.g., DocClassifier, Gitspace, Secrets, etc.).
2. **Logs (eve.json + PCAPs) are shipped to the Tulip server** on the Custom Machine.
3. **Tulip ingests these logs** and displays alerts with tags in its UI.

## Network Context (OCF26)

| Interface | IP Range | Purpose |
|-----------|----------|---------|
| `eth0` | `10.10.[team].X` | **GAMENET** - Attack traffic (Suricata listens here) |
| `eth1` | `172.28.0.X` | Internal team network |

> [!IMPORTANT]
> `eth0` is **DOWN by default**. You must run `GAMENET_UP` on each machine before Suricata can capture traffic!

## Quick Start

### 1. Copy Script to Machine
```bash
scp install_suricata.sh root@172.28.0.10X:~/
```

### 2. Run the Script
```bash
ssh root@172.28.0.10X
chmod +x install_suricata.sh
./install_suricata.sh <TULIP_IP>
```
Replace `<TULIP_IP>` with the IP of your Custom Machine running Tulip (e.g., `172.28.0.200`).

### 3. Enable GAMENET
```bash
GAMENET_UP
```

### 4. Authorize SSH for Log Shipping
On the **game machine**:
```bash
cat /root/.ssh/id_rsa.pub
```

On the **Tulip server** (Custom Machine):
```bash
echo "PASTE_KEY_HERE" >> /root/.ssh/authorized_keys
mkdir -p /opt/tulip_data/incoming/<HOSTNAME>
```

## Configuration Details

### Suricata Rules

The script creates `/etc/suricata/rules/ctf_attacks.rules` with common attack signatures:

| Tag | Description |
|-----|-------------|
| `path_traversal` | `../` or `..\` in URI |
| `sqli` | SQL Injection patterns |
| `cmdi` | Command Injection (`;`, `|`) |
| `xss` | `<script>` tags |
| `lfi` | `/etc/passwd`, `/proc/self` |
| `backdoor` | Connections to ports 4444, 9999, 1337 |

**Adding Custom Rules:**
```bash
# Edit the rules file
nano /etc/suricata/rules/ctf_attacks.rules

# Restart Suricata to apply
systemctl restart suricata
```

### Eve.json Configuration

Suricata outputs alerts to `/var/log/suricata/eve.json`. Tulip reads this file to display alerts. The recommended config section (already applied):

```yaml
- eve-log:
    enabled: yes
    filename: eve.json
    types:
      - alert:
          metadata: yes
          tagged-packets: yes
```

### TCPdump Settings

The script starts `tcpdump` with these parameters:

| Flag | Value | Meaning |
|------|-------|---------|
| `-i` | `eth0` | Listen on GAMENET interface |
| `-G` | `60` | Rotate file every 60 seconds |
| `-W` | `20` | Keep max 20 files (~20 min history) |
| `not port 22` | - | Exclude SSH (management) traffic |

PCAPs are saved to `/var/log/pcaps/`.

## Troubleshooting

### Suricata Not Starting?
```bash
# Check if eth0 is up
ip addr show eth0

# If DOWN, run:
GAMENET_UP

# Then restart Suricata:
systemctl restart suricata
```

### No Logs on Tulip?
```bash
# Test rsync manually
/usr/local/bin/ship_to_tulip.sh

# Check cron log
tail -f /var/log/ship_to_tulip.log
```

### Disk Filling Up?
```bash
# Clean old PCAPs
rm /var/log/pcaps/*.pcap

# Clean eve.json
echo "" > /var/log/suricata/eve.json
```
