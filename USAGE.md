# PacketQTH Usage Guide

Complete guide to using PacketQTH.

## Table of Contents

- [Connecting](#connecting)
- [Authentication](#authentication)
- [Commands](#commands)
- [Device Control](#device-control)
- [Automations](#automations)
- [Tips & Tricks](#tips--tricks)

## Connecting

### Via LinBPQ

1. Connect to your LinBPQ node via packet radio
2. Use the telnet command to connect to PacketQTH
3. LinBPQ will automatically send your callsign

```
C KN4XYZ-5
Connected to KN4XYZ-5
*** Connected to BPQ
BPQ> TELNET PACKETQTH

PacketQTH v0.1.0
TOTP Code:
```

### Via Direct Telnet (Testing)

For testing without LinBPQ:

```bash
telnet localhost 8023
```

You'll be prompted for your callsign:

```
PacketQTH v0.1.0
Callsign: KN4XYZ
TOTP Code:
```

## Authentication

PacketQTH uses TOTP (Time-based One-Time Password) for secure authentication over cleartext radio.

### Setting Up TOTP

1. Generate your TOTP secret:
```bash
python tools/setup_totp.py KN4XYZ --qr-file qr.png
```

2. Scan the QR code with your authenticator app:
   - Google Authenticator
   - Authy
   - Microsoft Authenticator
   - Any RFC 6238 compatible app

3. Add your secret to `users.yaml`

### Logging In

1. Connect to PacketQTH
2. Enter your 6-digit TOTP code when prompted
3. The code changes every 30 seconds

**Example:**
```
TOTP Code: 123456

Welcome KN4XYZ!
Type H for help

>
```

### Failed Authentication

- You have 3 attempts per connection
- After 5 failed attempts in 5 minutes, your callsign is rate-limited
- Wait 5 minutes before trying again

## Commands

All commands are designed to be ultra-compact for low bandwidth.

### Command Format

```
<COMMAND> [parameters]
```

Commands are case-insensitive: `L`, `l`, and `LIST` all work.

### Command Reference

| Command | Parameters | Description | Example |
|---------|------------|-------------|---------|
| `L` | `[page]` | List devices | `L` or `L 2` |
| `S` | `<id>` | Show device details | `S 1` |
| `ON` | `<id>` | Turn device on | `ON 1` |
| `OFF` | `<id>` | Turn device off | `OFF 2` |
| `SET` | `<id> <val>` | Set device value | `SET 1 75` |
| `A` | `[page]` | List automations | `A` or `A 2` |
| `T` | `<id>` | Trigger automation | `T 1` |
| `H` | | Show help menu | `H` |
| `R` | | Refresh entity cache | `R` |
| `Q` | | Quit session | `Q` |

### Command Aliases

Many commands have multiple forms:

- `L`, `LIST` - List devices
- `A`, `AUTO`, `AUTOMATIONS` - List automations
- `H`, `HELP`, `?` - Help
- `Q`, `QUIT`, `EXIT`, `BYE` - Quit

## Device Control

### Listing Devices

```
> L

DEVICES (pg 1/2)
1.LT Kitchen    [ON]
2.LT Bedroom    [--]
3.SW Garage     [ON]
4.SN Temp       72F
5.BL Blinds     75%
6.CL Thermostat 70F
7.FN Ceiling    50%
8.LK Front Door [ON]
9.SC Movie      [--]
10.AU GoodNight [ON]
N:
```

**Entity Abbreviations:**
- `LT` - Light
- `SW` - Switch
- `SN` - Sensor
- `BL` - Blind/Cover
- `CL` - Climate
- `FN` - Fan
- `LK` - Lock
- `SC` - Scene
- `AU` - Automation

**State Indicators:**
- `[ON]` - Device is on
- `[--]` - Device is off
- `[??]` - State unknown/unavailable
- `75%` - Percentage value
- `72F` - Temperature value

**Pagination:**
- `N:` - Next page available
- `P:` - Previous page available
- `N P:` - Both available

Navigate pages: `L 2`, `L 3`, etc.

### Showing Device Details

Get detailed information about a specific device:

```
> S 1

#1 LT Kitchen
State: [ON]
Bright: 78%
Entity: light.kitchen
Domain: light
```

### Turning Devices On/Off

Simple on/off control:

```
> ON 1
OK: Kitchen Light turned on

> OFF 2
OK: Bedroom Light turned off
```

**Works with:**
- Lights
- Switches
- Fans
- Scenes
- Scripts
- Automations (enable/disable)

### Setting Values

Set brightness, position, temperature, etc:

```
> SET 1 128
OK: Kitchen Light set to 128

> SET 5 75
OK: Blinds set to 75

> SET 6 72
OK: Thermostat set to 72
```

**Value Ranges:**

| Device Type | Parameter | Range |
|-------------|-----------|-------|
| Light | Brightness | 0-255 |
| Cover/Blind | Position | 0-100 (0=closed, 100=open) |
| Climate | Temperature | -50 to 120 |
| Fan | Speed | 0-100 |

## Automations

### Listing Automations

```
> A

AUTOMATIONS (pg 1/1)
1.AU GoodNight  [ON]
2.AU Morning    [ON]
3.AU Away       [--]
```

### Triggering Automations

Run an automation:

```
> T 1
OK: Good Night Routine triggered
```

### Enabling/Disabling Automations

Use `ON` and `OFF` commands:

```
> OFF 3
OK: Away Mode turned off

> ON 3
OK: Away Mode turned on
```

## Tips & Tricks

### Bandwidth Optimization

**Keep commands short:**
- ✅ `L` (1 byte)
- ❌ `LIST` (4 bytes)

**Use pagination:**
- Default: 10 items per page (~2 seconds @ 1200 baud)
- Configure in `config.yaml`: `display.page_size`

**Avoid excessive refreshing:**
- Entity cache is refreshed automatically
- Manual refresh: `R` command

### Common Workflows

**Turn off all lights at bedtime:**
```
> L           # List devices
> OFF 1       # Kitchen
> OFF 2       # Bedroom
> OFF 7       # Living room
> T 1         # Trigger "Good Night" automation
```

**Check sensor status:**
```
> L           # List devices
> S 4         # Show temperature sensor
> S 8         # Show humidity sensor
```

**Adjust blinds by time of day:**
```
> SET 5 0     # Morning: closed
> SET 5 75    # Afternoon: 75% open
> SET 5 0     # Evening: closed
```

### Error Messages

**Device not found:**
```
> ON 99
ERR: Device #99 not found
Use L to list devices
```

**Invalid command:**
```
> INVALID
ERR: Unknown command: INVALID
```

**Cannot control device:**
```
> ON 4
ERR: Sensor cannot be turned on
Use SET to control this device
```

**Value out of range:**
```
> SET 1 300
ERR: Light brightness must be 0-255
Example: SET 1 128
```

### Session Management

**Session timeout:**
- Default: 5 minutes of inactivity
- Configure in `config.yaml`: `telnet.timeout_seconds`

**Graceful exit:**
```
> Q
73!
```

**Connection lost:**
- Session automatically ends
- Reconnect and authenticate again

### Security Best Practices

1. **Never share your TOTP secret**
   - Keep QR code secure
   - Don't transmit secret over radio

2. **Use strong callsign verification**
   - Ensure your LinBPQ node properly identifies users
   - Only authorized callsigns in `users.yaml`

3. **Enable IP safelist**
   - Restrict connections to known IPs
   - Use CIDR notation: `192.168.1.0/24`

4. **Monitor logs**
   - Check `packetqth.log` for suspicious activity
   - Failed auth attempts are logged

5. **Regular TOTP rotation**
   - Regenerate secrets periodically
   - Update authenticator apps

### Troubleshooting

**Can't connect:**
1. Check PacketQTH is running: `docker ps` or `ps aux | grep python`
2. Check port: `netstat -an | grep 8023`
3. Check LinBPQ configuration
4. Check firewall rules

**Authentication fails:**
1. Verify TOTP code is current (30-second window)
2. Check time sync on client device
3. Verify callsign in `users.yaml`
4. Check rate limiting: wait 5 minutes

**Devices not showing:**
1. Check HomeAssistant connection
2. Verify HA token is valid
3. Check entity filters in `config.yaml`
4. Use `R` command to refresh cache

**Commands not working:**
1. Check device ID with `L` command
2. Verify device type supports operation
3. Check HomeAssistant logs
4. Check PacketQTH logs: `tail -f packetqth.log`

**Slow performance:**
1. Reduce `page_size` in config
2. Use more aggressive filtering
3. Check network latency to HA
4. Consider local HA instance

## Advanced Usage

### Custom Entity Filters

Edit `config.yaml`:

```yaml
homeassistant:
  entity_filter:
    # Only these domains
    include_domains:
      - light
      - switch

    # Exclude specific entities
    exclude_entities:
      - "sensor.*_battery"
      - "light.basement_*"
```

### Multiple Users

Add multiple callsigns to `users.yaml`:

```yaml
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
  W1ABC: "HXDMVJECJJWSRB3H"
  N2DEF: "MFRGGZDFMZTWQ2LK"
```

Each user needs their own TOTP secret.

### IP Safelist

Restrict access to specific networks:

```yaml
security:
  ip_safelist:
    - "192.168.1.0/24"    # Local network
    - "10.0.0.0/8"        # VPN
    - "44.0.0.0/8"        # AMPRNet
```

Empty list = allow all connections.

### Docker Deployment

Production setup with Docker:

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### Systemd Service

Run as systemd service:

```bash
# Copy service file
sudo cp packetqth.service /etc/systemd/system/

# Enable and start
sudo systemctl enable packetqth
sudo systemctl start packetqth

# Check status
sudo systemctl status packetqth

# View logs
sudo journalctl -u packetqth -f
```

---

**73!** 📡 Happy remote home controlling!
