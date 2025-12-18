# 🚀 MoMo-Nexus Deployment Guide

> **Version:** 0.1.0 | **Last Updated:** 2025-12-18

---

## 📋 Overview

This document provides step-by-step instructions for deploying MoMo-Nexus in various configurations.

---

## 🎯 Deployment Options

| Option | Use Case | Complexity |
|--------|----------|------------|
| **Local Dev** | Development, testing | Easy |
| **Single Node** | Small deployment | Medium |
| **High Availability** | Production | Advanced |
| **Field Kit** | Portable, outdoor | Medium |

---

## 💻 Local Development

### Prerequisites

```bash
# Python 3.10+
python3 --version

# pip
pip3 --version

# git
git --version
```

### Installation

```bash
# Clone repository
git clone https://github.com/Momo-Master/MoMo-Nexus.git
cd MoMo-Nexus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Configuration

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit configuration
nano config.yaml
```

```yaml
# config.yaml
server:
  host: 0.0.0.0
  port: 8080
  debug: true

database:
  path: ./data/nexus.db

channels:
  lora:
    enabled: false  # No hardware in dev
    mock: true
  
  wifi:
    enabled: true
    interface: wlan0
  
  cellular:
    enabled: false
    mock: true

fleet:
  heartbeat_interval: 30
  timeout: 300

logging:
  level: DEBUG
  file: ./logs/nexus.log
```

### Run

```bash
# Start Nexus
python -m nexus

# Or with uvicorn (for development)
uvicorn nexus.api:app --reload --port 8080

# Run tests
pytest tests/ -v
```

### Access

```
Web Dashboard: http://localhost:8080
API Docs:      http://localhost:8080/docs
WebSocket:     ws://localhost:8080/ws
```

---

## 🖥️ Single Node Deployment

### System Requirements

```
Hardware:
• Raspberry Pi 4 (4GB+) or x86 server
• 32GB+ storage
• Internet connection
• Optional: LoRa, 4G hardware

Software:
• Raspberry Pi OS Lite (64-bit)
• or Debian 11+ / Ubuntu 22.04+
```

### Automated Installation

```bash
# Download and run installer
curl -sSL https://raw.githubusercontent.com/Momo-Master/MoMo-Nexus/main/install.sh | bash

# Or step by step:
wget https://raw.githubusercontent.com/Momo-Master/MoMo-Nexus/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### Manual Installation

#### Step 1: System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    python3 python3-pip python3-venv \
    git sqlite3 \
    hostapd dnsmasq \
    screen tmux

# Create nexus user
sudo useradd -m -s /bin/bash nexus
sudo usermod -aG dialout,gpio,bluetooth nexus
```

#### Step 2: Install Nexus

```bash
# Switch to nexus user
sudo su - nexus

# Clone repository
git clone https://github.com/Momo-Master/MoMo-Nexus.git
cd MoMo-Nexus

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install
pip install -r requirements.txt
```

#### Step 3: Configure

```bash
# Copy production config
cp config.production.yaml config.yaml

# Edit for your environment
nano config.yaml
```

```yaml
# config.yaml (production)
server:
  host: 0.0.0.0
  port: 8080
  debug: false

database:
  path: /data/nexus/nexus.db

channels:
  lora:
    enabled: true
    port: /dev/ttyUSB0
    baudrate: 115200
  
  wifi:
    enabled: true
    interface: wlan0
    mode: ap  # or client
    ssid: NexusAP
    password: ChangeMe123!
  
  cellular:
    enabled: true
    port: /dev/ttyUSB1
    apn: internet

security:
  jwt_secret: <generate-random-string>
  api_keys:
    - name: operator
      key: <generate-api-key>

logging:
  level: INFO
  file: /var/log/nexus/nexus.log
  max_size: 10MB
  backups: 5
```

#### Step 4: Create Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/nexus.service
```

```ini
[Unit]
Description=MoMo-Nexus Communication Hub
After=network.target

[Service]
Type=simple
User=nexus
WorkingDirectory=/home/nexus/MoMo-Nexus
Environment=PATH=/home/nexus/MoMo-Nexus/venv/bin
ExecStart=/home/nexus/MoMo-Nexus/venv/bin/python -m nexus
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable nexus
sudo systemctl start nexus

# Check status
sudo systemctl status nexus
```

#### Step 5: Configure Firewall

```bash
# UFW
sudo ufw allow 8080/tcp  # Web UI
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

---

## 📱 Field Kit Deployment

### Overview

Portable, battery-powered Nexus for field operations.

```
┌─────────────────────────────────────────────────────────────────┐
│                    FIELD KIT COMPONENTS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │ Raspberry   │  │ LoRa        │  │ 4G Modem    │            │
│   │ Pi 4        │  │ T-Beam      │  │ + Antenna   │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │ Power Bank  │  │ Solar Panel │  │ Pelican     │            │
│   │ 20000mAh    │  │ (optional)  │  │ Case        │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
│   Runtime: ~8-12 hours on battery                               │
│            Indefinite with solar                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Optimizations

```yaml
# config.yaml (field)
server:
  port: 8080
  debug: false

power_saving:
  enabled: true
  wifi_power_save: true
  cpu_governor: powersave
  screen_off: true

channels:
  lora:
    enabled: true
    duty_cycle: 1  # EU legal limit
  
  cellular:
    enabled: true
    low_power: true
    
logging:
  level: WARNING  # Reduce disk writes
```

### Quick Deploy Script

```bash
#!/bin/bash
# field-deploy.sh

echo "🚀 Starting Nexus Field Deployment..."

# Check battery
BATTERY=$(cat /sys/class/power_supply/BAT0/capacity 2>/dev/null || echo "N/A")
echo "🔋 Battery: $BATTERY%"

# Start services
sudo systemctl start nexus

# Enable WiFi AP for tablet access
sudo nmcli device wifi hotspot ssid NexusField password Field123!

# Get IP
IP=$(hostname -I | awk '{print $1}')
echo "📡 Access: http://$IP:8080"
echo "📱 WiFi: NexusField / Field123!"

# Show QR code (if qrencode installed)
qrencode -t ANSIUTF8 "WIFI:S:NexusField;T:WPA;P:Field123!;;"

echo "✅ Nexus is ready!"
```

---

## 🔒 Security Hardening

### Basic Security

```bash
# Change default passwords
passwd

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# SSH key only
ssh-copy-id user@nexus
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Install fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
```

### HTTPS Setup

```bash
# Using Caddy (auto HTTPS)
sudo apt install -y caddy

# Create Caddyfile
sudo nano /etc/caddy/Caddyfile
```

```
nexus.example.com {
    reverse_proxy localhost:8080
}
```

```bash
# Start Caddy
sudo systemctl restart caddy
```

### API Key Authentication

```yaml
# config.yaml
security:
  require_auth: true
  jwt_secret: <random-256-bit-string>
  api_keys:
    - name: operator1
      key: nxk_xxxxxxxxxxxxxxxxxxxx
      permissions: [read, write, admin]
    - name: readonly
      key: nxk_yyyyyyyyyyyyyyyyyyyy
      permissions: [read]
```

---

## 📊 Monitoring

### Health Checks

```bash
# Check service status
sudo systemctl status nexus

# Check logs
sudo journalctl -u nexus -f

# Check API health
curl http://localhost:8080/api/health
```

### Prometheus Metrics

```yaml
# config.yaml
metrics:
  enabled: true
  port: 9090
```

Access: `http://nexus:9090/metrics`

### Log Rotation

```bash
# /etc/logrotate.d/nexus
/var/log/nexus/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 nexus nexus
}
```

---

## 🔄 Backup & Recovery

### Backup Script

```bash
#!/bin/bash
# backup-nexus.sh

BACKUP_DIR="/backup/nexus"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
sqlite3 /data/nexus/nexus.db ".backup '$BACKUP_DIR/nexus_$DATE.db'"

# Backup config
cp /home/nexus/MoMo-Nexus/config.yaml $BACKUP_DIR/config_$DATE.yaml

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.yaml" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
```

### Restore

```bash
# Stop service
sudo systemctl stop nexus

# Restore database
cp /backup/nexus/nexus_YYYYMMDD.db /data/nexus/nexus.db

# Restore config
cp /backup/nexus/config_YYYYMMDD.yaml /home/nexus/MoMo-Nexus/config.yaml

# Start service
sudo systemctl start nexus
```

---

## 🐛 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Service won't start | Config error | Check `journalctl -u nexus` |
| No LoRa connection | Wrong port | Check `ls /dev/ttyUSB*` |
| 4G not connecting | APN wrong | Verify APN in config |
| Web UI not loading | Firewall | Check `sudo ufw status` |
| High CPU usage | Logging | Reduce log level |

### Debug Mode

```bash
# Run in foreground with debug
cd /home/nexus/MoMo-Nexus
source venv/bin/activate
NEXUS_DEBUG=1 python -m nexus
```

### Check Ports

```bash
# LoRa
sudo screen /dev/ttyUSB0 115200
# Type commands, Ctrl+A then K to exit

# 4G
sudo screen /dev/ttyUSB1 115200
AT
OK
AT+CSQ
+CSQ: 20,0
```

---

## ✅ Deployment Checklist

```
Pre-Deployment:
□ Hardware assembled and tested
□ SD card flashed
□ Config file customized
□ Security hardened

Deployment:
□ Service installed and enabled
□ Firewall configured
□ HTTPS enabled (if public)
□ Monitoring configured

Post-Deployment:
□ All channels tested
□ API accessible
□ Backup scheduled
□ Documentation updated
```

---

*MoMo-Nexus Deployment Guide v0.1.0*

