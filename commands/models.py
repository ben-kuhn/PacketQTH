"""
PacketQTH Command Models

Data structures for parsed commands.
"""

from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class CommandType(Enum):
    """Command types supported by PacketQTH."""
    LIST = "list"              # List devices
    SHOW = "show"              # Show device details
    ON = "on"                  # Turn on device
    OFF = "off"                # Turn off device
    SET = "set"                # Set device value
    AUTOMATIONS = "automations"  # List automations
    TRIGGER = "trigger"        # Trigger automation
    HELP = "help"              # Show help
    QUIT = "quit"              # Quit session
    REFRESH = "refresh"        # Refresh cache
    UNKNOWN = "unknown"        # Unknown command


@dataclass
class Command:
    """
    Represents a parsed command.

    Attributes:
        type: Command type
        raw_input: Original input string
        device_id: Numeric device ID (for device commands)
        value: Value parameter (for SET command)
        page: Page number (for list commands)
        error: Error message if parsing failed
    """
    type: CommandType
    raw_input: str
    device_id: Optional[int] = None
    value: Optional[Any] = None
    page: Optional[int] = None
    error: Optional[str] = None

    def is_valid(self) -> bool:
        """Check if command is valid (no parsing errors)."""
        return self.error is None

    def requires_device_id(self) -> bool:
        """Check if command requires a device ID."""
        return self.type in (
            CommandType.SHOW,
            CommandType.ON,
            CommandType.OFF,
            CommandType.SET
        )

    def requires_value(self) -> bool:
        """Check if command requires a value parameter."""
        return self.type == CommandType.SET

    def supports_pagination(self) -> bool:
        """Check if command supports pagination."""
        return self.type in (CommandType.LIST, CommandType.AUTOMATIONS)

    def is_write_operation(self) -> bool:
        """
        Check if command is a write operation that modifies state.

        Write operations require fresh TOTP verification for security.

        Returns:
            True if command modifies HomeAssistant state, False otherwise
        """
        return self.type in (
            CommandType.ON,
            CommandType.OFF,
            CommandType.SET,
            CommandType.TRIGGER
        )

    def __str__(self) -> str:
        """String representation of command."""
        parts = [f"Command({self.type.value}"]

        if self.device_id is not None:
            parts.append(f"device_id={self.device_id}")

        if self.value is not None:
            parts.append(f"value={self.value}")

        if self.page is not None:
            parts.append(f"page={self.page}")

        if self.error:
            parts.append(f"error='{self.error}'")

        return ", ".join(parts) + ")"


class ParseError(Exception):
    """Exception raised when command parsing fails."""

    def __init__(self, message: str, suggestion: Optional[str] = None):
        """
        Initialize parse error.

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
