#!/bin/bash

SERVICE_NAME="tcpdump-capture.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

echo "Creating systemd service at $SERVICE_PATH..."

sudo bash -c "cat > $SERVICE_PATH" << 'EOF'
[Unit]
Description=TCPDump Packet Capture Service
After=network.target

[Service]
ExecStart=/usr/bin/tcpdump -i eth0 -w /var/log/pcaps/capture-%Y-%m-%d_%H-%M-%S.pcap -G 3600 -C 100 -Z root
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Creating pcap directory if missing..."
sudo mkdir -p /var/log/pcaps
sudo chmod 755 /var/log/pcaps

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling service to start at boot..."
sudo systemctl enable $SERVICE_NAME

echo "Starting service now..."
sudo systemctl start $SERVICE_NAME

echo "Done. Check status with: systemctl status $SERVICE_NAME"
