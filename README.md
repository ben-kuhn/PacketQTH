# PacketQTH

> Control your HomeAssistant from anywhere via packet radio

**PacketQTH** is a minimal, text-based interface for HomeAssistant designed for use over packet radio. Connect via telnet through your linBPQ node and control your smart home with simple commands, at 1200, or even 300 baud.

```
PacketQTH v0.1.0
KN4XYZ

Welcome KN4XYZ!
Type H for help

> L

DEVICES (pg 1/1)
1.LT Kitchen    [ON]
2.LT Bedroom    [--]
3.SW Garage     [ON]
4.SN Temp       72F
N:

> OFF 1
OK: Kitchen Light turned off

> H

COMMANDS
L [pg]    List devices
S <id>    Show device
ON <id>   Turn on
OFF <id>  Turn off
SET <id> <val> Set value
A [pg]    List automations
T <id>    Trigger automation
H         Help (this menu)
Q         Quit
```

## Features

- 🔐 **Secure Authentication** - TOTP-based auth safe for cleartext radio (no passwords transmitted)
- 📡 **Ultra Low Bandwidth** - Optimized for 1200 baud packet radio connections
- ⚡ **Simple Commands** - Single-letter shortcuts for fast operation
- 🏠 **Full HA Control** - Lights, switches, sensors, blinds, and automations
- 🐳 **Containerized** - Docker deployment with security hardening
- 🔒 **Rate Limited** - Protection against brute force attacks
- 📱 **Standard TOTP** - Works with Google Authenticator, Password Managers, etc.

## Why PacketQTH?

Packet radio provides reliable communication when internet and cellular networks fail. With PacketQTH, you can:

- Meet part 97 requirements for automatic operation using relays managed by HomeAssistant without depending on the internet
- Access home automation from remote locations without internet
- Monitor your station's power usage with HomeAssistant-connected sensors over the air
- Demonstrate practical applications of packet radio technology

## Quick Start

### Prerequisites

- HomeAssistant instance with API access
- BPQ packet node/BBS
- Python 3.11+
- Docker (recommended) or systemd

### Dependencies

PacketQTH has minimal dependencies for fast installation:

**Core (required):**
- `pyotp` - TOTP authentication
- `PyYAML` - Configuration files
- `aiohttp` - HomeAssistant API client

**Tools (optional):**
- `qrcode[pil]` - QR code generation for TOTP setup

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth
```

2. **Set up users:**

**Option A: Docker-Only (No Host Dependencies)** ⭐ Recommended for Docker
```bash
# Generate TOTP using Docker (no Python packages needed on host!)
./tools/docker-setup.sh KN4XYZ

# Scan the ASCII QR code displayed in terminal with your authenticator app
```

**Option B: Simple Python (No Packages)**
```bash
# Generate secret using only Python stdlib
python3 tools/generate_secret.py KN4XYZ

# Manually enter the displayed secret into your authenticator app
```

**Option C: Full Setup Tool (Requires Python Packages)**
```bash
# Install tools dependencies on host
pip3 install -r requirements-tools.txt

# Generate with QR code
python3 tools/setup_totp.py KN4XYZ
```

**Add User to Configuration:**
```bash
# Copy example users file
cp users.yaml.example users.yaml

# Add your TOTP secret to users.yaml
nano users.yaml
```

**Note:** See [DOCKER.md](DOCKER.md) for detailed Docker setup instructions.

3. **Configure the application:**
```bash
# Copy example config
cp config.yaml.example config.yaml

# Edit config with your settings
nano config.yaml

# Set your HomeAssistant token (recommended via environment variable)
export HA_TOKEN=your_long_lived_access_token_here
```

Or add the token directly to config.yaml:
```yaml
homeassistant:
  url: http://homeassistant.local:8123
  token: your_long_lived_access_token_here
```

4. **Run with Docker (recommended):**

**Important:** Complete steps 2 and 3 (TOTP setup and configuration) BEFORE running Docker!

```bash
# After setting up users and config on host
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Docker + TOTP Setup Workflow:**
1. Run `setup_totp.py` on your **host machine** (not in container)
2. Scan QR code with your authenticator app
3. Add TOTP secret to `users.yaml` on your host
4. Create `config.yaml` on your host with HA token
5. Run `docker-compose up -d` (mounts config files from host)

**Or run directly without Docker:**
```bash
pip3 install -r requirements.txt
python3 main.py

# Or use the start script
./start.sh
```

5. **Configure LinBPQ:**

Add an application entry to your LinBPQ `bpq32.cfg`:
```
APPLICATION 10,PACKETQTH,C 10 HOST localhost 8023
```

This creates a telnet application that connects to PacketQTH on localhost:8023.

Users can then connect with: `C PACKETQTH` or `TELNET PACKETQTH`

6. **Connect and test:**

Via LinBPQ:
```
BPQ -> TELNET -> Connect to PacketQTH
```

Or directly via telnet for testing:
```bash
telnet localhost 8023
```

## Architecture

PacketQTH uses a layered architecture optimized for low-bandwidth radio:

```
linBPQ Node → Telnet Server → Session Manager → TOTP Auth
                                      ↓
                              Command Parser
                                      ↓
                          HomeAssistant API Client
                                      ↓
                              Entity Cache
                                      ↓
                              Text Formatter
```

Key components:
- **Telnet Server** - Handles incoming connections
- **TOTP Authentication** - Secure auth without passwords
- **Session Manager** - Tracks authenticated users
- **Command Parser** - Minimal text command processing
- **Entity Cache** - Reduces HomeAssistant API calls
- **Text Formatter** - Ultra-compact output

See [ARCHITECTURE.md](ha_packet_architecture.md) for detailed design documentation.

## Security

PacketQTH is designed for security over cleartext radio:

- ✅ **No password transmission** - Uses TOTP one-time codes
- ✅ **Rate limiting** - 5 attempts, 5-minute lockout
- ✅ **Session timeout** - 5-minute inactivity timeout
- ✅ **Container isolation** - Run in Docker with dropped privileges
- ✅ **Read-only filesystem** - Limits attack surface
- ✅ **Audit logging** - Track authentication attempts

### Legal Note

Packet radio in amateur bands (USA) prohibits:
- ❌ Encryption of message content
- ❌ Obscuring message meaning
- ✅ Authentication is permitted (TOTP codes are not encryption)

TOTP provides authentication without encrypting the communication, making it legal for amateur radio use while preventing unauthorized access.

## Usage

### Basic Commands

```
L              List devices (paginated)
S <id>         Show device status
ON <id>        Turn device on
OFF <id>       Turn device off
SET <id> <val> Set device value (e.g., brightness, position)
A              List automations
T <id>         Trigger automation
H              Help menu
Q              Quit
```

### Device Abbreviations

- `LT` - Light
- `SW` - Switch  
- `SN` - Sensor
- `BL` - Blind/Cover

### Example Session

```
> L
DEVICES (pg 1/1)
1.LT Kitchen      [ON]
2.SW Garage       [OFF]

> ON 2
OK: Garage Switch ON

> A
AUTOMATIONS (pg 1/1)
1. Good Night
2. Morning Routine

> T 1
OK: Good Night triggered

> Q
73!
```

## Configuration

### users.yaml

```yaml
users:
  - callsign: KN4XYZ
    totp_secret: JBSWY3DPEHPK3PXP
    enabled: true

security:
  max_failed_attempts: 5
  lockout_duration_seconds: 300
  session_timeout_seconds: 300
```

### config.yaml

```yaml
telnet:
  host: 0.0.0.0
  port: 8023
  max_connections: 10
  timeout_seconds: 300

homeassistant:
  url: http://homeassistant.local:8123
  token: eyJ0eXAiOiJKV1QiLCJhbGc...
  
display:
  page_size: 10
  use_colors: false
  
filters:
  included_domains:
    - light
    - switch
    - automation
    - cover
    - sensor
  excluded_entities:
    - sensor.uptime
```

## Development

### Project Structure

```
packetqth/
├── auth/              # TOTP authentication module
├── server/            # Telnet server and session management
├── commands/          # Command parsing and handlers
├── homeassistant/     # HomeAssistant API client
├── formatting/        # Text output formatting
├── utils/             # Configuration and utilities
└── tools/             # Setup and testing scripts
```

### Running Tests

```bash
# Test TOTP authentication
python tools/test_totp.py

# Interactive auth test
python tools/test_totp.py --interactive

# Generate user secrets
python tools/setup_totp.py <CALLSIGN>
```

### Building Container

```bash
docker build -t packetqth:latest .
docker-compose up -d
```

## Contributing

Contributions welcome! Areas of interest:

- Additional entity types (climate, media players, etc.)
- Command macros/scripting
- APRS integration
- Position-aware automation
- Performance optimizations
- Documentation improvements

Please open an issue first to discuss major changes.

## Roadmap

- [ ] Complete telnet server implementation
- [ ] Command parser and handlers
- [ ] HomeAssistant API client
- [ ] Entity caching layer
- [ ] Text formatter with pagination
- [ ] Status monitoring/polling
- [ ] Command macros
- [ ] APRS integration
- [ ] Multi-language support

## License

GNU General Public License v3.0 or later - See LICENSE file for details

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

## Support

- **Issues:** [GitHub Issues](https://github.com/ben-kuhn/packetqth/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ben-kuhn/packetqth/discussions)
- **Email:** ku0hn@ku0hn.radio

## Acknowledgments

Built for the amateur radio and home automation communities. Special thanks to:

- The HomeAssistant team for their excellent API
- John G8BPQ for linBPQ
- The packet radio community keeping the mode alive

## Ham Radio Resources

- [ARRL Packet Radio](https://www.arrl.org/packet-radio)
- [linBPQ Documentation](https://www.cantab.net/users/john.wiseman/Documents/)
- [Amateur Radio Emergency Communications](https://www.arrl.org/ares)

---

**73 de PacketQTH** 📡🏠

*Control your QTH from anywhere on the airwaves*
