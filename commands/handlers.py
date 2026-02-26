"""
PacketQTH Command Handlers

Execute parsed and validated commands.
"""

import logging
from typing import List, Optional
from .models import Command, CommandType
from homeassistant.client import HomeAssistantClient
from homeassistant.filters import EntityMapper
from formatting import (
    format_page_with_entities,
    format_entity_line,
    format_entity_detail,
    format_main_menu,
    format_error_message,
    format_success_message,
    format_info_message
)

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    Execute commands against HomeAssistant.

    Handles:
        - Device control (on/off/set)
        - Listing devices and automations
        - Showing device details
        - Triggering automations
        - Help and system commands
    """

    def __init__(
        self,
        ha_client: HomeAssistantClient,
        entity_mapper: EntityMapper,
        page_size: int = 10
    ):
        """
        Initialize handler.

        Args:
            ha_client: HomeAssistant API client
            entity_mapper: Entity mapper with numeric IDs
            page_size: Items per page for lists
        """
        self.ha = ha_client
        self.mapper = entity_mapper
        self.page_size = page_size

    async def handle(self, command: Command) -> List[str]:
        """
        Execute command and return response lines.

        Args:
            command: Parsed and validated command

        Returns:
            List of response lines to send to user
        """
        try:
            if command.type == CommandType.LIST:
                return await self._handle_list(command)
            elif command.type == CommandType.SHOW:
                return await self._handle_show(command)
            elif command.type == CommandType.ON:
                return await self._handle_on(command)
            elif command.type == CommandType.OFF:
                return await self._handle_off(command)
            elif command.type == CommandType.SET:
                return await self._handle_set(command)
            elif command.type == CommandType.AUTOMATIONS:
                return await self._handle_automations(command)
            elif command.type == CommandType.TRIGGER:
                return await self._handle_trigger(command)
            elif command.type == CommandType.HELP:
                return self._handle_help(command)
            elif command.type == CommandType.REFRESH:
                return await self._handle_refresh(command)
            elif command.type == CommandType.QUIT:
                return self._handle_quit(command)
            else:
                return format_error_message("Command not implemented")

        except Exception as e:
            logger.error(f"Error handling command: {e}", exc_info=True)
            return format_error_message(str(e))

    async def _handle_list(self, command: Command) -> List[str]:
        """Handle LIST command."""
        page_num = command.page or 1

        # Get all entities from mapper
        entities = self.mapper.get_all()

        if not entities:
            return format_error_message("No devices found", "Check HA connection")

        # Filter out automations
        devices = [e for e in entities if not e['entity_id'].startswith('automation.')]

        # Format page
        lines, page_info = format_page_with_entities(
            entities=devices,
            entity_formatter_func=format_entity_line,
            page_num=page_num,
            page_size=self.page_size,
            title="DEVICES"
        )

        return lines

    async def _handle_show(self, command: Command) -> List[str]:
        """Handle SHOW command."""
        entity = self.mapper.get_by_id(command.device_id)

        if not entity:
            return format_error_message(
                f"Device #{command.device_id} not found",
                "Use L to list devices"
            )

        # Format detailed view
        lines = format_entity_detail(command.device_id, entity)
        return lines

    async def _handle_on(self, command: Command) -> List[str]:
        """Handle ON command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']

        try:
            await self.ha.turn_on(entity_id)

            # Get friendly name
            name = entity['attributes'].get('friendly_name', entity_id)

            return [format_success_message(f"{name} turned on")]

        except Exception as e:
            logger.error(f"Error turning on {entity_id}: {e}")
            return format_error_message(f"Failed to turn on device", str(e))

    async def _handle_off(self, command: Command) -> List[str]:
        """Handle OFF command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']

        try:
            await self.ha.turn_off(entity_id)

            # Get friendly name
            name = entity['attributes'].get('friendly_name', entity_id)

            return [format_success_message(f"{name} turned off")]

        except Exception as e:
            logger.error(f"Error turning off {entity_id}: {e}")
            return format_error_message(f"Failed to turn off device", str(e))

    async def _handle_set(self, command: Command) -> List[str]:
        """Handle SET command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        try:
            # Handle based on domain
            if domain == 'light':
                # Set brightness (0-255)
                brightness = int(command.value)
                await self.ha.turn_on(entity_id, brightness=brightness)

            elif domain == 'cover':
                # Set position (0-100)
                position = int(command.value)
                await self.ha.call_service(
                    'cover',
                    'set_cover_position',
                    entity_id=entity_id,
                    position=position
                )

            elif domain == 'climate':
                # Set temperature
                temperature = float(command.value)
                await self.ha.call_service(
                    'climate',
                    'set_temperature',
                    entity_id=entity_id,
                    temperature=temperature
                )

            elif domain == 'fan':
                # Set percentage
                percentage = int(command.value)
                await self.ha.call_service(
                    'fan',
                    'set_percentage',
                    entity_id=entity_id,
                    percentage=percentage
                )

            elif domain in ('input_number', 'number'):
                # Set value
                value = float(command.value)
                await self.ha.call_service(
                    domain,
                    'set_value',
                    entity_id=entity_id,
                    value=value
                )

            else:
                return format_error_message(
                    f"SET not supported for {domain}",
                    "Use ON/OFF instead"
                )

            # Get friendly name
            name = entity['attributes'].get('friendly_name', entity_id)

            return [format_success_message(f"{name} set to {command.value}")]

        except Exception as e:
            logger.error(f"Error setting {entity_id}: {e}")
            return format_error_message(f"Failed to set device", str(e))

    async def _handle_automations(self, command: Command) -> List[str]:
        """Handle AUTOMATIONS command."""
        page_num = command.page or 1

        # Get all entities from mapper
        entities = self.mapper.get_all()

        # Filter for automations only
        automations = [e for e in entities if e['entity_id'].startswith('automation.')]

        if not automations:
            return format_error_message("No automations found")

        # Format page
        lines, page_info = format_page_with_entities(
            entities=automations,
            entity_formatter_func=format_entity_line,
            page_num=page_num,
            page_size=self.page_size,
            title="AUTOMATIONS"
        )

        return lines

    async def _handle_trigger(self, command: Command) -> List[str]:
        """Handle TRIGGER command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']

        try:
            await self.ha.trigger_automation(entity_id)

            # Get friendly name
            name = entity['attributes'].get('friendly_name', entity_id)

            return [format_success_message(f"{name} triggered")]

        except Exception as e:
            logger.error(f"Error triggering {entity_id}: {e}")
            return format_error_message(f"Failed to trigger automation", str(e))

    def _handle_help(self, command: Command) -> List[str]:
        """Handle HELP command."""
        return format_main_menu()

    async def _handle_refresh(self, command: Command) -> List[str]:
        """Handle REFRESH command."""
        try:
            # Force cache refresh
            entities = await self.ha.get_states(use_cache=False)

            # Update entity mapper
            self.mapper.clear()
            self.mapper.add_entities(entities)

            return [format_success_message(f"Refreshed {len(entities)} entities")]

        except Exception as e:
            logger.error(f"Error refreshing: {e}")
            return format_error_message("Failed to refresh", str(e))

    def _handle_quit(self, command: Command) -> List[str]:
        """Handle QUIT command."""
        return ["73!"]
