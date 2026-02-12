# PacketQTH Docker Guide

Complete guide for running PacketQTH in Docker containers.

## Overview

PacketQTH can be deployed using Docker for:
- Isolation and security
- Easy updates
- Consistent environment
- Production deployment

**Important:** TOTP setup must be done on the host machine BEFORE running the container.

## Quick Start

**Docker-Only (No Host Dependencies):**
```bash
# 1. Setup TOTP using Docker
./tools/docker-setup.sh YOUR_CALLSIGN

# Scan QR code displayed in terminal with your phone

# 2. Configure
cp config.yaml.example config.yaml
cp users.yaml.example users.yaml
nano users.yaml  # Add TOTP secret from step 1
nano config.yaml # Set HomeAssistant URL

# 3. Run container
docker-compose up -d
```

**Alternative (Python Only, No Packages):**
```bash
# 1. Generate TOTP secret (no dependencies!)
python3 tools/generate_secret.py YOUR_CALLSIGN

# Manually enter secret in authenticator app

# 2-3. Same as above
```

## TOTP Setup for Docker

### Three Methods (Choose One)

**Method 1: Docker-Only Setup** (Recommended - no host dependencies!)
**Method 2: Simple Python Script** (minimal dependencies)
**Method 3: Full Setup Tool** (requires Python + packages on host)

Choose based on what you have available:
- Have Docker? → Use Method 1
- Have Python but no packages? → Use Method 2
- Have Python + packages? → Use Method 3

### Method 1: Docker-Only Setup (Recommended) 🐳

**Best for:** Pure Docker deployments, no host dependencies needed!

This method runs the setup tool in a temporary container with QR code support.

**With Terminal QR Code:**
```bash
# Display QR code in terminal (scan with phone)
./tools/docker-setup.sh KN4XYZ

# The script will:
# 1. Build a temporary setup container
# 2. Generate TOTP secret
# 3. Display ASCII QR code in your terminal
# 4. Show the secret for users.yaml
```

**With QR Code File:**
```bash
# Save QR code as PNG file
./tools/docker-setup.sh KN4XYZ qr.png

# Opens qr.png in current directory
# Scan with your phone's camera or authenticator app
```

**What it does:**
- Builds temporary `packetqth-setup` image with tools
- Runs setup_totp.py inside container
- Mounts current directory for file output
- No host dependencies except Docker!

### Method 2: Simple Python Script (No Packages) 🐍

**Best for:** Minimal Python installation, no packages

This uses only Python standard library (no pip install needed).

```bash
# Generate secret with Python (no packages needed!)
python3 tools/generate_secret.py KN4XYZ

# Output:
# ======================================================================
# TOTP Setup for KN4XYZ
# ======================================================================
#
# Generated TOTP Secret:
#   JBSWY3DPEHPK3PXP
#
# Manual Entry Instructions:
#   1. Open your authenticator app
#   2. Tap '+' or 'Add account'
#   3. Choose 'Enter a setup key' or 'Manual entry'
#   4. Enter these details:
#      Account name: PacketQTH - KN4XYZ
#      Key: JBSWY3DPEHPK3PXP
#      Time-based: Yes
#
# Add to users.yaml:
#   users:
#     KN4XYZ: "JBSWY3DPEHPK3PXP"
```

Then manually enter the secret in your authenticator app (no QR code scanning).

### Method 3: Full Setup Tool (With Host Packages) 📱

**Best for:** If you already have Python + packages installed

This is the original method requiring host dependencies.

#### Method 1: Terminal QR Code (Recommended)

Best for Docker deployments - no file access needed!

```bash
# Install tools on host
pip3 install -r requirements-tools.txt

# Generate TOTP secret with terminal QR code
python3 tools/setup_totp.py KN4XYZ

# Output:
# ========================================
# TOTP Setup for KN4XYZ
# ========================================
#
# Secret: JBSWY3DPEHPK3PXP
#
# QR Code (scan with authenticator app):
#
# [ASCII QR code displays here]
#
# Add to users.yaml:
# users:
#   KN4XYZ: "JBSWY3DPEHPK3PXP"
```

**Scan the ASCII QR code with your phone's authenticator app!**

#### Method 2: Image File with Volume Mount

If you prefer PNG QR codes:

```bash
# Generate QR code to file
python3 tools/setup_totp.py KN4XYZ --qr-file ./qr_codes/kn4xyz.png

# QR code saved to ./qr_codes/kn4xyz.png
# Open the file and scan with your phone
```

#### Method 3: Manual Entry (No QR Package)

If you don't want to install qrcode package:

```bash
# Generate without QR code
python3 tools/setup_totp.py KN4XYZ

# Output shows:
# Secret: JBSWY3DPEHPK3PXP
# Manual setup URI: otpauth://totp/KN4XYZ?secret=JBSWY3DPEHPK3PXP&issuer=PacketQTH

# Manually enter the secret into your authenticator app:
# 1. Open Google Authenticator
# 2. Tap "+" to add account
# 3. Choose "Enter a setup key"
# 4. Account name: PacketQTH - KN4XYZ
# 5. Key: JBSWY3DPEHPK3PXP
# 6. Time-based: Yes
```

### Add to Configuration

After generating TOTP secrets:

```bash
# Edit users.yaml on host
nano users.yaml

# Add your users:
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
  W1ABC: "HXDMVJECJJWSRB3H"
```

## Docker Compose Setup

### 1. Directory Structure

```
packetqth/
├── config.yaml          # Your configuration (host)
├── users.yaml           # Your TOTP secrets (host)
├── docker-compose.yml   # Container definition
├── Dockerfile           # Image build
└── ... other files
```

### 2. Configuration Files

**config.yaml** (on host):
```yaml
homeassistant:
  url: http://homeassistant.local:8123
  # Token via environment variable (recommended)

telnet:
  host: 0.0.0.0
  port: 8023
  bpq_mode: true

# ... rest of config
```

**users.yaml** (on host):
```yaml
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
```

**.env** (on host):
```bash
HA_TOKEN=your_long_lived_access_token_here
```

### 3. Docker Compose

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  packetqth:
    build: .
    container_name: packetqth
    restart: unless-stopped

    # Mount config from host
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./users.yaml:/app/users.yaml:ro
      - ./logs:/app/logs

    # Port mapping
    ports:
      - "8023:8023"

    # Environment variables
    environment:
      - HA_TOKEN=${HA_TOKEN}

    # Security
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
```

### 4. Run Container

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop
docker-compose down
```

## Volume Mounts Explained

The container mounts files from your host:

```yaml
volumes:
  # Config (read-only)
  - ./config.yaml:/app/config.yaml:ro
  - ./users.yaml:/app/users.yaml:ro

  # Logs (read-write)
  - ./logs:/app/logs
```

**Why:**
- Config files live on host (easy to edit)
- Logs accessible from host
- No need to rebuild container for config changes
- TOTP secrets never inside container image

## Complete Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth

# 2. Generate TOTP secrets on HOST
pip3 install -r requirements-tools.txt
python3 tools/setup_totp.py YOUR_CALLSIGN

# Scan QR code with phone

# 3. Create config files on HOST
cp config.yaml.example config.yaml
cp users.yaml.example users.yaml
nano config.yaml  # Edit settings
nano users.yaml   # Add TOTP secret from step 2

# 4. Set environment variables on HOST
echo "HA_TOKEN=your_token_here" > .env

# 5. Build and run container
docker-compose up -d

# 6. Verify
docker-compose logs -f
# Should see: "PacketQTH started successfully"
```

### Adding New Users

```bash
# 1. Generate TOTP on HOST (not in container!)
python3 tools/setup_totp.py W1ABC

# 2. Scan QR code

# 3. Update users.yaml on HOST
nano users.yaml
# Add: W1ABC: "HXDMVJECJJWSRB3H"

# 4. Restart container
docker-compose restart

# Done! New user can connect
```

### Updating Configuration

```bash
# 1. Edit config on HOST
nano config.yaml

# 2. Restart container
docker-compose restart

# Changes applied immediately
```

## Troubleshooting

### QR Code Not Displaying

**Problem:** Running setup_totp.py inside container doesn't show QR code

**Solution:** Run on HOST machine, not in container
```bash
# ❌ Wrong
docker-compose exec packetqth python tools/setup_totp.py KN4XYZ

# ✅ Correct
python3 tools/setup_totp.py KN4XYZ
```

### Can't Access QR Code File

**Problem:** Generated qr.png but can't find it

**Solution:** Check your current directory on host
```bash
# File is saved to current directory
ls -la *.png

# Or specify full path
python3 tools/setup_totp.py KN4XYZ --qr-file ~/qr_codes/kn4xyz.png
```

### Permission Denied on Config Files

**Problem:** Container can't read config files

**Solution:** Check file permissions
```bash
# Make readable
chmod 644 config.yaml users.yaml

# Check permissions
ls -l config.yaml users.yaml
# Should show: -rw-r--r--
```

### Container Can't Connect to HomeAssistant

**Problem:** `homeassistant.local` doesn't resolve inside container

**Solution 1:** Use IP address in config.yaml
```yaml
homeassistant:
  url: http://192.168.1.100:8123
```

**Solution 2:** Use Docker host networking
```yaml
# docker-compose.yml
services:
  packetqth:
    network_mode: "host"
```

### TOTP Codes Not Working

**Problem:** Generated TOTP but codes fail

**Solution:** Check time sync
```bash
# On host
date

# On authenticator app
# Make sure phone time is set to automatic

# Clock drift tolerance is ±90 seconds
```

## Security Considerations

### Container Security

The Dockerfile implements security best practices:

```dockerfile
# Non-root user
USER packetqth:packetqth

# Minimal base image
FROM python:3.11-slim

# Only runtime dependencies
RUN pip install --no-cache-dir -r requirements.txt
```

Docker Compose adds more:
```yaml
# Run as specific user
user: "1000:1000"

# Read-only root filesystem
read_only: true

# Drop all capabilities
cap_drop:
  - ALL
```

### Secrets Management

**DO:**
- ✅ Store HA_TOKEN in `.env` file (not committed to git)
- ✅ Keep TOTP secrets in `users.yaml` (not in Dockerfile)
- ✅ Use environment variables for sensitive data
- ✅ Mount config files read-only

**DON'T:**
- ❌ Hard-code tokens in Dockerfile
- ❌ Commit .env to git
- ❌ Store secrets in container image
- ❌ Share TOTP secrets over insecure channels

### File Permissions

```bash
# Config files: owner read/write, others read
chmod 644 config.yaml users.yaml

# Env file: owner read/write only
chmod 600 .env

# Verify
ls -l
# -rw------- .env
# -rw-r--r-- config.yaml
# -rw-r--r-- users.yaml
```

## Advanced Usage

### Multi-Stage Build

Optimize image size:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
# Result: smaller image
```

### Health Check

Add to docker-compose.yml:

```yaml
services:
  packetqth:
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "8023"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Auto-Restart

Container automatically restarts on failure:

```yaml
services:
  packetqth:
    restart: unless-stopped
```

### Log Management

Rotate logs:

```yaml
services:
  packetqth:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Common Patterns

### Development vs Production

**Development:**
```bash
# Edit code on host
# Auto-reload with volume mount
docker-compose -f docker-compose.dev.yml up
```

**Production:**
```bash
# Build specific version
docker build -t packetqth:v1.0.0 .

# Run with restart policy
docker-compose up -d
```

### Backup Configuration

```bash
# Backup config and secrets
tar czf packetqth-backup-$(date +%Y%m%d).tar.gz \
  config.yaml users.yaml .env

# Restore
tar xzf packetqth-backup-20260210.tar.gz
```

### Update Container

```bash
# Pull latest code
git pull

# Rebuild image
docker-compose build

# Restart with new image
docker-compose up -d

# Clean old images
docker image prune
```

## Summary

**Key Points:**
1. ✅ **Always** run TOTP setup on HOST (not in container)
2. ✅ Use terminal QR codes (no file access needed)
3. ✅ Mount config files from host
4. ✅ Store secrets in .env (not in Dockerfile)
5. ✅ Run container as non-root user

**Setup Order:**
1. Generate TOTP → 2. Scan QR → 3. Edit config → 4. Run container

**When to Rebuild:**
- Code changes
- Dependency updates
- Dockerfile changes

**When to Restart:**
- Config changes
- User changes
- After updates

---

**73!** 📡 Secure containerized packet radio home automation!
