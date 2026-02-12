"""
PacketQTH Command Parser

Parse user input into structured Command objects.
"""

import re
from typing import Optional, List
from .models import Command, CommandType, ParseError


class CommandParser:
    """
    Parse text commands into Command objects.

    Supports commands:
        L [page]         - List devices
        S <id>           - Show device
        ON <id>          - Turn on device
        OFF <id>         - Turn off device
        SET <id> <val>   - Set device value
        A [page]         - List automations
        T <id>           - Trigger automation
        H                - Help
        Q                - Quit
        R                - Refresh cache
    """

    # Command aliases
    COMMAND_MAP = {
        'L': CommandType.LIST,
        'LIST': CommandType.LIST,
        'S': CommandType.SHOW,
        'SHOW': CommandType.SHOW,
        'ON': CommandType.ON,
        'OFF': CommandType.OFF,
        'SET': CommandType.SET,
        'A': CommandType.AUTOMATIONS,
        'AUTO': CommandType.AUTOMATIONS,
        'AUTOMATIONS': CommandType.AUTOMATIONS,
        'T': CommandType.TRIGGER,
        'TRIGGER': CommandType.TRIGGER,
        'H': CommandType.HELP,
        'HELP': CommandType.HELP,
        '?': CommandType.HELP,
        'Q': CommandType.QUIT,
        'QUIT': CommandType.QUIT,
        'EXIT': CommandType.QUIT,
        'BYE': CommandType.QUIT,
        'R': CommandType.REFRESH,
        'REFRESH': CommandType.REFRESH,
    }

    def __init__(self):
        """Initialize parser."""
        pass

    def parse(self, input_text: str) -> Command:
        """
        Parse input text into Command object.

        Args:
            input_text: Raw user input

        Returns:
            Command object (may have error set if parsing failed)
        """
        # Store original input
        raw_input = input_text

        # Normalize: strip whitespace and convert to uppercase
        normalized = input_text.strip().upper()

        # Handle empty input
        if not normalized:
            return Command(
                type=CommandType.UNKNOWN,
                raw_input=raw_input,
                error="Empty command"
            )

        # Split into tokens
        tokens = normalized.split()

        # First token is the command
        cmd_token = tokens[0]

        # Look up command type
        cmd_type = self.COMMAND_MAP.get(cmd_token)

        if cmd_type is None:
            return Command(
                type=CommandType.UNKNOWN,
                raw_input=raw_input,
                error=f"Unknown command: {cmd_token}"
            )

        # Parse based on command type
        try:
            if cmd_type == CommandType.LIST:
                return self._parse_list(tokens, raw_input)
            elif cmd_type == CommandType.SHOW:
                return self._parse_show(tokens, raw_input)
            elif cmd_type == CommandType.ON:
                return self._parse_on(tokens, raw_input)
            elif cmd_type == CommandType.OFF:
                return self._parse_off(tokens, raw_input)
            elif cmd_type == CommandType.SET:
                return self._parse_set(tokens, raw_input)
            elif cmd_type == CommandType.AUTOMATIONS:
                return self._parse_automations(tokens, raw_input)
            elif cmd_type == CommandType.TRIGGER:
                return self._parse_trigger(tokens, raw_input)
            elif cmd_type == CommandType.HELP:
                return self._parse_help(tokens, raw_input)
            elif cmd_type == CommandType.QUIT:
                return self._parse_quit(tokens, raw_input)
            elif cmd_type == CommandType.REFRESH:
                return self._parse_refresh(tokens, raw_input)
            else:
                return Command(
                    type=CommandType.UNKNOWN,
                    raw_input=raw_input,
                    error="Unhandled command type"
                )
        except ParseError as e:
            return Command(
                type=cmd_type,
                raw_input=raw_input,
                error=str(e)
            )

    def _parse_list(self, tokens: List[str], raw_input: str) -> Command:
        """Parse LIST command: L [page]"""
        page = None

        if len(tokens) > 1:
            page = self._parse_int(tokens[1], "page number")
            if page < 1:
                raise ParseError("Page number must be >= 1")

        return Command(
            type=CommandType.LIST,
            raw_input=raw_input,
            page=page
        )

    def _parse_show(self, tokens: List[str], raw_input: str) -> Command:
        """Parse SHOW command: S <id>"""
        if len(tokens) < 2:
            raise ParseError("SHOW requires device ID", "Usage: S <id>")

        device_id = self._parse_int(tokens[1], "device ID")

        if device_id < 1:
            raise ParseError("Device ID must be >= 1")

        return Command(
            type=CommandType.SHOW,
            raw_input=raw_input,
            device_id=device_id
        )

    def _parse_on(self, tokens: List[str], raw_input: str) -> Command:
        """Parse ON command: ON <id>"""
        if len(tokens) < 2:
            raise ParseError("ON requires device ID", "Usage: ON <id>")

        device_id = self._parse_int(tokens[1], "device ID")

        if device_id < 1:
            raise ParseError("Device ID must be >= 1")

        return Command(
            type=CommandType.ON,
            raw_input=raw_input,
            device_id=device_id
        )

    def _parse_off(self, tokens: List[str], raw_input: str) -> Command:
        """Parse OFF command: OFF <id>"""
        if len(tokens) < 2:
            raise ParseError("OFF requires device ID", "Usage: OFF <id>")

        device_id = self._parse_int(tokens[1], "device ID")

        if device_id < 1:
            raise ParseError("Device ID must be >= 1")

        return Command(
            type=CommandType.OFF,
            raw_input=raw_input,
            device_id=device_id
        )

    def _parse_set(self, tokens: List[str], raw_input: str) -> Command:
        """Parse SET command: SET <id> <value>"""
        if len(tokens) < 3:
            raise ParseError(
                "SET requires device ID and value",
                "Usage: SET <id> <value>"
            )

        device_id = self._parse_int(tokens[1], "device ID")

        if device_id < 1:
            raise ParseError("Device ID must be >= 1")

        # Try to parse value as number, but allow strings
        value_str = tokens[2]
        try:
            # Try int first
            value = int(value_str)
        except ValueError:
            try:
                # Try float
                value = float(value_str)
            except ValueError:
                # Keep as string
                value = value_str

        return Command(
            type=CommandType.SET,
            raw_input=raw_input,
            device_id=device_id,
            value=value
        )

    def _parse_automations(self, tokens: List[str], raw_input: str) -> Command:
        """Parse AUTOMATIONS command: A [page]"""
        page = None

        if len(tokens) > 1:
            page = self._parse_int(tokens[1], "page number")
            if page < 1:
                raise ParseError("Page number must be >= 1")

        return Command(
            type=CommandType.AUTOMATIONS,
            raw_input=raw_input,
            page=page
        )

    def _parse_trigger(self, tokens: List[str], raw_input: str) -> Command:
        """Parse TRIGGER command: T <id>"""
        if len(tokens) < 2:
            raise ParseError(
                "TRIGGER requires automation ID",
                "Usage: T <id>"
            )

        device_id = self._parse_int(tokens[1], "automation ID")

        if device_id < 1:
            raise ParseError("Automation ID must be >= 1")

        return Command(
            type=CommandType.TRIGGER,
            raw_input=raw_input,
            device_id=device_id
        )

    def _parse_help(self, tokens: List[str], raw_input: str) -> Command:
        """Parse HELP command: H"""
        return Command(
            type=CommandType.HELP,
            raw_input=raw_input
        )

    def _parse_quit(self, tokens: List[str], raw_input: str) -> Command:
        """Parse QUIT command: Q"""
        return Command(
            type=CommandType.QUIT,
            raw_input=raw_input
        )

    def _parse_refresh(self, tokens: List[str], raw_input: str) -> Command:
        """Parse REFRESH command: R"""
        return Command(
            type=CommandType.REFRESH,
            raw_input=raw_input
        )

    def _parse_int(self, value: str, field_name: str) -> int:
        """
        Parse integer value.

        Args:
            value: String value to parse
            field_name: Name of field (for error messages)

        Returns:
            Parsed integer

        Raises:
            ParseError: If value is not a valid integer
        """
        try:
            return int(value)
        except ValueError:
            raise ParseError(f"Invalid {field_name}: {value}")


def parse_command(input_text: str) -> Command:
    """
    Parse command text (convenience function).

    Args:
        input_text: Raw user input

    Returns:
        Command object
    """
    parser = CommandParser()
    return parser.parse(input_text)
