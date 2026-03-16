# Quick Start - Docker Only

Complete setup using only Docker (no Python installation required on host).

## Prerequisites

- Docker or Podman installed
- HomeAssistant with API access

## Setup Steps

### 1. Run the Setup Wizard

The interactive setup wizard generates all config files (`config.yaml`, `.env`, `users.yaml`, `docker-compose.generated.yml`) in one step:

```bash
# Podman (rootless) — use --userns=keep-id for volume mounts:
podman run --rm -it \
  --userns=keep-id \
  -v $(pwd):/config \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml

# Docker:
docker run --rm -it \
  --user $(id -u):$(id -g) \
  -v $(pwd):/config \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml
```

The wizard will prompt for:
- HomeAssistant URL and API token (tests connection)
- Telnet server port and timeout settings
- Entity filter (which HA domains/entities to expose)
- First user callsign (generates TOTP, displays QR code to scan)
- Docker host port for the generated compose file

**Scan the QR code** displayed during user setup with your authenticator app (Google Authenticator, Authy, etc.)

**Alternative (TOTP only):** If you only need to generate a TOTP secret without the wizard:
```bash
# Terminal QR code (no volume mount needed):
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN

# Save QR code as PNG (writes to host directory):
# Podman:
podman run --rm --userns=keep-id -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png
# Docker:
docker run --rm --user $(id -u):$(id -g) -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png
```

### 2. Clone Repository

```bash
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth
```

> **Note:** If you ran the wizard before cloning, move the generated config files into the cloned directory.

### 3. Start PacketQTH

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
ON <id>        Turn on (requires fresh TOTP)
OFF <id>       Turn off (requires fresh TOTP)
SET <id> <val> Set value (requires fresh TOTP)
A              List automations
T <id>         Trigger automation (requires fresh TOTP)
H              Help
Q              Quit
```

**Security Note:** Write operations (ON/OFF/SET/T) require a fresh TOTP code for each action. Read operations (L/S/A/H) execute immediately. This provides enhanced security over cleartext radio and naturally rate-limits changes to 30-second intervals.

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

### Permission Denied When Running Setup Wizard

**Problem:** `PermissionError` writing to `/config` when running `configure.py`

**Solution:** Rootless Podman maps `--user $(id -u):$(id -g)` to a subuid, not your real host uid. Use `--userns=keep-id` instead:
```bash
podman run --rm -it --userns=keep-id -v $(pwd):/config \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml
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
# Generate TOTP for new user (prints secret + QR code to terminal)
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py W1ABC

# Add secret to users.yaml
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

1. **Tools image** (`packetqth-tools`) - Used for setup:
   ```bash
   # Full wizard (recommended — generates all config files):
   podman run --rm -it --userns=keep-id -v $(pwd):/config \
     ghcr.io/ben-kuhn/packetqth-tools:latest \
     python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml

   # TOTP only (for adding individual users):
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
