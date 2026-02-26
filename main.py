#!/usr/bin/env python3
"""
PacketQTH Main Application

Text-based HomeAssistant interface for packet radio.
Integrates TOTP authentication, telnet server, and command handling.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
import yaml
from typing import Dict, Any

# Auth components
from auth import TOTPAuthenticator, SessionManager

# HomeAssistant components
from homeassistant.client import HomeAssistantClient
from homeassistant.filters import EntityFilter, EntityMapper

# Command components
from commands import CommandHandler

# Server components
from server.telnet import TelnetServer


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/packetqth.log')
    ]
)

logger = logging.getLogger(__name__)


class PacketQTH:
    """
    Main PacketQTH application.

    Coordinates all components:
        - TOTP authentication
        - HomeAssistant API client
        - Entity filtering and mapping
        - Command handling
        - Telnet server
    """

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize application.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.server: TelnetServer = None
        self.ha_client: HomeAssistantClient = None
        self.entity_mapper: EntityMapper = None
        self.command_handler: CommandHandler = None
        self.running = False

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary
        """
        logger.info(f"Loading configuration from {self.config_path}")

        if not Path(self.config_path).exists():
            logger.error(f"Configuration file not found: {self.config_path}")
            sys.exit(1)

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            logger.info("Configuration loaded successfully")
            return config

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            sys.exit(1)

    def load_users(self, users_path: str = 'users.yaml') -> Dict[str, str]:
        """
        Load user TOTP secrets from YAML file.

        Args:
            users_path: Path to users file

        Returns:
            Dictionary of {callsign: totp_secret}
        """
        logger.info(f"Loading users from {users_path}")

        if not Path(users_path).exists():
            logger.error(f"Users file not found: {users_path}")
            sys.exit(1)

        try:
            with open(users_path, 'r') as f:
                data = yaml.safe_load(f)

            users = data.get('users', {})
            logger.info(f"Loaded {len(users)} users")
            return users

        except Exception as e:
            logger.error(f"Error loading users: {e}")
            sys.exit(1)

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing PacketQTH")

        # Load configuration
        self.config = self.load_config()

        # Initialize authenticator
        users_file = self.config.get('auth', {}).get('users_file', 'users.yaml')
        authenticator = TOTPAuthenticator(users_file)
        session_manager = SessionManager()
        logger.info("Authentication components initialized")

        # Initialize HomeAssistant client
        ha_config = self.config.get('homeassistant', {})
        ha_url = ha_config.get('url')
        ha_token = os.environ.get('HA_TOKEN') or ha_config.get('token')

        if not ha_url or not ha_token:
            logger.error("HomeAssistant URL and token required")
            sys.exit(1)

        self.ha_client = HomeAssistantClient(
            url=ha_url,
            token=ha_token,
            cache_ttl=ha_config.get('cache_ttl', 60)
        )
        logger.info(f"HomeAssistant client initialized: {ha_url}")

        # Test connection and load entities
        try:
            entities = await self.ha_client.get_states(use_cache=False)
            logger.info(f"Connected to HomeAssistant: {len(entities)} entities found")

        except Exception as e:
            logger.error(f"Failed to connect to HomeAssistant: {e}")
            sys.exit(1)

        # Initialize entity filter and mapper
        filter_config = ha_config.get('entity_filter', {})

        entity_filter = EntityFilter(
            included_domains=filter_config.get('include_domains'),
            excluded_entities=filter_config.get('exclude_entities'),
        )

        # Filter entities
        filtered_entities = entity_filter.filter_entities(entities)
        logger.info(f"Filtered to {len(filtered_entities)} entities")

        # Create entity mapper
        self.entity_mapper = EntityMapper()
        self.entity_mapper.add_entities(filtered_entities)
        logger.info("Entity mapper initialized")

        # Initialize command handler
        self.command_handler = CommandHandler(
            ha_client=self.ha_client,
            entity_mapper=self.entity_mapper,
            page_size=self.config.get('display', {}).get('page_size', 10)
        )
        logger.info("Command handler initialized")

        # Initialize telnet server
        telnet_config = self.config.get('telnet', {})
        security_config = self.config.get('security', {})

        self.server = TelnetServer(
            host=telnet_config.get('host', '0.0.0.0'),
            port=telnet_config.get('port', 8023),
            authenticator=authenticator,
            session_manager=session_manager,
            command_handler=self.command_handler,
            max_connections=telnet_config.get('max_connections', 10),
            timeout_seconds=telnet_config.get('timeout_seconds', 300),
            max_auth_attempts=security_config.get('max_auth_attempts', 3),
            welcome_banner=security_config.get('welcome_banner', 'PacketQTH'),
            bpq_mode=telnet_config.get('bpq_mode', True),
            ip_safelist=security_config.get('ip_safelist', [])
        )
        logger.info(f"Telnet server initialized: {telnet_config.get('host')}:{telnet_config.get('port')}")

    async def start(self):
        """Start the application."""
        logger.info("Starting PacketQTH")

        # Initialize components
        await self.initialize()

        # Start telnet server
        await self.server.start()

        self.running = True
        logger.info("PacketQTH started successfully")

        # Show startup info
        telnet_config = self.config.get('telnet', {})
        logger.info("=" * 60)
        logger.info(f"PacketQTH is running")
        logger.info(f"Telnet: {telnet_config.get('host')}:{telnet_config.get('port')}")
        logger.info(f"BPQ Mode: {telnet_config.get('bpq_mode', True)}")
        logger.info(f"Max Connections: {telnet_config.get('max_connections', 10)}")
        logger.info(f"Timeout: {telnet_config.get('timeout_seconds', 300)}s")
        logger.info(f"Entities: {len(self.entity_mapper.get_all_entities())}")
        logger.info("=" * 60)

    async def stop(self):
        """Stop the application."""
        logger.info("Stopping PacketQTH")

        self.running = False

        # Stop telnet server
        if self.server:
            await self.server.stop()

        # Close HomeAssistant client
        if self.ha_client:
            await self.ha_client.close()

        logger.info("PacketQTH stopped")

    async def run(self):
        """Run the application until stopped."""
        await self.start()

        # Wait for server to finish
        await self.server.wait_closed()

        await self.stop()


async def main():
    """Main entry point."""
    # Create application
    app = PacketQTH()

    # Setup signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(app.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        await app.stop()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await app.stop()
        sys.exit(1)


if __name__ == '__main__':
    logger.info("PacketQTH - HomeAssistant for Packet Radio")
    logger.info("=" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
