# Manual Setup

Step-by-step setup without the interactive wizard. Use this if you prefer to configure files by hand or are automating deployment.

> **Easier alternative:** The [setup wizard](../README.md#2-run-the-setup-wizard) generates all files below in one interactive session.

## 1. Clone the Repository

```bash
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth
```

## 2. Generate a TOTP Secret for Your First User

See [docs/USER_SETUP.md](USER_SETUP.md) for all options. Quick start using the tools image:

```bash
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN
```

Scan the QR code with your authenticator app and note the base32 secret.

## 3. Create users.yaml

```bash
cp users.yaml.example users.yaml
```

Edit `users.yaml` and add your callsign and TOTP secret:

```yaml
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
```

Set restrictive permissions:

```bash
chmod 600 users.yaml
```

See [docs/USER_SETUP.md](USER_SETUP.md) for adding additional users.

## 4. Create .env

```bash
echo "HA_TOKEN=your_long_lived_access_token_here" > .env
chmod 600 .env
```

To create a HomeAssistant long-lived access token:
1. Open HomeAssistant → your profile (bottom left)
2. Scroll to **Long-Lived Access Tokens**
3. Click **Create Token**, copy it into `.env`

## 5. Create config.yaml

```bash
cp config.yaml.example config.yaml
```

Key settings to edit:

```yaml
homeassistant:
  url: http://homeassistant.local:8123   # Your HA URL
  token: ${HA_TOKEN}                      # Reads from .env

telnet:
  host: 0.0.0.0
  port: 8023
  timeout_seconds: 300
  bpq_mode: true                          # Set false for direct telnet testing

security:
  max_auth_attempts: 3

homeassistant:
  entity_filter:
    include_domains:
      - light
      - switch
      - automation
      - cover
      - sensor
    exclude_entities:
      - "sensor.uptime"
      - "sensor.time"
```

See [`config.yaml.example`](../config.yaml.example) for all available options.

## 6. Create docker-compose.yml

Create a `logs/` directory and a `docker-compose.yml`:

```bash
mkdir -p logs
```

```yaml
services:
  packetqth:
    image: ghcr.io/ben-kuhn/packetqth:latest
    container_name: packetqth
    restart: unless-stopped
    user: "1000:1000"          # Replace with your uid:gid (id -u && id -g)
    ports:
      - "127.0.0.1:8023:8023"
    volumes:
      - /path/to/config.yaml:/app/config.yaml:ro
      - /path/to/users.yaml:/app/users.yaml:ro
      - /path/to/logs:/app/logs
    environment:
      - HA_TOKEN=${HA_TOKEN}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
```

Replace `/path/to/` with the absolute path to your config directory, and `1000:1000` with the output of `id -u` and `id -g`.

## 7. Start the Server

```bash
docker compose up -d
docker compose logs -f
```

## 8. Configure LinBPQ

Add to `bpq32.cfg`:

```
APPLICATION 10,PACKETQTH,C 10 HOST localhost 8023
```

Restart LinBPQ, then users connect with `C PACKETQTH`.

## 9. Test

```bash
telnet localhost 8023
```

---

## Adding Users Later

Generate a new TOTP secret (see [docs/USER_SETUP.md](USER_SETUP.md)), add it to `users.yaml`, then restart:

```bash
docker compose restart
```

## Updating

```bash
docker pull ghcr.io/ben-kuhn/packetqth:latest
docker compose up -d
```
