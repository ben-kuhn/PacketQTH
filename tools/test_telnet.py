#!/usr/bin/env python3
"""
PacketQTH Telnet Server Test Tool

Test the telnet server with a simple command handler.
"""

import sys
import os
import asyncio
import argparse
import yaml
import logging

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import TelnetServer, run_server
from auth import TOTPAuthenticator, SessionManager


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def simple_command_handler(session, command: str):
    """
    Simple command handler for testing.

    Args:
        session: TelnetSession instance
        command: Command string from user

    Returns:
        Response string or list of strings
    """
    cmd = command.upper().strip()

    if cmd == 'H' or cmd == 'HELP':
        return [
            "HELP MENU",
            "H          Help (this menu)",
            "S          Show stats",
            "T          Test command",
            "E          Echo test",
            "Q          Quit",
            "",
            "Commands are case-insensitive."
        ]

    elif cmd == 'S' or cmd == 'STATS':
        return [
            f"Session Info:",
            f"  Callsign: {session.get_callsign()}",
            f"  Remote: {session.get_remote_addr()}",
            f"  Idle: {session.get_idle_time():.1f}s",
            f"  Timeout: {session.timeout_seconds}s"
        ]

    elif cmd == 'T' or cmd == 'TEST':
        return "OK: Test successful!"

    elif cmd.startswith('E ') or cmd == 'E':
        # Echo command
        if len(cmd) > 2:
            echo_text = command[2:].strip()
            return f"ECHO: {echo_text}"
        else:
            return "ECHO: (no text provided)"

    else:
        return [
            f"Unknown command: {command}",
            "Type H for help."
        ]


def load_config(config_file: str) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        logger.warning(f"Config file '{config_file}' not found, using defaults")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config: {e}")
        return {}


async def run_test_server(
    host: str = '0.0.0.0',
    port: int = 8023,
    users_file: str = 'users.yaml',
    max_connections: int = 5,
    timeout: int = 300,
    use_config: bool = False,
    config_file: str = 'config.yaml'
):
    """
    Run telnet server with test command handler.

    Args:
        host: Host to bind to
        port: Port to listen on
        users_file: Path to users.yaml
        max_connections: Max concurrent connections
        timeout: Session timeout in seconds
        use_config: Load settings from config file
        config_file: Path to config file
    """
    if use_config:
        # Load from config file
        config = load_config(config_file)

        # Override with provided values
        if 'telnet' not in config:
            config['telnet'] = {}

        config['telnet']['host'] = host
        config['telnet']['port'] = port
        config['telnet']['max_connections'] = max_connections
        config['telnet']['timeout_seconds'] = timeout

        if 'auth' not in config:
            config['auth'] = {}
        config['auth']['users_file'] = users_file

        if 'security' not in config:
            config['security'] = {}
        if 'welcome_banner' not in config['security']:
            config['security']['welcome_banner'] = 'PacketQTH Test Server'

        # Run server from config
        logger.info("Starting server from configuration...")
        await run_server(config, command_handler=simple_command_handler)

    else:
        # Create manually
        logger.info("Starting server with manual configuration...")

        authenticator = TOTPAuthenticator(users_file)
        session_manager = SessionManager(timeout_minutes=timeout // 60)

        banner = '\n'.join([
            '╔════════════════════════════════════╗',
            '║   PacketQTH Test Server v1.0       ║',
            '╚════════════════════════════════════╝'
        ])

        server = TelnetServer(
            host=host,
            port=port,
            authenticator=authenticator,
            session_manager=session_manager,
            command_handler=simple_command_handler,
            max_connections=max_connections,
            timeout_seconds=timeout,
            banner=banner,
            max_auth_attempts=3
        )

        # Setup signal handlers
        import signal

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            server.shutdown()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            await server.run()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt")
            await server.stop()


async def show_server_info(port: int = 8023):
    """
    Show information about connecting to the server.

    Args:
        port: Port server is listening on
    """
    print("\n" + "="*60)
    print("PacketQTH Telnet Server Test")
    print("="*60)
    print(f"\nServer will listen on port {port}")
    print("\nTo connect, use:")
    print(f"  telnet localhost {port}")
    print("\nOr from another machine:")
    print(f"  telnet <server-ip> {port}")
    print("\nMake sure you have:")
    print("  1. Created users.yaml with test users")
    print("  2. Set up TOTP codes in authenticator app")
    print("\nTo create a test user:")
    print("  python tools/setup_totp.py TEST")
    print("\nAvailable test commands:")
    print("  H  - Help menu")
    print("  S  - Show session stats")
    print("  T  - Test command")
    print("  E <text> - Echo text")
    print("  Q  - Quit")
    print("\n" + "="*60)
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH telnet server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with defaults
  python test_telnet.py

  # Custom port and connection limit
  python test_telnet.py --port 2323 --max-connections 2

  # Use config.yaml settings
  python test_telnet.py --use-config

  # Custom users file
  python test_telnet.py --users-file test_users.yaml

Setup:
  1. Create test user:
     python tools/setup_totp.py TEST --qr-file test.png

  2. Scan QR code with authenticator app

  3. Add user to users.yaml:
     users:
       TEST: "SECRET_FROM_SETUP"

  4. Start test server:
     python test_telnet.py

  5. Connect:
     telnet localhost 8023

  6. Authenticate with TEST and 6-digit code from app
        """
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8023,
        help='Port to listen on (default: 8023)'
    )
    parser.add_argument(
        '--users-file',
        default='users.yaml',
        help='Path to users.yaml file (default: users.yaml)'
    )
    parser.add_argument(
        '--max-connections',
        type=int,
        default=5,
        help='Maximum concurrent connections (default: 5)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Session timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--use-config',
        action='store_true',
        help='Load settings from config.yaml'
    )
    parser.add_argument(
        '--config-file',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Show connection info
    asyncio.run(show_server_info(args.port))

    # Run server
    try:
        asyncio.run(run_test_server(
            host=args.host,
            port=args.port,
            users_file=args.users_file,
            max_connections=args.max_connections,
            timeout=args.timeout,
            use_config=args.use_config,
            config_file=args.config_file
        ))
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
