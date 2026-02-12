"""
PacketQTH Telnet Server

Async telnet server for PacketQTH packet radio interface.
"""

import asyncio
import logging
import signal
import ipaddress
from typing import Optional, Callable, Dict, Any, List, Union
from datetime import datetime

from auth import TOTPAuthenticator, SessionManager
from .session import TelnetSession


logger = logging.getLogger(__name__)


class TelnetServer:
    """
    Async telnet server with TOTP authentication.

    Features:
    - Multiple concurrent connections
    - Per-connection authentication
    - Configurable connection limits
    - Graceful shutdown
    - Connection tracking
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8023,
        authenticator: Optional[TOTPAuthenticator] = None,
        session_manager: Optional[SessionManager] = None,
        command_handler: Optional[Callable] = None,
        max_connections: int = 10,
        timeout_seconds: int = 300,
        banner: str = "",
        max_auth_attempts: int = 3,
        bpq_mode: bool = True,
        ip_safelist: Optional[List[str]] = None
    ):
        """
        Initialize telnet server.

        Args:
            host: Host address to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 8023)
            authenticator: TOTP authenticator (creates default if None)
            session_manager: Session manager (creates default if None)
            command_handler: Async function to handle commands
            max_connections: Maximum concurrent connections (default: 10)
            timeout_seconds: Connection timeout in seconds (default: 300)
            banner: Welcome banner to display on connect
            max_auth_attempts: Maximum authentication attempts (default: 3)
            bpq_mode: BPQ compatibility mode - expects callsign as first line (default: True)
            ip_safelist: List of allowed IP addresses/networks in CIDR notation (empty = allow all)
        """
        self.host = host
        self.port = port
        self.authenticator = authenticator or TOTPAuthenticator()
        self.session_manager = session_manager or SessionManager()
        self.command_handler = command_handler
        self.max_connections = max_connections
        self.timeout_seconds = timeout_seconds
        self.banner = banner
        self.max_auth_attempts = max_auth_attempts
        self.bpq_mode = bpq_mode

        # Parse IP safelist (supports CIDR notation)
        self.ip_safelist: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = []
        if ip_safelist:
            for ip_entry in ip_safelist:
                try:
                    # Parse as network (supports CIDR notation like 192.168.1.0/24)
                    network = ipaddress.ip_network(ip_entry, strict=False)
                    self.ip_safelist.append(network)
                    logger.debug(f"Added to safelist: {network}")
                except ValueError as e:
                    logger.error(f"Invalid IP/network in safelist: {ip_entry} - {e}")

        # Server state
        self.server: Optional[asyncio.Server] = None
        self.active_sessions: List[TelnetSession] = []
        self.total_connections = 0
        self.start_time: Optional[datetime] = None
        self.shutdown_event = asyncio.Event()

    def is_ip_allowed(self, ip_address: str) -> bool:
        """
        Check if an IP address is in the safelist.

        Args:
            ip_address: IP address to check

        Returns:
            True if allowed (or safelist is empty), False otherwise
        """
        # Empty safelist = allow all
        if not self.ip_safelist:
            return True

        try:
            ip = ipaddress.ip_address(ip_address)

            # Check if IP is in any of the safelist networks
            for network in self.ip_safelist:
                if ip in network:
                    return True

            return False

        except ValueError as e:
            logger.error(f"Invalid IP address: {ip_address} - {e}")
            return False

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """
        Handle a new telnet connection.

        Args:
            reader: Stream reader
            writer: Stream writer
        """
        # Get remote address
        peername = writer.get_extra_info('peername')
        remote_ip = peername[0] if peername else "unknown"
        remote_addr = f"{peername[0]}:{peername[1]}" if peername else "unknown"

        # Check IP safelist
        if not self.is_ip_allowed(remote_ip):
            logger.warning(f"Connection rejected (not in safelist): {remote_addr}")

            try:
                writer.write(b"ERR: Connection not allowed from this address.\r\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

            return

        # Check connection limit
        if len(self.active_sessions) >= self.max_connections:
            logger.warning(f"Connection limit reached, rejecting {remote_addr}")

            try:
                writer.write(b"ERR: Connection limit reached. Try again later.\r\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

            return

        # Create session
        session = TelnetSession(
            reader=reader,
            writer=writer,
            authenticator=self.authenticator,
            session_manager=self.session_manager,
            command_handler=self.command_handler,
            timeout_seconds=self.timeout_seconds,
            max_auth_attempts=self.max_auth_attempts,
            bpq_mode=self.bpq_mode
        )

        # Track session
        self.active_sessions.append(session)
        self.total_connections += 1

        logger.info(
            f"New session started from {session.get_remote_addr()} "
            f"({len(self.active_sessions)}/{self.max_connections} active)"
        )

        try:
            # Run session
            await session.run(banner=self.banner)

        except Exception as e:
            logger.error(f"Session error: {e}", exc_info=True)

        finally:
            # Remove from active sessions
            if session in self.active_sessions:
                self.active_sessions.remove(session)

            logger.info(
                f"Session ended from {session.get_remote_addr()} "
                f"({len(self.active_sessions)}/{self.max_connections} active)"
            )

    async def start(self):
        """
        Start the telnet server.

        Raises:
            OSError: If unable to bind to port
        """
        logger.info(f"Starting telnet server on {self.host}:{self.port}")

        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                self.host,
                self.port
            )

            self.start_time = datetime.now()

            # Get actual bound address (useful if port was 0)
            addrs = ', '.join(
                f"{sock.getsockname()[0]}:{sock.getsockname()[1]}"
                for sock in self.server.sockets
            )

            logger.info(f"Telnet server listening on {addrs}")
            logger.info(f"Max connections: {self.max_connections}")
            logger.info(f"Session timeout: {self.timeout_seconds}s")

        except OSError as e:
            logger.error(f"Failed to start server: {e}")
            raise

    async def serve_forever(self):
        """
        Serve connections until shutdown.

        This method blocks until shutdown is requested.
        """
        if not self.server:
            raise RuntimeError("Server not started. Call start() first.")

        logger.info("Server ready. Waiting for connections...")

        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except asyncio.CancelledError:
            logger.info("Server cancelled")

        finally:
            await self.stop()

    async def stop(self):
        """Stop the server and close all connections."""
        logger.info("Stopping telnet server...")

        # Close server (stop accepting new connections)
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Server closed")

        # Close all active sessions
        if self.active_sessions:
            logger.info(f"Closing {len(self.active_sessions)} active sessions...")

            close_tasks = [session.close() for session in self.active_sessions]
            await asyncio.gather(*close_tasks, return_exceptions=True)

            self.active_sessions.clear()
            logger.info("All sessions closed")

        logger.info("Server stopped")

    async def run(self):
        """
        Start server and run until shutdown.

        Convenience method that combines start() and serve_forever().
        """
        await self.start()
        await self.serve_forever()

    def shutdown(self):
        """Request server shutdown (can be called from signal handler)."""
        logger.info("Shutdown requested")
        self.shutdown_event.set()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.

        Returns:
            Dictionary with server stats
        """
        uptime = None
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            'active_connections': len(self.active_sessions),
            'max_connections': self.max_connections,
            'total_connections': self.total_connections,
            'uptime_seconds': uptime,
            'listening': self.server is not None and self.server.is_serving(),
            'sessions': [
                {
                    'callsign': session.get_callsign(),
                    'remote_addr': session.get_remote_addr(),
                    'authenticated': session.is_authenticated(),
                    'idle_seconds': session.get_idle_time()
                }
                for session in self.active_sessions
            ]
        }

    def get_active_callsigns(self) -> List[str]:
        """
        Get list of authenticated callsigns.

        Returns:
            List of callsigns for authenticated sessions
        """
        return [
            session.get_callsign()
            for session in self.active_sessions
            if session.is_authenticated() and session.get_callsign()
        ]

    @staticmethod
    def from_config(
        config: Dict[str, Any],
        authenticator: Optional[TOTPAuthenticator] = None,
        session_manager: Optional[SessionManager] = None,
        command_handler: Optional[Callable] = None
    ) -> 'TelnetServer':
        """
        Create TelnetServer from configuration dict.

        Expected config format:
        {
            'telnet': {
                'host': '0.0.0.0',
                'port': 8023,
                'max_connections': 10,
                'timeout_seconds': 300,
                'bpq_mode': True
            },
            'security': {
                'welcome_banner': 'PacketQTH v1.0',
                'max_auth_attempts': 3,
                'ip_safelist': ['192.168.1.0/24', '10.0.0.0/8']
            }
        }

        Args:
            config: Configuration dictionary
            authenticator: TOTP authenticator instance
            session_manager: Session manager instance
            command_handler: Command handler function

        Returns:
            TelnetServer instance
        """
        telnet_config = config.get('telnet', {})
        security_config = config.get('security', {})

        # Build banner
        banner_text = security_config.get('welcome_banner', 'PacketQTH')
        if banner_text:
            # Create simple ASCII box around banner
            banner_width = len(banner_text) + 4
            banner = '\n'.join([
                '╔' + '═' * banner_width + '╗',
                '║  ' + banner_text + '  ║',
                '╚' + '═' * banner_width + '╝'
            ])
        else:
            banner = ''

        return TelnetServer(
            host=telnet_config.get('host', '0.0.0.0'),
            port=telnet_config.get('port', 8023),
            authenticator=authenticator,
            session_manager=session_manager,
            command_handler=command_handler,
            max_connections=telnet_config.get('max_connections', 10),
            timeout_seconds=telnet_config.get('timeout_seconds', 300),
            banner=banner,
            max_auth_attempts=security_config.get('max_auth_attempts', 3),
            bpq_mode=telnet_config.get('bpq_mode', True),
            ip_safelist=security_config.get('ip_safelist', [])
        )


async def run_server(
    config: Dict[str, Any],
    command_handler: Optional[Callable] = None
):
    """
    Run telnet server from configuration.

    This is a convenience function that:
    - Creates authenticator and session manager
    - Creates and starts server
    - Handles shutdown signals
    - Provides clean shutdown

    Args:
        config: Configuration dictionary
        command_handler: Optional command handler function
    """
    # Create authenticator and session manager
    authenticator = TOTPAuthenticator(config.get('auth', {}).get('users_file', 'users.yaml'))
    session_manager = SessionManager(
        timeout_minutes=config.get('telnet', {}).get('timeout_seconds', 300) // 60
    )

    # Create server
    server = TelnetServer.from_config(
        config=config,
        authenticator=authenticator,
        session_manager=session_manager,
        command_handler=command_handler
    )

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        server.shutdown()

    if hasattr(signal, 'SIGTERM'):
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

    if hasattr(signal, 'SIGINT'):
        loop.add_signal_handler(signal.SIGINT, signal_handler)

    # Run server
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
        await server.stop()
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        await server.stop()
        raise
