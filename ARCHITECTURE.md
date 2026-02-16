# PacketQTH Architecture

> Detailed software architecture for PacketQTH - HomeAssistant over Packet Radio

## Overview

PacketQTH is a text-based interface for HomeAssistant designed for extremely low-bandwidth packet radio connections (typical 1200 baud). The architecture prioritizes:

1. **Minimal bandwidth** - Every byte counts at 1200 baud
2. **Security over cleartext** - Safe operation without encryption
3. **Simplicity** - Easy to understand and maintain
4. **Reliability** - Graceful degradation and error handling

## System Context

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   linBPQ    │ Telnet  │  PacketQTH   │  HTTP   │ HomeAssistant│
│ Packet Node ├────────▶│    Server    ├────────▶│     API      │
│     (BBS)   │ 1200bd  │              │         │              │
└─────────────┘         └──────────────┘         └─────────────┘
                              ▲
                              │
                         TOTP Codes
                         (Authenticator App)
```

## Design Constraints

### 1. Bandwidth Limitations

**1200 baud** = ~120 bytes/second = ~7200 bytes/minute

Implications:
- Use single-letter commands
- Minimize prompts and output
- Cache frequently accessed data
- Paginate large result sets
- No ANSI colors or fancy formatting

### 2. Legal Requirements

Amateur radio (USA - Part 97) prohibits:
- Message content encryption
- Obscuring message meaning

Solution:
- TOTP for authentication (legal - not encryption)
- All commands and data sent in clear text
- Single-use time-limited codes prevent credential theft

### 3. Security Requirements

Operating over cleartext radio requires:
- No password transmission
- Rate limiting to prevent brute force
- Session management with timeout
- Container isolation for blast radius limitation

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     linBPQ Packet Node                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ Telnet (port 8023)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   TELNET SERVER LAYER                        │
│  • Accept connections                                        │
│  • Handle multiple sessions (async)                          │
│  • Text I/O management                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION LAYER                        │
│  • TOTP verification (login + per-write operation)          │
│  • Session management                                        │
│  • Rate limiting                                             │
│  • Write operation protection                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   COMMAND PARSER LAYER                       │
│  • Parse single-letter commands                              │
│  • Parameter extraction                                      │
│  • Input validation                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   COMMAND HANDLER LAYER                      │
│  • List devices (L)                                          │
│  • Show status (S)                                           │
│  • Control devices (ON/OFF/SET)                              │
│  • Trigger automations (A/T)                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 HOMEASSISTANT API CLIENT                     │
│  • Entity queries                                            │
│  • State changes                                             │
│  • Automation triggers                                       │
│  • Error handling                                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     ENTITY CACHE LAYER                       │
│  • Cache entity list (reduce API calls)                     │
│  • Refresh on demand or interval                             │
│  • Filter by domain                                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   TEXT FORMATTER LAYER                       │
│  • Compact entity display                                    │
│  • Pagination                                                │
│  • Status abbreviations                                      │
│  • Minimal whitespace                                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Telnet Server Layer

**Purpose:** Accept and manage telnet connections

**Implementation:**
- Python `asyncio` for concurrent connections
- Configurable max connections (default: 10)
- Connection timeout (default: 5 minutes inactivity)

**Key Operations:**
```python
async def handle_connection(reader, writer):
    # 1. Display banner
    # 2. Authenticate user (TOTP)
    # 3. Enter command loop
    # 4. Clean up on disconnect
```

**Output Format:**
- Plain ASCII text
- No ANSI codes (compatibility)
- CRLF line endings

### 2. Authentication Layer

**Purpose:** Verify user identity without sending passwords, and protect write operations

**Components:**
- `TOTPAuthenticator` - TOTP verification with rate limiting
- `SessionManager` - Track authenticated sessions

**Flow:**
```
1. User connects
2. System prompts: "Callsign: "
3. User enters: KN4XYZ
4. System prompts: "TOTP Code: "
5. User enters: 123456 (from authenticator app)
6. System verifies code
   ✓ Success → Create session, enter command loop
   ✗ Failure → Show error, retry (max 5 attempts)

7. User enters command
   • Read operation (L/S/A/H/R) → Execute immediately
   • Write operation (ON/OFF/SET/T) → Prompt for fresh TOTP
8. For write operations:
   System prompts: "TOTP Code: "
   User enters: 789012 (fresh code from app)
   System verifies code
   ✓ Success → Execute write operation
   ✗ Failure → Deny operation, stay in session
```

**Security Features:**
- **TOTP-per-write**: Fresh code required for every state change
- **Natural rate limiting**: Write operations limited to 30-second intervals
- **Authentication rate limiting**: 5 failed login attempts per 5 minutes trigger lockout
- Session timeout: 5 minutes inactivity (configurable)
- ±90 second time window (clock drift tolerance)
- Secure session IDs (32 hex chars)

See [auth/README.md](auth/README.md) for details.

### 3. Command Parser Layer

**Purpose:** Parse minimal text commands

**Command Format:**
```
COMMAND [id] [value]
```

**Examples:**
```
L              # List devices
S 1            # Show device 1 status
ON 3           # Turn device 3 on
OFF 3          # Turn device 3 off
SET 1 50       # Set device 1 to 50% (brightness, position, etc.)
A              # List automations
T 2            # Trigger automation 2
H              # Help
Q              # Quit
```

**Parser Logic:**
1. Read line from user
2. Strip whitespace, convert to uppercase
3. Split on whitespace
4. Extract command and parameters
5. Validate command exists
6. Validate parameters (if required)
7. Call appropriate handler

### 4. Command Handler Layer

**Purpose:** Execute commands and format responses

**Handlers:**

#### List Devices (L)
```
Input:  L [page]
Action: Fetch entities from cache, paginate, display
Output:
  DEVICES (pg 1/2)
  1.LT Kitchen    [ON]
  2.SW Garage     [OFF]
  3.SN Temp       72F
  ...
```

#### Show Status (S)
```
Input:  S <id>
Action: Get device details
Output:
  #1 LT Kitchen
  State: ON
  Brightness: 80%
```

#### Control Device (ON/OFF/SET)
```
Input:  ON <id> | OFF <id> | SET <id> <value>
Action: Call HA API to change state
Output:
  OK: Kitchen ON
  or
  ERR: Device not found
```

#### List Automations (A)
```
Input:  A [page]
Action: Get automations from cache
Output:
  AUTOMATIONS (pg 1/1)
  1. Good Night
  2. Morning Routine
```

#### Trigger Automation (T)
```
Input:  T <id>
Action: Call HA API to trigger
Output:
  OK: Good Night triggered
```

### 5. HomeAssistant API Client

**Purpose:** Interface with HomeAssistant REST API

**Implementation:**
- `aiohttp` for async HTTP requests
- Long-lived access token authentication
- Timeout handling (10 seconds default)
- Retry logic for transient failures

**Key Endpoints:**
```
GET  /api/states                    # List all entities
GET  /api/states/<entity_id>        # Get specific entity
POST /api/services/<domain>/<service>  # Control device
POST /api/services/automation/trigger  # Trigger automation
```

**Error Handling:**
- Connection timeout → "ERR: HA offline"
- 401 Unauthorized → "ERR: Invalid token"
- 404 Not Found → "ERR: Device not found"
- 500 Server Error → "ERR: HA error"

### 6. Entity Cache Layer

**Purpose:** Reduce API calls by caching entity list

**Strategy:**
- Fetch all entities on session start
- Cache for 60 seconds (configurable)
- Refresh on demand with `R` command
- Filter by domain (light, switch, sensor, cover, etc.)

**Cache Structure:**
```python
{
  "light.kitchen": {
    "id": 1,                    # Local numeric ID
    "entity_id": "light.kitchen",
    "friendly_name": "Kitchen",
    "state": "on",
    "attributes": {...}
  },
  ...
}
```

**Benefits:**
- Fast device listing (no API call)
- Reduced HA load
- Faster response times

**Trade-offs:**
- Stale data (60 second window)
- Memory usage (minimal - ~100 entities = ~50KB)

### 7. Text Formatter Layer

**Purpose:** Format output for minimal bandwidth

**Techniques:**

#### Entity Abbreviations
```
LT = Light
SW = Switch
SN = Sensor
BL = Blind/Cover
AU = Automation
SC = Scene
```

#### Compact State Display
```
[ON]  = On
[--]  = Off
[50%] = Dimmed to 50%
72F   = Sensor reading
```

#### Pagination
```
DEVICES (pg 1/3)
1.LT Kitchen    [ON]
...
10.SW Garage    [OFF]
[N]ext [P]rev [Q]uit:
```

**Output Budget:**
- List entry: ~25 bytes
  ```
  1.LT Kitchen    [ON]\n
  ```
- Page of 10: ~300 bytes = ~2.5 seconds @ 1200 baud
- Keep pages ≤ 500 bytes for good UX

## Data Flow Examples

### Scenario 1: User Lists Devices

```
User Input:  L
     │
     ▼
┌────────────────────┐
│  Command Parser    │  Parse "L" → LIST command
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  Command Handler   │  Handle LIST
│  (List Devices)    │
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│   Entity Cache     │  Get cached entities
└─────────┬──────────┘  (if stale, fetch from HA)
          │
          ▼
┌────────────────────┐
│  Text Formatter    │  Format as compact list
└─────────┬──────────┘  Apply pagination
          │
          ▼
     Output:
     DEVICES (pg 1/1)
     1.LT Kitchen    [ON]
     2.SW Garage     [OFF]
```

### Scenario 2: User Turns On Light

```
User Input:  ON 1
     │
     ▼
┌────────────────────┐
│  Command Parser    │  Parse "ON 1" → CONTROL command
└─────────┬──────────┘  device_id=1, action=ON
          │
          ▼
┌────────────────────┐
│  Command Handler   │  Handle CONTROL
│  (Control Device)  │  Lookup device 1 in cache
└─────────┬──────────┘  → light.kitchen
          │
          ▼
┌────────────────────┐
│   HA API Client    │  POST /api/services/light/turn_on
└─────────┬──────────┘  {"entity_id": "light.kitchen"}
          │
          ▼
┌────────────────────┐
│  Text Formatter    │  Format response
└─────────┬──────────┘
          │
          ▼
     Output:
     OK: Kitchen ON
```

### Scenario 3: User Authenticates

```
Connection Established
     │
     ▼
┌────────────────────┐
│  Telnet Server     │  Display: "Callsign: "
└─────────┬──────────┘
          │
          ▼
     User Input:  KN4XYZ
     │
     ▼
┌────────────────────┐
│  Telnet Server     │  Display: "TOTP Code: "
└─────────┬──────────┘
          │
          ▼
     User Input:  123456
     │
     ▼
┌────────────────────┐
│ TOTP Authenticator │  Verify code for KN4XYZ
└─────────┬──────────┘  Check rate limit
          │              Validate code
          ▼
     ✓ Valid
     │
     ▼
┌────────────────────┐
│  Session Manager   │  Create session
└─────────┬──────────┘  Generate session ID
          │              Set timeout
          ▼
     Output:
     Authenticated. Welcome KN4XYZ!

     [Main Menu]
```

## Configuration

### config.yaml

Primary application configuration:

```yaml
telnet:
  host: 0.0.0.0
  port: 8023
  max_connections: 10
  timeout_seconds: 300

homeassistant:
  url: http://homeassistant.local:8123
  token: ${HA_TOKEN}
  timeout: 10
  cache_refresh_interval: 60

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
```

### users.yaml

User authentication configuration:

```yaml
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
  W1ABC: "HXDMVJECJJWSRB3H"
```

See [auth/README.md](auth/README.md) for user management.

## Deployment Options

### Option 1: Docker (Recommended)

**Benefits:**
- Container isolation limits blast radius
- Easy deployment and updates
- Reproducible environment

**Security Hardening:**
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
```

**Command:**
```bash
docker-compose up -d
```

### Option 2: Systemd Service

**Benefits:**
- Native Linux service
- Automatic start on boot
- Journal logging

**Installation:**
```bash
sudo cp packetqth.service /etc/systemd/system/
sudo systemctl enable packetqth
sudo systemctl start packetqth
```

### Option 3: Direct Execution

**Benefits:**
- Easy development
- Direct access to logs

**Command:**
```bash
python main.py
```

## Security Considerations

### 1. Authentication

✅ **TOTP-per-Write Protection**
- Fresh TOTP code required for every write operation (ON/OFF/SET/TRIGGER)
- Read operations (L/S/A/H/R) execute without additional auth
- Naturally rate-limits write operations to 30-second intervals
- Prevents replay attacks even if TOTP code is intercepted
- Single-use, time-limited codes
- Safe for cleartext transmission
- Standard authenticator app support

❌ **What We Don't Use:**
- Passwords (would be exposed)
- API keys (would be exposed)
- Encryption (illegal on amateur radio)
- Session-only auth (too risky for write operations)

### 2. Rate Limiting

**Authentication Rate Limiting:**
- 5 failed login attempts → 5 minute lockout
- Prevents brute force attacks
- Per-callsign tracking

**Write Operation Rate Limiting:**
- TOTP window naturally limits writes to 30-second intervals
- Fresh code required per operation
- Cannot be bypassed or batched

### 3. Container Isolation

- Non-root user inside container
- Read-only filesystem
- Dropped capabilities
- Network isolation

### 4. Input Validation

- Sanitize all user input
- Validate command parameters
- Prevent injection attacks

### 5. Session Management

- 5 minute inactivity timeout (configurable)
- Secure random session IDs (32 hex chars)
- Automatic cleanup of expired sessions
- Session only grants read access
- Write operations require fresh TOTP regardless of session

## Performance Considerations

### Bandwidth Budget

At 1200 baud (120 bytes/second):

| Operation | Bytes | Time |
|-----------|-------|------|
| Auth prompt (login) | ~50 | 0.4s |
| List 10 devices | ~300 | 2.5s |
| Control device (read) | ~15 | 0.1s |
| Control device (write) | ~30 | 0.3s (includes TOTP prompt) |
| TOTP prompt | ~15 | 0.1s |
| Response | ~20 | 0.2s |

**Target:** < 3 seconds for read operations, < 1 second for write prompts

**Note:** Write operations require fresh TOTP code, adding ~0.3s overhead

### API Call Optimization

- Cache entity list (60s TTL)
- Batch requests when possible
- Timeout after 10 seconds
- Graceful degradation on failure

### Memory Usage

- ~50KB per cached entity list (100 entities)
- ~10KB per active session
- ~100KB per connection
- **Total:** ~5MB for 10 concurrent users

## Error Handling

### Connection Errors

```
Scenario: HA is unreachable
Response: ERR: HA offline
Action:   Use cached data if available
```

### Authentication Errors

```
Scenario: Invalid TOTP code
Response: Invalid callsign or token
Action:   Increment failed attempt counter
          Apply rate limit if needed
```

### Command Errors

```
Scenario: Device not found
Response: ERR: Device not found
Action:   Display available device IDs
```

## Future Enhancements

### Phase 2: Advanced Features
- [ ] Device filtering by room
- [ ] Command macros (save frequently used sequences)
- [ ] Status polling (optional background updates)
- [ ] Scene and script support
- [ ] Historical data queries
- [ ] Notification system

### Phase 3: Multi-User Enhancements
- [x] Concurrent user support (already implemented)
- [ ] Per-user device access control
- [ ] Activity logging per user
- [ ] User-specific command shortcuts

## Testing Strategy

### Unit Tests
- Authentication logic
- Command parsing
- Text formatting
- Cache management

### Integration Tests
- End-to-end auth flow
- HA API interaction
- Error handling

### Manual Tests
```bash
# Test TOTP auth
python tools/test_totp.py --interactive

# Test HA connectivity
curl -H "Authorization: Bearer $HA_TOKEN" \
  http://homeassistant.local:8123/api/states

# Test telnet
telnet localhost 8023
```

## Monitoring

### Metrics to Track
- Active connections
- Authentication success/failure rate
- HA API response times
- Command frequency
- Error rates

### Logging
```python
INFO  - User KN4XYZ authenticated
INFO  - Command: L (list devices)
INFO  - Command: ON 1 (light.kitchen)
ERROR - HA API timeout
```

## References

- [RFC 6238 - TOTP](https://tools.ietf.org/html/rfc6238)
- [HomeAssistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [FCC Part 97](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97)
- [linBPQ Documentation](https://www.cantab.net/users/john.wiseman/Documents/)

---

**73!** 📡🏠
