"""
Tests for server/telnet.py

Covers: is_ip_allowed (CIDR, IPv4, IPv6, empty safelist, invalid),
        get_stats, get_active_callsigns, TelnetServer.__init__ config.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from auth.totp import TOTPAuthenticator, SessionManager
from server.telnet import TelnetServer
from server.session import TelnetSession


def make_server(ip_safelist=None, **kwargs):
    """Build a TelnetServer with minimal mocking."""
    auth = MagicMock(spec=TOTPAuthenticator)
    sm = MagicMock(spec=SessionManager)
    return TelnetServer(
        host='127.0.0.1',
        port=8023,
        authenticator=auth,
        session_manager=sm,
        ip_safelist=ip_safelist,
        **kwargs
    )


# ---------------------------------------------------------------------------
# is_ip_allowed
# ---------------------------------------------------------------------------

class TestIsIpAllowed:
    def test_empty_safelist_allows_all(self):
        server = make_server(ip_safelist=[])
        assert server.is_ip_allowed('1.2.3.4')
        assert server.is_ip_allowed('192.168.1.100')
        assert server.is_ip_allowed('10.0.0.1')

    def test_none_safelist_allows_all(self):
        server = make_server(ip_safelist=None)
        assert server.is_ip_allowed('1.2.3.4')

    def test_exact_ip_allowed(self):
        server = make_server(ip_safelist=['192.168.1.1'])
        assert server.is_ip_allowed('192.168.1.1')

    def test_exact_ip_blocked(self):
        server = make_server(ip_safelist=['192.168.1.1'])
        assert not server.is_ip_allowed('192.168.1.2')

    def test_cidr_subnet_allowed(self):
        server = make_server(ip_safelist=['192.168.1.0/24'])
        assert server.is_ip_allowed('192.168.1.1')
        assert server.is_ip_allowed('192.168.1.254')

    def test_cidr_subnet_blocked(self):
        server = make_server(ip_safelist=['192.168.1.0/24'])
        assert not server.is_ip_allowed('192.168.2.1')
        assert not server.is_ip_allowed('10.0.0.1')

    def test_multiple_networks(self):
        server = make_server(ip_safelist=['10.0.0.0/8', '192.168.0.0/16'])
        assert server.is_ip_allowed('10.1.2.3')
        assert server.is_ip_allowed('192.168.5.5')
        assert not server.is_ip_allowed('172.16.0.1')

    def test_localhost_allowed(self):
        server = make_server(ip_safelist=['127.0.0.0/8'])
        assert server.is_ip_allowed('127.0.0.1')
        assert server.is_ip_allowed('127.0.0.255')

    def test_ipv6_loopback(self):
        server = make_server(ip_safelist=['::1/128'])
        assert server.is_ip_allowed('::1')

    def test_ipv6_subnet(self):
        server = make_server(ip_safelist=['fe80::/10'])
        assert server.is_ip_allowed('fe80::1')
        assert not server.is_ip_allowed('2001::1')

    def test_invalid_ip_returns_false(self):
        server = make_server(ip_safelist=['192.168.1.0/24'])
        assert not server.is_ip_allowed('not_an_ip')
        assert not server.is_ip_allowed('')

    def test_invalid_safelist_entry_ignored(self):
        # Invalid entry should be silently skipped
        server = make_server(ip_safelist=['invalid_entry', '192.168.1.0/24'])
        # Valid entry still works
        assert server.is_ip_allowed('192.168.1.5')

    def test_host_bits_not_strict(self):
        # 192.168.1.5/24 has host bits set - strict=False should handle it
        server = make_server(ip_safelist=['192.168.1.5/24'])
        assert server.is_ip_allowed('192.168.1.100')

    def test_single_host_cidr(self):
        server = make_server(ip_safelist=['10.0.0.1/32'])
        assert server.is_ip_allowed('10.0.0.1')
        assert not server.is_ip_allowed('10.0.0.2')


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_stats_structure(self):
        server = make_server()
        stats = server.get_stats()
        required_keys = {
            'active_connections', 'max_connections',
            'total_connections', 'uptime_seconds',
            'listening', 'sessions'
        }
        assert required_keys.issubset(stats.keys())

    def test_no_uptime_before_start(self):
        server = make_server()
        stats = server.get_stats()
        assert stats['uptime_seconds'] is None

    def test_uptime_after_start_time_set(self):
        server = make_server()
        server.start_time = datetime.now() - timedelta(seconds=60)
        stats = server.get_stats()
        assert stats['uptime_seconds'] is not None
        assert stats['uptime_seconds'] >= 60

    def test_active_connections_empty(self):
        server = make_server()
        stats = server.get_stats()
        assert stats['active_connections'] == 0
        assert stats['sessions'] == []

    def test_total_connections_tracked(self):
        server = make_server()
        server.total_connections = 42
        stats = server.get_stats()
        assert stats['total_connections'] == 42

    def test_max_connections_in_stats(self):
        server = make_server(max_connections=5)
        stats = server.get_stats()
        assert stats['max_connections'] == 5

    def test_stats_with_mock_session(self):
        server = make_server()
        mock_session = MagicMock(spec=TelnetSession)
        mock_session.get_callsign.return_value = 'KN4XYZ'
        mock_session.get_remote_addr.return_value = '127.0.0.1:1234'
        mock_session.is_authenticated.return_value = True
        mock_session.get_idle_time.return_value = 10.0

        server.active_sessions = [mock_session]
        stats = server.get_stats()

        assert stats['active_connections'] == 1
        assert len(stats['sessions']) == 1
        session_info = stats['sessions'][0]
        assert session_info['callsign'] == 'KN4XYZ'
        assert session_info['authenticated'] is True
        assert session_info['idle_seconds'] == 10.0


# ---------------------------------------------------------------------------
# get_active_callsigns
# ---------------------------------------------------------------------------

class TestGetActiveCallsigns:
    def test_empty_when_no_sessions(self):
        server = make_server()
        assert server.get_active_callsigns() == []

    def test_returns_authenticated_callsigns(self):
        server = make_server()
        s1 = MagicMock(spec=TelnetSession)
        s1.is_authenticated.return_value = True
        s1.get_callsign.return_value = 'KN4XYZ'

        s2 = MagicMock(spec=TelnetSession)
        s2.is_authenticated.return_value = True
        s2.get_callsign.return_value = 'W1ABC'

        server.active_sessions = [s1, s2]
        callsigns = server.get_active_callsigns()
        assert set(callsigns) == {'KN4XYZ', 'W1ABC'}

    def test_excludes_unauthenticated(self):
        server = make_server()
        unauthed = MagicMock(spec=TelnetSession)
        unauthed.is_authenticated.return_value = False
        unauthed.get_callsign.return_value = None

        server.active_sessions = [unauthed]
        assert server.get_active_callsigns() == []

    def test_excludes_none_callsign(self):
        server = make_server()
        session = MagicMock(spec=TelnetSession)
        session.is_authenticated.return_value = True
        session.get_callsign.return_value = None  # authenticated but no callsign yet

        server.active_sessions = [session]
        assert server.get_active_callsigns() == []


# ---------------------------------------------------------------------------
# TelnetServer initialization
# ---------------------------------------------------------------------------

class TestTelnetServerInit:
    def test_default_host_and_port(self):
        server = TelnetServer()
        assert server.host == '0.0.0.0'
        assert server.port == 8023

    def test_custom_host_and_port(self):
        server = TelnetServer(host='127.0.0.1', port=9999)
        assert server.host == '127.0.0.1'
        assert server.port == 9999

    def test_default_creates_authenticator(self):
        server = TelnetServer()
        assert isinstance(server.authenticator, TOTPAuthenticator)

    def test_default_creates_session_manager(self):
        server = TelnetServer()
        assert isinstance(server.session_manager, SessionManager)

    def test_from_config(self):
        config = {
            'telnet': {
                'host': '0.0.0.0',
                'port': 8023,
                'max_connections': 5,
                'timeout_seconds': 120,
                'banner': 'Hello!',
                'max_auth_attempts': 3,
                'bpq_mode': False,
            },
            'security': {
                'ip_safelist': ['192.168.0.0/16']
            }
        }
        server = TelnetServer.from_config(config)
        assert server.port == 8023
        assert server.max_connections == 5
        assert server.bpq_mode is False
        assert len(server.ip_safelist) == 1
