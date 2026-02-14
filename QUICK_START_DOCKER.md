# Quick Start - Docker Only

Complete setup using only Docker (no Python installation required on host).

## Prerequisites

- Docker installed
- HomeAssistant with API access

## Setup Steps

### 1. Generate TOTP Secret

Use the pre-built tools image to generate your TOTP secret:

```bash
# Generate TOTP with terminal QR code
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN

# The tool will display:
# - Your TOTP secret (save this!)
# - ASCII QR code (scan with phone)
# - Configuration snippet
```

**Scan the QR code** with your authenticator app (Google Authenticator, Authy, etc.)

**Alternative:** Save QR code as PNG file:
```bash
docker run --rm -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png

# Open qr.png and scan with your phone
```

### 2. Clone Repository

```bash
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth
```

### 3. Create Configuration Files

**Create config.yaml:**
```bash
cp config.yaml.example config.yaml
nano config.yaml
```

Update:
- `homeassistant.url` - Your HomeAssistant URL
- Other settings as needed

**Create users.yaml:**
```bash
cp users.yaml.example users.yaml
nano users.yaml
```

Add your TOTP secret from step 1:
```yaml
users:
  YOUR_CALLSIGN: "JBSWY3DPEHPK3PXP"  # Replace with your actual secret

security:
  max_failed_attempts: 5
  lockout_duration_seconds: 300
  session_timeout_seconds: 300
```

**Create .env file:**
```bash
cp .env.example .env
nano .env
```

Add your HomeAssistant token:
```
HA_TOKEN=your_long_lived_access_token_here
```

To create a token:
1. Open HomeAssistant
2. Click your profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy the token to `.env`

### 4. Start PacketQTH

```bash
# Pull the runtime image (if not already pulled)
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Start the server
docker-compose up -d

# View logs
docker-compose logs -f
```

You should see:
```
PacketQTH started successfully
Telnet: 0.0.0.0:8023
Entities: XX
```

### 5. Test Connection

**Direct telnet test:**
```bash
telnet localhost 8023
```

You should see:
```
PacketQTH v0.1.0

YOUR_CALLSIGN
TOTP Code: 123456

Welcome YOUR_CALLSIGN!
Type H for help

>
```

Enter a TOTP code from your authenticator app.

### 6. Configure LinBPQ

Add to your `bpq32.cfg`:
```
APPLICATION 10,PACKETQTH,C 10 HOST localhost 8023
```

Restart LinBPQ, then connect:
```
C PACKETQTH
```

## Commands

Once connected:
```
L              List devices
S <id>         Show device details
ON <id>        Turn on
OFF <id>       Turn off
SET <id> <val> Set value
A              List automations
T <id>         Trigger automation
H              Help
Q              Quit
```

## Updating

```bash
# Pull latest image
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Restart
docker-compose down
docker-compose up -d
```

## Troubleshooting

### Can't connect to HomeAssistant

Check the logs:
```bash
docker-compose logs
```

Common issues:
- Wrong `HA_TOKEN` in `.env`
- Wrong URL in `config.yaml`
- HomeAssistant not accessible from container

Test HA connection:
```bash
# From host machine
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://homeassistant.local:8123/api/states
```

### TOTP codes not working

- Check phone time is set to automatic
- Clock drift tolerance is ±90 seconds
- Verify secret in `users.yaml` matches authenticator app
- Check callsign in `users.yaml` matches connection

Regenerate TOTP if needed:
```bash
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN
```

### Container won't start

Check logs:
```bash
docker-compose logs packetqth
```

Verify config files exist:
```bash
ls -l config.yaml users.yaml .env
```

### Connection refused on port 8023

Check if container is running:
```bash
docker ps | grep packetqth
```

Check port binding:
```bash
docker-compose ps
```

If bound to 127.0.0.1:8023, only local connections allowed.
To allow remote connections, edit `docker-compose.yml`:
```yaml
ports:
  - "8023:8023"  # Allow from anywhere
```

## Advanced

### Add Another User

```bash
# Generate TOTP for new user
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py W1ABC

# Add to users.yaml
nano users.yaml

# Restart
docker-compose restart
```

### Use Specific Version

```bash
# Use version 1.0.0 instead of latest
docker pull ghcr.io/ben-kuhn/packetqth:1.0.0

# Edit docker-compose.yml
image: ghcr.io/ben-kuhn/packetqth:1.0.0

# Restart
docker-compose up -d
```

### View All Commands Available in Tools Image

```bash
docker run --rm ghcr.io/ben-kuhn/packetqth-tools:latest
```

Shows available tools and usage examples.

### Run Security Audit

```bash
# Auth module audit
docker run --rm ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/security_audit.py

# Server module audit
docker run --rm ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/audit_server.py
```

## Summary

**Two images, two purposes:**

1. **Tools image** (`packetqth-tools`) - Used ONCE for setup:
   ```bash
   docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
     python tools/setup_totp.py YOUR_CALLSIGN
   ```

2. **Runtime image** (`packetqth`) - Used for the server:
   ```bash
   docker-compose up -d
   ```

That's it! No Python installation on host required.

---

**73!** 📡🐳
