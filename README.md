# PacketQTH

> Control your HomeAssistant from anywhere via packet radio

**PacketQTH** is a minimal, text-based interface for HomeAssistant designed for use over packet radio. Connect via telnet through your linBPQ node and control your smart home with simple commands, even at 1200 baud.

The name combines "Packet" (radio) with "QTH" (ham radio Q-code for location/home) - representing remote home control via packet radio.

```
Connected to PACKETQTH
Callsign: KN4XYZ
TOTP Code: 123456

Authenticated. Welcome KN4XYZ!

MAIN MENU
[L]ist devices
[A]utomations
[H]elp
[Q]uit
> L

DEVICES (pg 1/1)
1.LT Kitchen      [ON]
2.LT Bedroom      [OFF]
3.SW Garage       [ON]

> OFF 1
OK: Kitchen Light OFF
```

## Features

- 🔐 **Secure Authentication** - TOTP-based auth safe for cleartext radio (no passwords transmitted)
- 📡 **Ultra Low Bandwidth** - Optimized for 1200 baud packet radio connections
- ⚡ **Simple Commands** - Single-letter shortcuts for fast operation
- 🏠 **Full HA Control** - Lights, switches, sensors, blinds, and automations
- 🐳 **Containerized** - Docker deployment with security hardening
- 🔒 **Rate Limited** - Protection against brute force attacks
- 📱 **Standard TOTP** - Works with Google Authenticator, Authy, etc.

## Why PacketQTH?

Packet radio provides reliable communication when internet and cellular networks fail. With PacketQTH, you can:

- Control your home during emergencies or disasters
- Access home automation from remote locations without internet
- Integrate home control with EMCOMM operations
- Demonstrate practical applications of packet radio technology

## Quick Start

### Prerequisites

- HomeAssistant instance with API access
- linBPQ packet node/BBS
- Python 3.11+
- Docker (recommended) or systemd

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/packetqth.git
cd packetqth
```

2. **Create user configuration:**
```bash
python tools/setup_totp.py KN4XYZ --qr-file qr.png
```
Scan the QR code with your authenticator app and add the user to `users.yaml`.

3. **Configure HomeAssistant connection:**
```yaml
# config.yaml
homeassistant:
  url: http://homeassistant.local:8123
  token: your_long_lived_access_token_here
```

4. **Run with Docker:**
```bash
docker-compose up -d
```

Or install dependencies and run directly:
```bash
pip install -r requirements.txt
python main.py
```

5. **Configure linBPQ:**
Point your linBPQ telnet gateway to `localhost:8023` (or your server IP).

6. **Connect and enjoy!**

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

MIT License - See LICENSE file for details

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/packetqth/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/packetqth/discussions)
- **Email:** your.callsign@example.com

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
