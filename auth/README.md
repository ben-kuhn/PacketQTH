# PacketQTH Authentication Module

TOTP-based authentication system designed for secure operation over cleartext packet radio.

## Overview

This module provides Time-based One-Time Password (TOTP) authentication for PacketQTH. TOTP is ideal for packet radio because:

- **No passwords transmitted** - Only time-based codes sent over the air
- **Single-use codes** - Each 6-digit code is valid for only 30 seconds
- **Legal for amateur radio** - Authentication is permitted; encryption is not
- **Standard compatible** - Works with Google Authenticator, Authy, 1Password, etc.

## Components

### TOTPAuthenticator

Handles TOTP verification with security features:

- ✅ Time-based code verification (6 digits, 30-second validity)
- ✅ Clock drift tolerance (±90 second window)
- ✅ Rate limiting (5 attempts per 5 minutes)
- ✅ User management from YAML configuration
- ✅ Hot-reload support for adding users without restart

**Example:**
```python
from auth import TOTPAuthenticator

auth = TOTPAuthenticator('users.yaml')

# Verify a TOTP code
success, message = auth.verify_totp('KN4XYZ', '123456')

if success:
    print(f"Authenticated: {message}")
else:
    print(f"Failed: {message}")
```

### SessionManager

Manages authenticated user sessions:

- ✅ Session creation and tracking
- ✅ Automatic timeout (default 30 minutes)
- ✅ Activity-based session renewal
- ✅ Secure random session IDs
- ✅ Automatic cleanup of expired sessions

**Example:**
```python
from auth import SessionManager

sessions = SessionManager(timeout_minutes=30)

# Create session after successful auth
session_id = sessions.create_session('KN4XYZ')

# Later, validate session
session = sessions.get_session(session_id)
if session:
    print(f"Valid session for {session.callsign}")
else:
    print("Session expired or invalid")

# Logout
sessions.end_session(session_id)
```

## Setup for New Users

### 1. Generate TOTP Secret

Use the included setup tool:

```bash
python tools/setup_totp.py KN4XYZ
```

This generates:
- Base32 secret for manual entry
- QR code (terminal or PNG file)
- Configuration entry for users.yaml

### 2. Scan QR Code

Open your authenticator app and scan the QR code. Supported apps:
- Google Authenticator (Android/iOS)
- Authy (Android/iOS/Desktop)
- 1Password
- Microsoft Authenticator
- Any RFC 6238 compatible app

### 3. Add to Configuration

Add the generated entry to `users.yaml`:

```yaml
users:
  - callsign: KN4XYZ
    totp_secret: JBSWY3DPEHPK3PXP
    enabled: true
```

### 4. Test Authentication

```bash
# Automated test (generates codes from secrets)
python tools/test_totp.py --automated

# Interactive test (use your authenticator app)
python tools/test_totp.py --interactive
```

## Security Features

### Rate Limiting

Prevents brute force attacks:
- **Limit:** 5 failed attempts in 5 minutes
- **Lockout:** 5 minutes
- **Automatic cleanup:** Old attempts removed after 5 minutes

### Time Window Tolerance

Accounts for clock drift between client and server:
- **Window:** ±90 seconds (3 intervals @ 30 seconds each)
- **Reason:** Packet radio operators may have clocks slightly out of sync
- **Trade-off:** Slightly longer vulnerability window for better usability

### Session Management

- **Timeout:** 30 minutes of inactivity (configurable)
- **Renewal:** Automatic on activity
- **IDs:** Cryptographically secure random tokens (32 hex characters)

## Why TOTP for Packet Radio?

### Legal Compliance

Amateur radio regulations (USA - Part 97) prohibit:
- ❌ Encryption of message content
- ❌ Obscuring message meaning

TOTP is legal because:
- ✅ It's authentication, not encryption
- ✅ The meaning of transmitted codes is clear (they're auth tokens)
- ✅ No message content is encrypted or obscured

### Security Over Cleartext

Even though anyone can listen to packet radio transmissions:

- **Codes are single-use** - Intercepted codes expire in 30 seconds
- **No password exposure** - Secrets never transmitted
- **Time-limited** - Old codes cannot be replayed
- **Rate limited** - Brute force attacks are impractical

### Attack Scenarios

| Attack | Mitigation |
|--------|-----------|
| Code interception | Code expires in 30 seconds |
| Code replay | Time-based validation prevents reuse |
| Brute force | Rate limiting (5 attempts / 5 minutes) |
| Secret theft | Secrets stored securely, never transmitted |

## Configuration

### users.yaml Format

The users are configured using the format expected by `TOTPAuthenticator`:

```yaml
users:
  # Callsign (key): TOTP Secret (value)
  KN4XYZ: "JBSWY3DPEHPK3PXP"
  W1ABC: "HXDMVJECJJWSRB3H"
  K2DEF: "MNOPQRSTUVWXYZ23"
```

**Note:** The example users.yaml in the project root uses a different format with additional metadata. The code expects the simpler dict format shown above.

### Customizing Security Settings

In your application code:

```python
# Custom rate limiting
auth = TOTPAuthenticator('users.yaml')
# Rate limit settings are hardcoded (5 attempts, 5 min window)

# Custom session timeout
sessions = SessionManager(timeout_minutes=60)  # 1 hour timeout
```

## Troubleshooting

### "Invalid callsign or token"

- Check that the callsign is in users.yaml
- Verify TOTP secret is correct
- Ensure authenticator app is synced (check time on both devices)
- Try the next code if you're near a 30-second boundary

### "Too many failed attempts"

- Rate limited for 5 minutes
- Wait for lockout to expire
- Check system time is correct

### Time Sync Issues

TOTP requires reasonably synchronized clocks:
- **Tolerance:** ±90 seconds built-in
- **Fix:** Sync system clock (ntpdate, systemd-timesyncd)
- **Test:** `python tools/test_totp.py --automated` (generates valid codes)

### Adding Users Without Restart

```python
# Reload users from file
auth.reload_users()
```

This allows adding new users to users.yaml without restarting the application.

## Implementation Details

### TOTP Algorithm (RFC 6238)

- **Hash:** HMAC-SHA1
- **Digits:** 6
- **Interval:** 30 seconds
- **Window:** 3 intervals (±90 seconds)

### Dependencies

- `pyotp` - TOTP implementation
- `qrcode` - QR code generation (setup tool)
- `yaml` - Configuration parsing

### Thread Safety

This module is **not thread-safe**. For concurrent access:
- Use locks around `verify_totp()` calls
- Use separate `SessionManager` instances per thread, or
- Implement your own synchronization

## API Reference

### TOTPAuthenticator

```python
class TOTPAuthenticator:
    def __init__(self, users_file: str = 'users.yaml')
    def load_users(self)
    def reload_users(self)
    def is_rate_limited(self, callsign: str) -> bool
    def verify_totp(self, callsign: str, token: str) -> Tuple[bool, str]
```

### SessionManager

```python
class SessionManager:
    def __init__(self, timeout_minutes: int = 30)
    def create_session(self, callsign: str) -> str
    def get_session(self, session_id: str) -> Optional[Session]
    def end_session(self, session_id: str)
    def cleanup_expired_sessions(self)
    def get_active_sessions(self) -> list
```

### Session

```python
@dataclass
class Session:
    callsign: str
    authenticated_at: datetime
    last_activity: datetime
    session_id: str

    def is_expired(self, timeout_minutes: int = 30) -> bool
    def update_activity(self)
```

## Further Reading

- [RFC 6238 - TOTP](https://tools.ietf.org/html/rfc6238)
- [FCC Part 97 - Amateur Radio Service](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97)
- [ARRL - Digital Modes and Authentication](https://www.arrl.org/digital)

---

**73!** 📡🔐
