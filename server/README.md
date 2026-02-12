# PacketQTH Telnet Server

Async telnet server with TOTP authentication for packet radio interface.

## Overview

This module provides a full-featured telnet server designed for PacketQTH's low-bandwidth packet radio use case. It handles multiple concurrent connections, TOTP authentication, session management, and command processing.

**Key Features:**

- ✅ **LinBPQ compatible** - Handles BPQ auto-sent callsigns
- ✅ **Async/await** - Non-blocking I/O with asyncio
- ✅ **TOTP authentication** - Integrated with auth module
- ✅ **Session management** - Per-connection state with timeout
- ✅ **Connection limiting** - Configurable max connections
- ✅ **Graceful shutdown** - Clean connection closure
- ✅ **Customizable banner** - Welcome message on connect
- ✅ **Command handler** - Pluggable command processing
- ✅ **Connection tracking** - Statistics and active session monitoring

## Components

### TelnetServer (telnet.py)

Main server that accepts and manages connections.

**Basic Usage:**

```python
import asyncio
from server import TelnetServer
from auth import TOTPAuthenticator, SessionManager

async def command_handler(session, command: str):
    """Handle commands from user."""
    if command.upper() == 'HELLO':
        return "Hello from PacketQTH!"
    return f"Unknown command: {command}"

async def main():
    # Create authenticator and session manager
    authenticator = TOTPAuthenticator('users.yaml')
    session_manager = SessionManager(timeout_minutes=30)

    # Create server
    server = TelnetServer(
        host='0.0.0.0',
        port=8023,
        authenticator=authenticator,
        session_manager=session_manager,
        command_handler=command_handler,
        max_connections=10,
        timeout_seconds=300,
        banner="Welcome to PacketQTH!"
    )

    # Run server
    await server.run()

asyncio.run(main())
```

**From Configuration:**

```python
import yaml
from server import run_server

async def command_handler(session, command):
    # Your command handling logic
    return "OK"

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Run server (handles auth, sessions, signals)
await run_server(config, command_handler=command_handler)
```

### TelnetSession (session.py)

Manages individual telnet connections.

**Features:**
- Line-based text I/O
- TOTP authentication flow
- Command loop with timeout
- Idle time tracking
- Automatic session cleanup

**Session Lifecycle:**

```
Connection → Banner → Authentication → Command Loop → Disconnect
                          ↓
                      Rate Limiting
                      TOTP Verification
                      Session Creation
```

## API Reference

### TelnetServer

#### Constructor

```python
TelnetServer(
    host: str = "0.0.0.0",
    port: int = 8023,
    authenticator: Optional[TOTPAuthenticator] = None,
    session_manager: Optional[SessionManager] = None,
    command_handler: Optional[Callable] = None,
    max_connections: int = 10,
    timeout_seconds: int = 300,
    banner: str = "",
    max_auth_attempts: int = 3
)
```

**Parameters:**
- `host` - Address to bind to (default: all interfaces)
- `port` - Port to listen on (default: 8023)
- `authenticator` - TOTP authenticator instance
- `session_manager` - Session manager instance
- `command_handler` - Async function to handle commands
- `max_connections` - Maximum concurrent connections
- `timeout_seconds` - Inactivity timeout
- `banner` - Welcome banner text
- `max_auth_attempts` - Max authentication attempts per connection

#### Methods

```python
async def start()
```
Start the server (begin listening for connections).

```python
async def serve_forever()
```
Block until shutdown is requested.

```python
async def run()
```
Convenience method: start() + serve_forever().

```python
async def stop()
```
Stop server and close all active connections.

```python
def shutdown()
```
Request shutdown (safe to call from signal handler).

```python
def get_stats() -> Dict[str, Any]
```
Get server statistics (connections, uptime, active sessions).

```python
def get_active_callsigns() -> List[str]
```
Get list of authenticated callsigns currently connected.

```python
@staticmethod
def from_config(config: Dict[str, Any], ...) -> TelnetServer
```
Create server from configuration dictionary.

### TelnetSession

#### Methods

```python
async def send(text: str, newline: bool = True)
```
Send text to client.

```python
async def send_lines(*lines: str)
```
Send multiple lines.

```python
async def read_line(prompt: str = "", timeout: Optional[int] = None) -> Optional[str]
```
Read a line of input from client with optional prompt.

```python
async def authenticate() -> bool
```
Perform TOTP authentication flow.

```python
async def command_loop()
```
Main command processing loop.

```python
async def run(banner: str = "")
```
Run complete session: banner → auth → commands.

```python
async def close()
```
Close connection and cleanup.

```python
def is_authenticated() -> bool
```
Check if session is authenticated.

```python
def get_callsign() -> Optional[str]
```
Get authenticated callsign.

```python
def get_idle_time() -> float
```
Get seconds since last activity.

## Configuration

### Complete Example (config.yaml)

```yaml
telnet:
  # Address to bind to
  host: 0.0.0.0

  # Port to listen on
  port: 8023

  # Maximum concurrent connections
  max_connections: 10

  # Connection timeout in seconds
  timeout_seconds: 300

  # BPQ compatibility mode
  bpq_mode: true

security:
  # Welcome banner
  welcome_banner: "PacketQTH v1.0"

  # Maximum authentication attempts
  max_auth_attempts: 3

  # IP safelist (empty = allow all)
  # ip_safelist:
  #   - 192.168.1.0/24
  #   - 10.0.0.5

auth:
  # Path to users file
  users_file: users.yaml
```

### Banner Formatting

The banner is automatically wrapped in a simple ASCII box:

```python
# Config:
security:
  welcome_banner: "PacketQTH v1.0"

# Displays as:
╔════════════════════════╗
║  PacketQTH v1.0        ║
╚════════════════════════╝
```

## LinBPQ Compatibility

PacketQTH is designed to work seamlessly with LinBPQ packet nodes. BPQ mode handles the specific way BPQ connects to applications.

### How BPQ Connects

When a user connects to an application through LinBPQ:

1. User connects to BPQ node via packet radio
2. User types command to launch application (e.g., "C PACKETQTH")
3. BPQ establishes TCP connection to PacketQTH server
4. **BPQ automatically sends the user's callsign as the first line**
5. PacketQTH authenticates and enters command loop

### BPQ Mode (Default)

When `bpq_mode: true` (default), the server:
- Waits for callsign as first line (no prompt)
- Does not prompt for callsign
- Proceeds directly to TOTP authentication

**Configuration:**

```yaml
telnet:
  bpq_mode: true  # Enable BPQ compatibility (default)
```

**User Experience (from BPQ):**

```
C PACKETQTH
Connected to PACKETQTH
╔════════════════════════╗
║  PacketQTH v1.0        ║
╚════════════════════════╝

TOTP Code: 123456

Authenticated. Welcome KN4XYZ!
>
```

Notice: No "Callsign:" prompt - BPQ sent it automatically.

### Standard Mode

When `bpq_mode: false`, the server:
- Prompts for callsign
- Suitable for direct telnet connections (not through BPQ)

**Configuration:**

```yaml
telnet:
  bpq_mode: false  # Disable BPQ compatibility
```

**User Experience (direct telnet):**

```
telnet localhost 8023
╔════════════════════════╗
║  PacketQTH v1.0        ║
╚════════════════════════╝

Callsign: KN4XYZ
TOTP Code: 123456

Authenticated. Welcome KN4XYZ!
>
```

### Testing BPQ Mode

Use the BPQ simulator to test:

```bash
# Start PacketQTH server
python tools/test_telnet.py

# In another terminal, simulate BPQ connection
python tools/simulate_bpq.py KN4XYZ

# The simulator automatically sends callsign (like BPQ does)
# You'll be prompted for TOTP code
# Then you can test commands interactively
```

### BPQ Configuration

Add PacketQTH to your LinBPQ configuration:

```ini
# In bpq32.cfg or linbpq.conf

[LinBPQ]
...

[Telnet Server]
...
CMDPORT 23 63000

APPLICATION 1,PACKETQTH,C 1 HOST 1 S
```

**Configuration explained:**
- `APPLICATION 1,PACKETQTH` - Application #1 named "PACKETQTH"
- `C 1` - Command "C" triggers application, index 1
- `HOST 1` - Connect to host defined in CMDPORT (port 8023)
- `S` - Return to node on disconnect (optional)

Users connect by typing: `C PACKETQTH` or `C 1`

### Automatic Fallback

BPQ mode includes automatic fallback:

1. Server waits for first line (expecting callsign from BPQ)
2. If empty or malformed line received
3. Server switches to standard mode and prompts for callsign

This allows graceful handling of both BPQ and direct connections.

### BPQ Documentation Reference

For complete LinBPQ applications interface documentation, see:
- [LinBPQ Applications Interface](https://www.cantab.net/users/john.wiseman/Documents/LinBPQ%20Applications%20Interface.html)

## Command Handler

The command handler is an async function that processes user commands.

### Signature

```python
async def command_handler(
    session: TelnetSession,
    command: str
) -> Union[str, List[str], None]
```

**Parameters:**
- `session` - TelnetSession instance (access to send, callsign, etc.)
- `command` - Command string from user

**Returns:**
- `str` - Single line response
- `List[str]` - Multi-line response
- `None` - No response

### Example Command Handler

```python
async def my_command_handler(session, command: str):
    cmd = command.upper().strip()

    if cmd == 'H' or cmd == 'HELP':
        return [
            "AVAILABLE COMMANDS:",
            "H - Help",
            "S - Status",
            "Q - Quit"
        ]

    elif cmd == 'S' or cmd == 'STATUS':
        return f"Callsign: {session.get_callsign()}"

    elif cmd.startswith('ECHO '):
        text = command[5:]
        return f"ECHO: {text}"

    else:
        return f"Unknown command: {command}"
```

### Accessing Server Components

The session has access to core components:

```python
async def command_handler(session, command):
    # Get callsign
    callsign = session.get_callsign()

    # Get idle time
    idle = session.get_idle_time()

    # Send additional output
    await session.send("Processing...")

    # Read more input
    confirm = await session.read_line("Are you sure? (Y/N): ")

    # Access session timeout
    timeout = session.timeout_seconds

    return "OK"
```

## Authentication Flow

### Client Experience

```
Connected to PacketQTH
╔════════════════════════╗
║  PacketQTH v1.0        ║
╚════════════════════════╝

Callsign: KN4XYZ
TOTP Code: 123456

Authenticated. Welcome KN4XYZ!
>
```

### Authentication Process

1. Client connects
2. Server displays banner
3. Server prompts for callsign
4. Server checks rate limiting
5. Server prompts for TOTP code
6. Server verifies code with auth module
7. If successful:
   - Create session in session manager
   - Enter command loop
8. If failed:
   - Record failed attempt
   - Allow retry (up to max_auth_attempts)

### Failed Authentication

```
Callsign: KN4XYZ
TOTP Code: 000000
Invalid callsign or token.
Try again (2 attempts remaining).

Callsign: KN4XYZ
TOTP Code: 000001
Invalid callsign or token.
Try again (1 attempt remaining).

Callsign: KN4XYZ
TOTP Code: 000002
Invalid callsign or token.
Maximum authentication attempts exceeded.
```

### Rate Limiting

If a user has 5 failed attempts in 5 minutes:

```
Callsign: KN4XYZ
TOTP Code: 123456
Too many failed attempts. Try again in 5 minutes.
```

## Session Management

### Session Lifecycle

1. **Created** - After successful authentication
2. **Active** - User is sending commands
3. **Idle** - No activity for some time
4. **Expired** - Idle timeout reached
5. **Ended** - User quit or connection closed

### Timeout Behavior

```python
# Session times out after inactivity
# Default: 300 seconds (5 minutes)

# User is idle for 5 minutes:
Session expired due to inactivity.
```

### Automatic Quit

Built-in commands that end the session:
- `Q`
- `QUIT`
- `EXIT`
- `BYE`

All are case-insensitive.

## Error Handling

### Connection Limit Reached

```
ERR: Connection limit reached. Try again later.
```

### Read Timeout

If no input received within timeout period, connection closes silently.

### Command Handler Errors

If command handler raises an exception:

```python
async def buggy_handler(session, command):
    # This will raise an exception
    result = 1 / 0
    return result

# Client sees:
ERR: Command processing error
```

The server logs the full exception for debugging.

## Statistics & Monitoring

### Get Server Stats

```python
stats = server.get_stats()

# Returns:
{
    'active_connections': 3,
    'max_connections': 10,
    'total_connections': 47,
    'uptime_seconds': 3600.0,
    'listening': True,
    'sessions': [
        {
            'callsign': 'KN4XYZ',
            'remote_addr': '192.168.1.100:12345',
            'authenticated': True,
            'idle_seconds': 15.2
        },
        # ... more sessions
    ]
}
```

### Get Active Users

```python
callsigns = server.get_active_callsigns()
# Returns: ['KN4XYZ', 'W1ABC', 'K2DEF']
```

## Testing

### Quick Test

```bash
# Start test server
python tools/test_telnet.py

# In another terminal, connect
telnet localhost 8023
```

### Test Commands

The test server provides these commands:
- `H` - Help menu
- `S` - Show session stats
- `T` - Test command (returns "OK")
- `E <text>` - Echo text back
- `Q` - Quit

### Custom Port

```bash
python tools/test_telnet.py --port 2323
telnet localhost 2323
```

### Debug Mode

```bash
python tools/test_telnet.py --debug
```

Shows detailed logging of all connections and commands.

## Integration Example

### Complete Server Setup

```python
import asyncio
import yaml
from server import run_server

# Load configuration
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Define command handler
async def handle_command(session, command: str):
    """Process commands from users."""

    cmd = command.upper().strip()

    if cmd == 'L':
        # List devices
        return ["Device 1", "Device 2", "Device 3"]

    elif cmd == 'H':
        # Help
        return ["Commands:", "L - List", "H - Help", "Q - Quit"]

    else:
        return f"Unknown command: {command}"

# Run server
asyncio.run(run_server(config, command_handler=handle_command))
```

### With HomeAssistant Integration

```python
import asyncio
from server import TelnetServer
from homeassistant import HomeAssistantClient
from auth import TOTPAuthenticator, SessionManager

# Create HA client
ha_client = HomeAssistantClient(
    url='http://homeassistant.local:8123',
    token='your_token'
)

# Command handler with HA access
async def ha_command_handler(session, command: str):
    cmd = command.upper().strip()

    if cmd == 'L':
        # List devices from HA
        entities = await ha_client.get_states()
        return [f"{i}. {e['entity_id']}" for i, e in enumerate(entities[:10], 1)]

    elif cmd.startswith('ON '):
        # Turn on device
        device_id = int(cmd.split()[1])
        entity = ha_client.get_entity_by_id(device_id)
        if entity:
            await ha_client.turn_on(entity['entity_id'])
            return f"OK: {entity['entity_id']} ON"
        return "ERR: Device not found"

    return "Unknown command"

# Create and run server
async def main():
    auth = TOTPAuthenticator('users.yaml')
    sessions = SessionManager()

    server = TelnetServer(
        port=8023,
        authenticator=auth,
        session_manager=sessions,
        command_handler=ha_command_handler
    )

    await server.run()

asyncio.run(main())
```

## Deployment

### Standalone

```bash
python -m server.telnet
```

### With systemd

```ini
[Service]
ExecStart=/opt/packetqth/venv/bin/python main.py
WorkingDirectory=/opt/packetqth
```

### With Docker

Already configured in `docker-compose.yml`:

```yaml
ports:
  - "8023:8023"
```

## Troubleshooting

### "Address already in use"

Port is already bound by another process:

```bash
# Find process using port
lsof -i :8023

# Or use different port
python test_telnet.py --port 2323
```

### Connections Rejected

Check `max_connections` setting. Increase if needed:

```yaml
telnet:
  max_connections: 20
```

### Timeout Too Aggressive

Increase timeout:

```yaml
telnet:
  timeout_seconds: 600  # 10 minutes
```

### Authentication Always Fails

1. Check users.yaml format
2. Verify TOTP secret is correct
3. Check time sync on both systems
4. Try automated test: `python tools/test_totp.py`

### No Response to Commands

Verify command handler is registered:

```python
server = TelnetServer(
    command_handler=my_handler  # Must be set!
)
```

## Performance Considerations

### Concurrent Connections

Each connection uses:
- ~10KB memory
- 1 async task
- Minimal CPU (mostly idle)

**Recommendation:** Limit to 10-20 concurrent connections on modest hardware.

### Bandwidth Per Connection

At 1200 baud:
- Authentication: ~200 bytes (~2 seconds)
- Command: ~10 bytes (~0.1 seconds)
- Response: ~50-200 bytes (~0.5-2 seconds)

### Timeout Strategy

Balance between:
- **Short timeout:** Frees resources quickly
- **Long timeout:** Better user experience on slow links

**Recommendation:** 300 seconds (5 minutes) for packet radio.

## Security Considerations

### Authentication

- TOTP codes safe for cleartext transmission
- Rate limiting prevents brute force
- Session timeout limits exposure

### Network Security

**Bind to specific interface:**

```yaml
telnet:
  host: 127.0.0.1  # Localhost only
```

**IP Safelist (recommended):**

Restrict connections to specific IP addresses or networks:

```yaml
security:
  ip_safelist:
    - 192.168.1.0/24      # Local network
    - 10.0.0.5            # Specific IP
    - 2001:db8::/32       # IPv6 network
```

Features:
- ✅ Supports CIDR notation (IPv4 and IPv6)
- ✅ Empty list = allow all (default)
- ✅ Multiple networks/IPs supported
- ✅ Connections rejected before authentication

**Example - Allow only local network:**

```yaml
security:
  ip_safelist:
    - 192.168.1.0/24
```

**Example - Allow specific BPQ node IP:**

```yaml
security:
  ip_safelist:
    - 192.168.1.100  # BPQ node server
```

When an IP is rejected, the connection is immediately closed with:
```
ERR: Connection not allowed from this address.
```

**Additional security layers:**
- Use firewall to restrict access
- Run in container with network isolation

### Connection Limits

Prevent resource exhaustion:

```yaml
telnet:
  max_connections: 10
```

### Logging

All security events are logged:
- Successful authentication
- Failed attempts
- Rate limiting events
- Connection info
- IP safelist rejections

## Further Reading

- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Telnet Protocol (RFC 854)](https://tools.ietf.org/html/rfc854)
- [PacketQTH Architecture](../ARCHITECTURE.md)
- [Authentication Module](../auth/README.md)

---

**73!** 📡
