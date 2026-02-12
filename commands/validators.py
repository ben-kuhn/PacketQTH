"""
PacketQTH Command Validators

Validate commands against entity state and capabilities.
"""

from typing import Optional, Dict, Any, List
from .models import Command, CommandType


class ValidationError(Exception):
    """Exception raised when command validation fails."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            suggestion: Optional suggestion for user
        """
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)

    def __str__(self) -> str:
        """String representation."""
        if self.suggestion:
            return f"{self.message}\n{self.suggestion}"
        return self.message


class CommandValidator:
    """
    Validate commands against entity state.

    Checks:
        - Device IDs exist
        - Operations are valid for entity types
        - Values are appropriate for entity attributes
    """

    # Entities that support turn_on/turn_off
    SWITCHABLE_DOMAINS = {
        'light',
        'switch',
        'fan',
        'automation',
        'scene',
        'script'
    }

    # Entities that support set value
    SETTABLE_DOMAINS = {
        'light',      # brightness
        'cover',      # position
        'climate',    # temperature
        'fan',        # speed
        'input_number',
        'number'
    }

    # Attribute names for settable values
    SETTABLE_ATTRIBUTES = {
        'light': 'brightness',
        'cover': 'current_position',
        'climate': 'temperature',
        'fan': 'percentage',
        'input_number': 'state',
        'number': 'state'
    }

    def __init__(self, entity_mapper=None):
        """
        Initialize validator.

        Args:
            entity_mapper: EntityMapper instance (optional)
        """
        self.entity_mapper = entity_mapper

    def validate(self, command: Command) -> None:
        """
        Validate command.

        Args:
            command: Command to validate

        Raises:
            ValidationError: If command is invalid
        """
        # Skip validation for commands that don't need entity context
        if command.type in (
            CommandType.LIST,
            CommandType.AUTOMATIONS,
            CommandType.HELP,
            CommandType.QUIT,
            CommandType.REFRESH,
            CommandType.UNKNOWN
        ):
            return

        # Commands that require entity mapper
        if not self.entity_mapper:
            # Can't validate without entity mapper
            return

        # Get entity if command has device_id
        entity = None
        if command.device_id is not None:
            entity = self.entity_mapper.get_by_id(command.device_id)
            if not entity:
                raise ValidationError(
                    f"Device #{command.device_id} not found",
                    "Use L to list devices"
                )

        # Validate based on command type
        if command.type == CommandType.SHOW:
            self._validate_show(command, entity)
        elif command.type == CommandType.ON:
            self._validate_on(command, entity)
        elif command.type == CommandType.OFF:
            self._validate_off(command, entity)
        elif command.type == CommandType.SET:
            self._validate_set(command, entity)
        elif command.type == CommandType.TRIGGER:
            self._validate_trigger(command, entity)

    def _validate_show(self, command: Command, entity: Dict[str, Any]) -> None:
        """Validate SHOW command."""
        # SHOW works for any entity
        pass

    def _validate_on(self, command: Command, entity: Dict[str, Any]) -> None:
        """Validate ON command."""
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        if domain not in self.SWITCHABLE_DOMAINS:
            entity_type = domain.replace('_', ' ').title()
            raise ValidationError(
                f"{entity_type} cannot be turned on",
                f"Use SET to control this device"
            )

    def _validate_off(self, command: Command, entity: Dict[str, Any]) -> None:
        """Validate OFF command."""
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        if domain not in self.SWITCHABLE_DOMAINS:
            entity_type = domain.replace('_', ' ').title()
            raise ValidationError(
                f"{entity_type} cannot be turned off",
                f"Use SET to control this device"
            )

    def _validate_set(self, command: Command, entity: Dict[str, Any]) -> None:
        """Validate SET command."""
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        # Check if domain supports SET
        if domain not in self.SETTABLE_DOMAINS:
            entity_type = domain.replace('_', ' ').title()
            raise ValidationError(
                f"{entity_type} does not support SET",
                "Use ON/OFF for switches and lights"
            )

        # Validate value range for specific domains
        if command.value is not None:
            self._validate_value_range(domain, command.value, entity)

    def _validate_trigger(self, command: Command, entity: Dict[str, Any]) -> None:
        """Validate TRIGGER command."""
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        if domain != 'automation':
            raise ValidationError(
                f"#{command.device_id} is not an automation",
                "Use A to list automations"
            )

    def _validate_value_range(
        self,
        domain: str,
        value: Any,
        entity: Dict[str, Any]
    ) -> None:
        """
        Validate value is in acceptable range for domain.

        Args:
            domain: Entity domain
            value: Value to validate
            entity: Entity dict

        Raises:
            ValidationError: If value is out of range
        """
        # Convert to numeric if possible
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            # Non-numeric values are allowed for some domains
            return

        # Validate ranges based on domain
        if domain == 'light':
            # Brightness: 0-255 or 0-100 depending on interpretation
            # We'll accept 0-255 and convert in handler
            if not (0 <= numeric_value <= 255):
                raise ValidationError(
                    "Light brightness must be 0-255",
                    "Example: SET 1 128"
                )

        elif domain == 'cover':
            # Position: 0-100
            if not (0 <= numeric_value <= 100):
                raise ValidationError(
                    "Cover position must be 0-100",
                    "0=closed, 100=open"
                )

        elif domain == 'climate':
            # Temperature: reasonable range
            if not (-50 <= numeric_value <= 120):
                raise ValidationError(
                    "Temperature out of range",
                    "Use degrees F or C"
                )

        elif domain == 'fan':
            # Percentage: 0-100
            if not (0 <= numeric_value <= 100):
                raise ValidationError(
                    "Fan speed must be 0-100",
                    "Example: SET 2 75"
                )


def validate_command(command: Command, entity_mapper=None) -> None:
    """
    Validate command (convenience function).

    Args:
        command: Command to validate
        entity_mapper: EntityMapper instance (optional)

    Raises:
        ValidationError: If command is invalid
    """
    validator = CommandValidator(entity_mapper)
    validator.validate(command)
