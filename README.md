# PacketQTH

> Control your HomeAssistant from anywhere via packet radio

[![Docker Image](https://img.shields.io/badge/docker-ghcr.io-blue?logo=docker)](https://github.com/ben-kuhn/packetqth/pkgs/container/packetqth)
[![License](https://img.shields.io/badge/license-GPLv3+-blue.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/ben-kuhn/packetqth)](https://github.com/ben-kuhn/packetqth/releases)

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

TOTP Code: 123456
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

* Write operations (ON/OFF/SET/T) require fresh TOTP code
```

## Features

- 🔐 **Enhanced Security** - TOTP code required for every write operation (not just login)
- 🛡️ **Natural Rate Limiting** - Write operations limited to 30-second intervals by TOTP window
- 📡 **Ultra Low Bandwidth** - Optimized for 1200 baud packet radio connections
- ⚡ **Simple Commands** - Single-letter shortcuts for fast operation
- 🏠 **Full HA Control** - Lights, switches, sensors, blinds, and automations
- 🐳 **Containerized** - Docker deployment with security hardening
- 🔒 **Brute Force Protection** - 5 attempts trigger 5-minute lockout
- 📱 **Standard TOTP** - Works with Google Authenticator, Authy, password managers, etc.

## Why PacketQTH?

Packet radio provides reliable communication when internet and cellular networks fail. With PacketQTH, you can:

- Meet part 97 requirements for automatic operation using relays managed by HomeAssistant without depending on the internet
- Access home automation from remote locations without internet
- Monitor your station's power usage with HomeAssistant-connected sensors over the air
- Demonstrate practical applications of packet radio technology

## Quick Start

### Prerequisites

- HomeAssistant instance with API access
- Docker or Podman
- A linBPQ node (for packet radio use; telnet works directly for testing)

### 1. Clone the repository

```bash
git clone https://github.com/ben-kuhn/packetqth.git
cd packetqth
```

### 2. Run the setup wizard

The wizard generates `config.yaml`, `.env`, `users.yaml`, and `docker-compose.generated.yml` in one interactive session. It connects to your HomeAssistant to test the connection and lets you select which entities to expose.

```bash
# Podman (rootless):
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

During setup you will be shown a QR code — scan it with your authenticator app (Google Authenticator, Authy, etc.) before closing the wizard.

> **Prefer to configure manually?** See [docs/MANUAL_SETUP.md](docs/MANUAL_SETUP.md).

### 3. Start the server

```bash
# Use the generated compose file, or rename it:
cp docker-compose.generated.yml docker-compose.yml

docker compose up -d
docker compose logs -f
```

### 4. Configure LinBPQ

Add an application entry to your `bpq32.cfg`:

```
APPLICATION 10,PACKETQTH,C 10 HOST localhost 8023
```

Users connect with `C PACKETQTH` or `TELNET PACKETQTH`.

### 5. Test

```bash
telnet localhost 8023
```

## Usage

### Commands

```
L [pg]         List devices (paginated)
S <id>         Show device status
ON <id>        Turn device on
OFF <id>       Turn device off
SET <id> <val> Set device value (brightness, position, etc.)
A [pg]         List automations
T <id>         Trigger automation
H              Help
Q              Quit
```

Write operations (ON/OFF/SET/T) require a fresh TOTP code. Read operations (L/S/A/H) execute immediately.

### Device Abbreviations

| Code | Type |
|------|------|
| `LT` | Light |
| `SW` | Switch |
| `SN` | Sensor |
| `BL` | Blind/Cover |

## Architecture

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

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## Security

PacketQTH is designed for security over cleartext radio:

- ✅ **No password transmission** - Uses TOTP one-time codes
- ✅ **TOTP-per-write** - Fresh code required for every state change
- ✅ **Natural rate limiting** - 30-second intervals enforced by TOTP window
- ✅ **Authentication rate limiting** - Failed attempts trigger lockout
- ✅ **Session timeout** - Configurable inactivity timeout
- ✅ **Container isolation** - Dropped capabilities, read-only filesystem
- ✅ **Audit logging** - Authentication and write attempts logged

### Legal Note

Packet radio in amateur bands (USA) prohibits encryption of message content. TOTP provides authentication without encrypting the communication, making it legal for amateur radio use.

## Development

### Project Structure

```
packetqth/
├── auth/              # TOTP authentication
├── server/            # Telnet server and session management
├── commands/          # Command parsing and handlers
├── homeassistant/     # HomeAssistant API client
├── formatting/        # Text output formatting
├── tools/             # Setup scripts and utilities
└── docs/              # Documentation
```

### Running Tests

```bash
.venv/bin/pytest
```

### Building the Container

```bash
docker build -t packetqth:latest .
```

## Contributing

Contributions welcome! Areas of interest:

- Additional entity types (climate, media players, etc.)
- Command macros/scripting
- Status monitoring/polling for live updates
- Documentation improvements
- Testing and bug fixes

Please open an issue first to discuss major changes.

## Roadmap

**Completed:**
- [x] Telnet server, command parser, HomeAssistant API client
- [x] TOTP authentication with rate limiting and per-write codes
- [x] Entity caching and text formatter with pagination
- [x] LinBPQ compatibility (BPQ mode)
- [x] Multi-platform Docker images (amd64, arm64, armv7)
- [x] Interactive setup wizard
- [x] Security hardening

**Planned:**
- [ ] Status monitoring/polling for live state updates
- [ ] Command macros for custom shortcuts
- [ ] Scene and script support
- [ ] Climate and media player support

## License

GNU General Public License v3.0 or later — see [LICENSE](LICENSE).

## Support

- **Issues:** [GitHub Issues](https://github.com/ben-kuhn/packetqth/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ben-kuhn/packetqth/discussions)
- **Email:** ku0hn@ku0hn.radio

## Acknowledgments

Built for the amateur radio and home automation communities. Special thanks to:

- The HomeAssistant team for their excellent API
- John G8BPQ for linBPQ
- The packet radio community keeping the mode alive

---

**73 de PacketQTH** 📡🏠

*Control your QTH from anywhere on the airwaves*
