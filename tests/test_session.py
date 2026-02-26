"""
Tests for server/session.py

Covers: TOTP-per-write logic, authenticate(), command loop gating,
        send/read helpers, idle time tracking.

All async tests use pytest-asyncio.
"""

import asyncio
import pytest
import pyotp
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from auth.totp import TOTPAuthenticator, SessionManager
from server.session import TelnetSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_auth(secret=None, callsign='KN4XYZ'):
    """Create a TOTPAuthenticator with one user loaded in-memory."""
    if secret is None:
        secret = pyotp.random_base32()
    auth = TOTPAuthenticator.__new__(TOTPAuthenticator)
    auth.users_file = 'dummy.yaml'
    auth.users = {callsign: secret}
    auth.failed_attempts = {}
    auth.used_tokens = {}
    return auth, secret


def make_session(lines_to_send, callsign='KN4XYZ', secret=None, bpq_mode=True):
    """
    Build a TelnetSession with mocked reader/writer.

    lines_to_send: list of strings the fake client will "type"
    """
    auth, secret = make_auth(secret=secret, callsign=callsign)
    sm = SessionManager()

    reader = AsyncMock(spec=asyncio.StreamReader)
    # readline returns bytes; each call pops from the front of lines_to_send
    line_iter = iter(lines_to_send)

    async def fake_readline():
        try:
            return (next(line_iter) + '\n').encode()
        except StopIteration:
            return b''

    reader.readline = fake_readline

    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.is_closing.return_value = False
    writer.get_extra_info.return_value = ('127.0.0.1', 12345)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    session = TelnetSession(
        reader=reader,
        writer=writer,
        authenticator=auth,
        session_manager=sm,
        command_handler=None,
        timeout_seconds=300,
        max_auth_attempts=3,
        bpq_mode=bpq_mode
    )

    return session, auth, secret, writer


def get_sent_text(writer):
    """Collect all text sent via writer.write()."""
    parts = []
    for call in writer.write.call_args_list:
        data = call.args[0]
        if isinstance(data, bytes):
            parts.append(data.decode('utf-8', errors='replace'))
    return ''.join(parts)


# ---------------------------------------------------------------------------
# authenticate() tests
# ---------------------------------------------------------------------------

class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_successful_auth_bpq_mode(self):
        callsign = 'KN4XYZ'
        auth, secret = make_auth(callsign=callsign)
        sm = SessionManager()
        token = pyotp.TOTP(secret).now()

        reader = AsyncMock(spec=asyncio.StreamReader)
        lines = [callsign, token]
        line_iter = iter(lines)

        async def fake_readline():
            try:
                return (next(line_iter) + '\n').encode()
            except StopIteration:
                return b''

        reader.readline = fake_readline
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.get_extra_info.return_value = ('127.0.0.1', 1234)
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        session = TelnetSession(
            reader=reader, writer=writer,
            authenticator=auth, session_manager=sm,
            bpq_mode=True
        )

        result = await session.authenticate()
        assert result is True
        assert session.is_authenticated()
        assert session.get_callsign() == callsign

    @pytest.mark.asyncio
    async def test_wrong_totp_fails(self):
        callsign = 'KN4XYZ'
        auth, secret = make_auth(callsign=callsign)
        sm = SessionManager()

        reader = AsyncMock(spec=asyncio.StreamReader)
        # All attempts: callsign + bad token, repeated 3 times
        attempts = [callsign, '000000', callsign, '000000', callsign, '000000']
        line_iter = iter(attempts)

        async def fake_readline():
            try:
                return (next(line_iter) + '\n').encode()
            except StopIteration:
                return b''

        reader.readline = fake_readline
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.get_extra_info.return_value = ('127.0.0.1', 1234)
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        session = TelnetSession(
            reader=reader, writer=writer,
            authenticator=auth, session_manager=sm,
            bpq_mode=True
        )

        result = await session.authenticate()
        assert result is False
        assert not session.is_authenticated()

    @pytest.mark.asyncio
    async def test_invalid_totp_format_rejected(self):
        """Non-6-digit codes are rejected without consuming an attempt."""
        callsign = 'KN4XYZ'
        auth, secret = make_auth(callsign=callsign)
        sm = SessionManager()
        token = pyotp.TOTP(secret).now()

        reader = AsyncMock(spec=asyncio.StreamReader)
        # First attempt: invalid format; second attempt: valid token
        lines = [callsign, 'abc', callsign, token]
        line_iter = iter(lines)

        async def fake_readline():
            try:
                return (next(line_iter) + '\n').encode()
            except StopIteration:
                return b''

        reader.readline = fake_readline
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.get_extra_info.return_value = ('127.0.0.1', 1234)
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        session = TelnetSession(
            reader=reader, writer=writer,
            authenticator=auth, session_manager=sm,
            bpq_mode=True, max_auth_attempts=3
        )

        result = await session.authenticate()
        assert result is True  # valid token on second attempt succeeds

    @pytest.mark.asyncio
    async def test_rate_limited_user_rejected(self):
        callsign = 'KN4XYZ'
        auth, secret = make_auth(callsign=callsign)
        # Pre-load 5 failures to trigger rate limiting
        for _ in range(5):
            auth.record_failed_attempt(callsign)

        sm = SessionManager()
        token = pyotp.TOTP(secret).now()

        reader = AsyncMock(spec=asyncio.StreamReader)
        lines = [callsign, token]
        line_iter = iter(lines)

        async def fake_readline():
            try:
                return (next(line_iter) + '\n').encode()
            except StopIteration:
                return b''

        reader.readline = fake_readline
        writer = MagicMock(spec=asyncio.StreamWriter)
        writer.is_closing.return_value = False
        writer.get_extra_info.return_value = ('127.0.0.1', 1234)
        writer.write = MagicMock()
        writer.drain = AsyncMock()
        writer.close = MagicMock()
        writer.wait_closed = AsyncMock()

        session = TelnetSession(
            reader=reader, writer=writer,
            authenticator=auth, session_manager=sm,
            bpq_mode=True
        )

        result = await session.authenticate()
        assert result is False


# ---------------------------------------------------------------------------
# is_write_operation classification (via command model)
# ---------------------------------------------------------------------------

class TestWriteOperationClassification:
    """Integration: Command.is_write_operation() works as expected."""

    def test_on_is_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.ON, raw_input='ON 1', device_id=1)
        assert cmd.is_write_operation()

    def test_off_is_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.OFF, raw_input='OFF 1', device_id=1)
        assert cmd.is_write_operation()

    def test_set_is_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.SET, raw_input='SET 1 50', device_id=1, value='50')
        assert cmd.is_write_operation()

    def test_trigger_is_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.TRIGGER, raw_input='T 1', device_id=1)
        assert cmd.is_write_operation()

    def test_list_is_not_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.LIST, raw_input='L')
        assert not cmd.is_write_operation()

    def test_show_is_not_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.SHOW, raw_input='S 1', device_id=1)
        assert not cmd.is_write_operation()

    def test_automations_is_not_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.AUTOMATIONS, raw_input='A')
        assert not cmd.is_write_operation()

    def test_help_is_not_write(self):
        from commands.models import Command, CommandType
        cmd = Command(type=CommandType.HELP, raw_input='H')
        assert not cmd.is_write_operation()


# ---------------------------------------------------------------------------
# send() and send_lines() helpers
# ---------------------------------------------------------------------------

class TestSendHelpers:
    @pytest.mark.asyncio
    async def test_send_adds_crlf(self):
        session, auth, secret, writer = make_session([])
        await session.send('Hello')
        sent = get_sent_text(writer)
        assert 'Hello\r\n' in sent

    @pytest.mark.asyncio
    async def test_send_no_newline(self):
        session, auth, secret, writer = make_session([])
        await session.send('Prompt', newline=False)
        sent = get_sent_text(writer)
        assert 'Prompt' in sent
        assert 'Prompt\r\n' not in sent

    @pytest.mark.asyncio
    async def test_send_lines_sends_each(self):
        session, auth, secret, writer = make_session([])
        await session.send_lines('Line1', 'Line2', 'Line3')
        sent = get_sent_text(writer)
        assert 'Line1' in sent
        assert 'Line2' in sent
        assert 'Line3' in sent


# ---------------------------------------------------------------------------
# Idle time tracking
# ---------------------------------------------------------------------------

class TestIdleTime:
    @pytest.mark.asyncio
    async def test_idle_time_increases_over_time(self):
        session, _, _, _ = make_session([])
        t0 = session.get_idle_time()
        await asyncio.sleep(0.05)
        t1 = session.get_idle_time()
        assert t1 > t0

    @pytest.mark.asyncio
    async def test_send_resets_idle_time(self):
        session, _, _, _ = make_session([])
        await asyncio.sleep(0.05)
        before = session.get_idle_time()
        await session.send('ping')
        after = session.get_idle_time()
        assert after < before


# ---------------------------------------------------------------------------
# get_callsign / get_remote_addr / is_authenticated before auth
# ---------------------------------------------------------------------------

class TestSessionState:
    def test_not_authenticated_initially(self):
        session, _, _, _ = make_session([])
        assert not session.is_authenticated()

    def test_callsign_none_before_auth(self):
        session, _, _, _ = make_session([])
        assert session.get_callsign() is None

    def test_remote_addr_set(self):
        session, _, _, _ = make_session([])
        assert session.get_remote_addr() == '127.0.0.1:12345'
