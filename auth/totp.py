"""
PacketQTH TOTP Authentication

Time-based One-Time Password authentication for packet radio.
Safe for cleartext transmission - no passwords sent over the air!
"""

import pyotp
import time
import yaml
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import secrets


@dataclass
class Session:
    """Represents an authenticated session"""
    callsign: str
    authenticated_at: datetime
    last_activity: datetime
    session_id: str

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()


class TOTPAuthenticator:
    """
    TOTP-based authentication manager.

    Features:
    - Time-based codes (6 digits, 30 second validity)
    - Rate limiting (5 attempts per 5 minutes)
    - ±90 second time window (tolerates clock drift)
    - No passwords over cleartext radio!
    """

    def __init__(self, users_file: str = 'users.yaml'):
        """
        Initialize authenticator.

        Args:
            users_file: Path to YAML file containing user callsigns and TOTP secrets
        """
        self.users_file = users_file
        self.users: Dict[str, str] = {}
        self.failed_attempts: Dict[str, list] = {}
        self.used_tokens: Dict[str, Dict[str, float]] = {}  # callsign -> {token -> expiry_time}
        self.load_users()

    def load_users(self):
        """Load users from YAML configuration file"""
        try:
            with open(self.users_file, 'r') as f:
                data = yaml.safe_load(f)
                self.users = data.get('users', {})
        except FileNotFoundError:
            print(f"Warning: Users file '{self.users_file}' not found. No users loaded.")
            self.users = {}
        except yaml.YAMLError as e:
            print(f"Error parsing users file: {e}")
            self.users = {}

    def reload_users(self):
        """Reload users from file (for adding new users without restart)"""
        self.load_users()

    def is_rate_limited(self, callsign: str) -> bool:
        """
        Check if a callsign is rate limited.

        Rate limit: 5 failed attempts in 5 minutes = 5 minute lockout

        Args:
            callsign: Ham radio callsign to check

        Returns:
            True if rate limited, False otherwise
        """
        if callsign not in self.failed_attempts:
            return False

        # Clean up old attempts (> 5 minutes)
        cutoff_time = time.time() - 300  # 5 minutes ago
        self.failed_attempts[callsign] = [
            attempt for attempt in self.failed_attempts[callsign]
            if attempt > cutoff_time
        ]

        # Check if we have 5+ failed attempts in the last 5 minutes
        return len(self.failed_attempts[callsign]) >= 5

    def record_failed_attempt(self, callsign: str):
        """Record a failed authentication attempt"""
        if callsign not in self.failed_attempts:
            self.failed_attempts[callsign] = []
        self.failed_attempts[callsign].append(time.time())

    def clear_failed_attempts(self, callsign: str):
        """Clear failed attempts for a callsign (on successful auth)"""
        if callsign in self.failed_attempts:
            del self.failed_attempts[callsign]

    def verify_totp(self, callsign: str, token: str) -> Tuple[bool, str]:
        """
        Verify a TOTP token for a callsign.

        Args:
            callsign: Ham radio callsign (case insensitive)
            token: 6-digit TOTP code

        Returns:
            Tuple of (success: bool, message: str)
        """
        callsign = callsign.upper()

        # Check rate limiting
        if self.is_rate_limited(callsign):
            return False, "Too many failed attempts. Try again in 5 minutes."

        # Check if user exists
        if callsign not in self.users:
            self.record_failed_attempt(callsign)
            return False, "Invalid callsign or token."

        # Replay attack prevention: reject tokens already used within their validity window
        now = time.time()
        callsign_used = self.used_tokens.get(callsign, {})
        # Purge expired entries while we're here
        callsign_used = {t: exp for t, exp in callsign_used.items() if exp > now}
        if token in callsign_used:
            return False, "Code already used. Wait for next code."

        # Get user's TOTP secret
        secret = self.users[callsign]
        totp = pyotp.TOTP(secret)

        # Verify token with ±90 second window (3 intervals @ 30 sec each)
        # This tolerates clock drift between client and server
        if totp.verify(token, valid_window=3):
            # Record token as consumed for the full validity window (3 * 30s)
            callsign_used[token] = now + 90
            self.used_tokens[callsign] = callsign_used
            self.clear_failed_attempts(callsign)
            return True, "Authentication successful."
        else:
            self.record_failed_attempt(callsign)
            return False, "Invalid callsign or token."


class SessionManager:
    """
    Manages authenticated sessions.

    Features:
    - Session timeout (default 30 minutes)
    - Automatic cleanup of expired sessions
    - Activity tracking
    """

    def __init__(self, timeout_minutes: int = 30):
        """
        Initialize session manager.

        Args:
            timeout_minutes: Session timeout in minutes (default 30)
        """
        self.sessions: Dict[str, Session] = {}
        self.timeout_minutes = timeout_minutes

    def create_session(self, callsign: str) -> str:
        """
        Create a new authenticated session.

        Args:
            callsign: Ham radio callsign

        Returns:
            Session ID
        """
        session_id = secrets.token_hex(16)
        now = datetime.now()

        session = Session(
            callsign=callsign.upper(),
            authenticated_at=now,
            last_activity=now,
            session_id=session_id
        )

        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session object if valid and not expired, None otherwise
        """
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]

        # Check if expired
        if session.is_expired(self.timeout_minutes):
            del self.sessions[session_id]
            return None

        # Update activity and return
        session.update_activity()
        return session

    def end_session(self, session_id: str):
        """End a session (logout)"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.is_expired(self.timeout_minutes)
        ]
        for sid in expired:
            del self.sessions[sid]

    def get_active_sessions(self) -> list:
        """Get list of all active sessions"""
        self.cleanup_expired_sessions()
        return list(self.sessions.values())
