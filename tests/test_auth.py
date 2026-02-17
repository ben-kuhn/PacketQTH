"""
Tests for auth/totp.py

Covers: Session, TOTPAuthenticator, SessionManager
"""

import time
import pytest
import pyotp
from datetime import datetime, timedelta
from unittest.mock import patch

from auth.totp import Session, TOTPAuthenticator, SessionManager


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

class TestSession:
    def _make_session(self, last_activity_offset_seconds=0):
        now = datetime.now()
        last = now - timedelta(seconds=last_activity_offset_seconds)
        return Session(
            callsign='KN4XYZ',
            authenticated_at=now,
            last_activity=last,
            session_id='abc123'
        )

    def test_not_expired_when_new(self):
        s = self._make_session(last_activity_offset_seconds=0)
        assert not s.is_expired(timeout_minutes=5)

    def test_expired_after_timeout(self):
        # 31 minutes of inactivity against 30-minute timeout
        s = self._make_session(last_activity_offset_seconds=31 * 60)
        assert s.is_expired(timeout_minutes=30)

    def test_not_expired_before_timeout(self):
        # 29 minutes of inactivity against 30-minute timeout
        s = self._make_session(last_activity_offset_seconds=29 * 60)
        assert not s.is_expired(timeout_minutes=30)

    def test_update_activity_resets_timer(self):
        s = self._make_session(last_activity_offset_seconds=29 * 60)
        s.update_activity()
        # Now activity is fresh - should not be expired even with 1-minute timeout
        assert not s.is_expired(timeout_minutes=1)

    def test_expired_respects_custom_timeout(self):
        s = self._make_session(last_activity_offset_seconds=10 * 60)
        assert s.is_expired(timeout_minutes=5)
        assert not s.is_expired(timeout_minutes=15)

    def test_callsign_uppercased_on_creation(self):
        s = Session(
            callsign='KN4XYZ',
            authenticated_at=datetime.now(),
            last_activity=datetime.now(),
            session_id='x'
        )
        assert s.callsign == 'KN4XYZ'


# ---------------------------------------------------------------------------
# TOTPAuthenticator tests
# ---------------------------------------------------------------------------

class TestTOTPAuthenticator:
    def test_load_users_from_file(self, users_yaml):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        assert 'KN4XYZ' in auth.users
        assert auth.users['KN4XYZ'] == secret

    def test_load_users_missing_file(self, tmp_path):
        auth = TOTPAuthenticator(str(tmp_path / 'nonexistent.yaml'))
        assert auth.users == {}

    def test_verify_valid_totp(self, users_yaml):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        token = pyotp.TOTP(secret).now()
        success, msg = auth.verify_totp('KN4XYZ', token)
        assert success
        assert 'successful' in msg.lower()

    def test_verify_invalid_totp(self, users_yaml):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        success, msg = auth.verify_totp('KN4XYZ', '000000')
        assert not success

    def test_verify_unknown_callsign(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        success, msg = auth.verify_totp('W1UNKNOWN', '123456')
        assert not success

    def test_verify_case_insensitive_callsign(self, users_yaml):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        token = pyotp.TOTP(secret).now()
        success, _ = auth.verify_totp('kn4xyz', token)
        assert success

    def test_rate_limiting_after_5_failures(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        for _ in range(5):
            auth.verify_totp('KN4XYZ', '000000')
        assert auth.is_rate_limited('KN4XYZ')

    def test_not_rate_limited_below_threshold(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        for _ in range(4):
            auth.verify_totp('KN4XYZ', '000000')
        assert not auth.is_rate_limited('KN4XYZ')

    def test_rate_limit_returns_error(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        for _ in range(5):
            auth.verify_totp('KN4XYZ', '000000')
        success, msg = auth.verify_totp('KN4XYZ', '000000')
        assert not success
        assert 'too many' in msg.lower()

    def test_record_failed_attempt(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        assert not auth.is_rate_limited('KN4XYZ')
        for _ in range(5):
            auth.record_failed_attempt('KN4XYZ')
        assert auth.is_rate_limited('KN4XYZ')

    def test_clear_failed_attempts(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        for _ in range(5):
            auth.record_failed_attempt('KN4XYZ')
        assert auth.is_rate_limited('KN4XYZ')
        auth.clear_failed_attempts('KN4XYZ')
        assert not auth.is_rate_limited('KN4XYZ')

    def test_successful_auth_clears_failed_attempts(self, users_yaml):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        # Build up 4 failures
        for _ in range(4):
            auth.record_failed_attempt('KN4XYZ')
        # Successful auth should clear them
        token = pyotp.TOTP(secret).now()
        auth.verify_totp('KN4XYZ', token)
        assert not auth.is_rate_limited('KN4XYZ')

    def test_rate_limit_is_per_callsign(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        for _ in range(5):
            auth.record_failed_attempt('KN4XYZ')
        # Different callsign should not be rate limited
        assert not auth.is_rate_limited('W1OTHER')

    def test_old_failed_attempts_expire(self, users_yaml):
        path, _ = users_yaml
        auth = TOTPAuthenticator(path)
        # Manually add an old attempt (7 minutes ago)
        old_time = time.time() - 420
        auth.failed_attempts['KN4XYZ'] = [old_time] * 5
        # is_rate_limited cleans up old attempts
        assert not auth.is_rate_limited('KN4XYZ')

    def test_reload_users(self, users_yaml, tmp_path):
        path, secret = users_yaml
        auth = TOTPAuthenticator(path)
        assert 'KN4XYZ' in auth.users

        # Add a new user to the file
        import yaml
        new_secret = pyotp.random_base32()
        data = {'users': {'KN4XYZ': secret, 'W1NEW': new_secret}}
        with open(path, 'w') as f:
            yaml.dump(data, f)

        auth.reload_users()
        assert 'W1NEW' in auth.users


# ---------------------------------------------------------------------------
# SessionManager tests
# ---------------------------------------------------------------------------

class TestSessionManager:
    def test_create_session(self):
        sm = SessionManager()
        sid = sm.create_session('KN4XYZ')
        assert sid is not None
        assert len(sid) == 32  # 16 bytes hex = 32 chars

    def test_get_valid_session(self):
        sm = SessionManager()
        sid = sm.create_session('KN4XYZ')
        session = sm.get_session(sid)
        assert session is not None
        assert session.callsign == 'KN4XYZ'

    def test_get_nonexistent_session(self):
        sm = SessionManager()
        assert sm.get_session('nonexistent') is None

    def test_end_session(self):
        sm = SessionManager()
        sid = sm.create_session('KN4XYZ')
        sm.end_session(sid)
        assert sm.get_session(sid) is None

    def test_end_nonexistent_session_is_safe(self):
        sm = SessionManager()
        sm.end_session('nonexistent')  # should not raise

    def test_get_active_sessions(self):
        sm = SessionManager()
        sm.create_session('KN4XYZ')
        sm.create_session('W1ABC')
        sessions = sm.get_active_sessions()
        assert len(sessions) == 2
        callsigns = {s.callsign for s in sessions}
        assert {'KN4XYZ', 'W1ABC'} == callsigns

    def test_cleanup_expired_sessions(self):
        sm = SessionManager(timeout_minutes=1)
        sid = sm.create_session('KN4XYZ')
        # Manually expire the session
        sm.sessions[sid].last_activity = datetime.now() - timedelta(minutes=2)
        sm.cleanup_expired_sessions()
        assert sid not in sm.sessions

    def test_get_session_auto_cleanup(self):
        sm = SessionManager(timeout_minutes=1)
        sid = sm.create_session('KN4XYZ')
        sm.sessions[sid].last_activity = datetime.now() - timedelta(minutes=2)
        result = sm.get_session(sid)
        assert result is None

    def test_get_session_updates_activity(self):
        sm = SessionManager()
        sid = sm.create_session('KN4XYZ')
        before = sm.sessions[sid].last_activity
        sm.get_session(sid)
        after = sm.sessions[sid].last_activity
        assert after >= before

    def test_session_ids_are_unique(self):
        sm = SessionManager()
        ids = {sm.create_session('KN4XYZ') for _ in range(10)}
        assert len(ids) == 10

    def test_callsign_stored_uppercase(self):
        sm = SessionManager()
        sid = sm.create_session('kn4xyz')
        session = sm.get_session(sid)
        assert session.callsign == 'KN4XYZ'
