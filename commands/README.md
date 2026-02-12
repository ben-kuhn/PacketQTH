# PacketQTH Command Module

Command parsing and validation for text-based HomeAssistant control over packet radio.

## Overview

This module provides command parsing and validation for PacketQTH. Commands are designed to be extremely concise for 1200 baud packet radio transmission - most commands are 1-2 characters with minimal parameters.

**Key Features:**

- ✅ **Ultra-compact commands** - Single letter shortcuts (L, S, ON, OFF, etc.)
- ✅ **Flexible parsing** - Uppercase/lowercase, aliases
- ✅ **Strong validation** - Check entity existence and capabilities
- ✅ **Clear error messages** - Helpful suggestions for users
- ✅ **Type safety** - Strongly typed Command objects
- ✅ **Test coverage** - Comprehensive test tool included

## Command Reference

### Device Commands

```
L [page]         List devices (page optional)
S <id>           Show device details
ON <id>          Turn on device
OFF <id>         Turn off device
SET <id> <val>   Set device value
```

### Automation Commands

```
A [page]         List automations (page optional)
T <id>           Trigger automation
```

### System Commands

```
H                Help menu
R                Refresh entity cache
Q                Quit session
```

### Command Aliases

Most commands support multiple forms:

- `L`, `LIST`
- `S`, `SHOW`
- `A`, `AUTO`, `AUTOMATIONS`
- `T`, `TRIGGER`
- `H`, `HELP`, `?`
- `Q`, `QUIT`, `EXIT`, `BYE`
- `R`, `REFRESH`

## Modules

### models.py

Core data structures.

**CommandType Enum:**
- `LIST` - List devices
- `SHOW` - Show device details
- `ON` - Turn on device
- `OFF` - Turn off device
- `SET` - Set device value
- `AUTOMATIONS` - List automations
- `TRIGGER` - Trigger automation
- `HELP` - Show help
- `QUIT` - Quit session
- `REFRESH` - Refresh cache
- `UNKNOWN` - Unknown command

**Command Dataclass:**
```python
@dataclass
class Command:
    type: CommandType
    raw_input: str
    device_id: Optional[int] = None
    value: Optional[Any] = None
    page: Optional[int] = None
    error: Optional[str] = None
```

**Helper Methods:**
- `is_valid()` - Check if command parsed successfully
- `requires_device_id()` - Check if command needs device ID
- `requires_value()` - Check if command needs value parameter
- `supports_pagination()` - Check if command supports pages

### parser.py

Parse text input into Command objects.

**CommandParser Class:**
- Normalizes input (strip, uppercase)
- Splits into tokens
- Identifies command type
- Extracts parameters
- Validates parameter types
- Returns Command with error on failure

**Key Method:**
```python
def parse(self, input_text: str) -> Command
```

**Convenience Function:**
```python
def parse_command(input_text: str) -> Command
```

### validators.py

Validate commands against entity state.

**CommandValidator Class:**
- Checks device IDs exist
- Validates operations for entity types
- Validates value ranges
- Provides helpful error messages

**Validation Rules:**
- Switchable domains: light, switch, fan, automation, scene, script
- Settable domains: light, cover, climate, fan, input_number, number
- Value ranges: brightness (0-255), cover (0-100), fan (0-100)

**Key Method:**
```python
def validate(self, command: Command) -> None
```

**Convenience Function:**
```python
def validate_command(command: Command, entity_mapper=None) -> None
```

## Usage

### Basic Parsing

```python
from commands import parse_command

# Parse a command
command = parse_command("ON 1")

print(command.type)          # CommandType.ON
print(command.device_id)     # 1
print(command.is_valid())    # True
```

### With Error Handling

```python
from commands import parse_command

command = parse_command("INVALID")

if not command.is_valid():
    print(f"Error: {command.error}")
    # Error: Unknown command: INVALID
```

### With Validation

```python
from commands import parse_command, validate_command, ValidationError
from homeassistant.filters import EntityMapper

# Create entity mapper
mapper = EntityMapper()
mapper.add_entities(entities)

# Parse and validate
command = parse_command("ON 1")

try:
    validate_command(command, mapper)
    # Command is valid - execute it
except ValidationError as e:
    print(f"Validation error: {e.message}")
    if e.suggestion:
        print(f"Suggestion: {e.suggestion}")
```

### Complete Example

```python
from commands import parse_command, validate_command, ValidationError
from homeassistant.filters import EntityMapper

async def handle_user_input(input_text: str, mapper: EntityMapper):
    """Handle user command input."""

    # Parse command
    command = parse_command(input_text)

    # Check parsing
    if not command.is_valid():
        return f"ERR: {command.error}"

    # Validate command
    try:
        validate_command(command, mapper)
    except ValidationError as e:
        lines = [f"ERR: {e.message}"]
        if e.suggestion:
            lines.append(e.suggestion)
        return "\n".join(lines)

    # Execute command
    if command.type == CommandType.ON:
        entity = mapper.get_by_id(command.device_id)
        # Turn on entity...
        return f"OK: Turned on {entity['entity_id']}"

    # ... handle other command types
```

## API Reference

### Command Model

#### `Command.is_valid() -> bool`

Check if command parsed successfully (no error).

```python
command = parse_command("L")
if command.is_valid():
    # Process command
```

#### `Command.requires_device_id() -> bool`

Check if command requires a device ID.

```python
if command.requires_device_id() and command.device_id is None:
    # Error - missing device ID
```

#### `Command.requires_value() -> bool`

Check if command requires a value parameter.

```python
if command.requires_value() and command.value is None:
    # Error - missing value
```

#### `Command.supports_pagination() -> bool`

Check if command supports pagination.

```python
if command.supports_pagination():
    page = command.page or 1
```

### Parser

#### `parse_command(input_text: str) -> Command`

Parse command text into Command object.

```python
command = parse_command("ON 1")
```

#### `CommandParser.parse(input_text: str) -> Command`

Parse command (class method).

```python
parser = CommandParser()
command = parser.parse("SET 1 75")
```

### Validator

#### `validate_command(command: Command, entity_mapper=None) -> None`

Validate command against entity state.

```python
try:
    validate_command(command, mapper)
except ValidationError as e:
    print(e.message)
    print(e.suggestion)
```

#### `CommandValidator.validate(command: Command) -> None`

Validate command (class method).

```python
validator = CommandValidator(mapper)
validator.validate(command)
```

## Error Handling

### Parse Errors

Parse errors are stored in `Command.error`:

```python
command = parse_command("S")  # Missing device ID

print(command.error)
# "SHOW requires device ID"

print(command.is_valid())
# False
```

### Validation Errors

Validation errors raise `ValidationError`:

```python
try:
    validate_command(command, mapper)
except ValidationError as e:
    print(e.message)    # "Device #99 not found"
    print(e.suggestion) # "Use L to list devices"
```

## Command Examples

### LIST Command

```python
parse_command("L")       # List page 1
parse_command("L 2")     # List page 2
parse_command("LIST")    # List page 1
parse_command("list 3")  # List page 3 (case insensitive)
```

### SHOW Command

```python
parse_command("S 1")     # Show device #1
parse_command("SHOW 5")  # Show device #5
```

### ON/OFF Commands

```python
parse_command("ON 1")    # Turn on device #1
parse_command("OFF 2")   # Turn off device #2
parse_command("on 3")    # Turn on device #3 (case insensitive)
```

### SET Command

```python
parse_command("SET 1 75")     # Set device #1 to 75
parse_command("SET 2 100")    # Set device #2 to 100
parse_command("set 3 50.5")   # Set device #3 to 50.5 (float)
```

### AUTOMATIONS Command

```python
parse_command("A")       # List automations page 1
parse_command("A 2")     # List automations page 2
parse_command("AUTO")    # List automations (alias)
```

### TRIGGER Command

```python
parse_command("T 1")     # Trigger automation #1
parse_command("TRIGGER 5") # Trigger automation #5
```

### System Commands

```python
parse_command("H")       # Help
parse_command("?")       # Help (alias)
parse_command("R")       # Refresh
parse_command("Q")       # Quit
parse_command("EXIT")    # Quit (alias)
```

## Validation Rules

### Switchable Entities

Can use ON/OFF commands:
- light
- switch
- fan
- automation
- scene
- script

### Settable Entities

Can use SET command:
- light (brightness: 0-255)
- cover (position: 0-100)
- climate (temperature: -50 to 120)
- fan (percentage: 0-100)
- input_number
- number

### Value Ranges

| Domain | Attribute | Range | Notes |
|--------|-----------|-------|-------|
| light | brightness | 0-255 | Full brightness range |
| cover | position | 0-100 | 0=closed, 100=open |
| climate | temperature | -50 to 120 | Reasonable range |
| fan | percentage | 0-100 | Speed percentage |

## Testing

### Run Tests

```bash
# All tests
python tools/test_commands.py

# Specific test
python tools/test_commands.py --test parsing
python tools/test_commands.py --test errors
python tools/test_commands.py --test validation

# Interactive mode
python tools/test_commands.py --interactive
```

### Example Test Output

```
Basic Parsing Tests
============================================================

✓ List devices (page 1)
  Input:   'L'
  Parsed:  Command(list)

✓ List devices page 2
  Input:   'L 2'
  Parsed:  Command(list, page=2)

✓ Turn on device #1
  Input:   'ON 1'
  Parsed:  Command(on, device_id=1)

✓ Set device #1 to 75
  Input:   'SET 1 75'
  Parsed:  Command(set, device_id=1, value=75)
```

### Interactive Testing

```bash
$ python tools/test_commands.py -i

Interactive Command Parser Test
============================================================
Enter commands to parse (Q to quit)

Available test entities:
  1. light.kitchen               (Kitchen Light)
  2. switch.garage               (Garage Door)
  3. sensor.temperature          (Living Room Temp)
  4. cover.blinds                (Window Blinds)
  5. automation.good_night       (Good Night Routine)

> ON 1
Parsed: Command(on, device_id=1)
Validation: ✓ Valid

> SET 3 100
Parsed: Command(set, device_id=3, value=100)
Validation Error: Sensor does not support SET
Use ON/OFF for switches and lights

> Q
Parsed: Command(quit)
Validation: ✓ Valid
73!
```

## Integration Example

### Complete Session Handler

```python
from commands import parse_command, validate_command, ValidationError, CommandType
from homeassistant.filters import EntityMapper
from formatting import format_error_message, format_success_message

class CommandHandler:
    """Handle user commands in a session."""

    def __init__(self, ha_client, entity_mapper: EntityMapper):
        self.ha = ha_client
        self.mapper = entity_mapper

    async def handle(self, input_text: str) -> str:
        """
        Handle user command.

        Args:
            input_text: Raw user input

        Returns:
            Response text to send to user
        """
        # Parse command
        command = parse_command(input_text)

        # Check parsing
        if not command.is_valid():
            return "\n".join(format_error_message(command.error))

        # Validate command
        try:
            validate_command(command, self.mapper)
        except ValidationError as e:
            return "\n".join(format_error_message(e.message, e.suggestion))

        # Execute command
        try:
            if command.type == CommandType.ON:
                return await self._handle_on(command)
            elif command.type == CommandType.OFF:
                return await self._handle_off(command)
            elif command.type == CommandType.SET:
                return await self._handle_set(command)
            # ... other command types
        except Exception as e:
            return "\n".join(format_error_message(str(e)))

    async def _handle_on(self, command: Command) -> str:
        """Handle ON command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']

        await self.ha.turn_on(entity_id)

        name = entity['attributes'].get('friendly_name', entity_id)
        return format_success_message(f"{name} turned on")

    async def _handle_off(self, command: Command) -> str:
        """Handle OFF command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']

        await self.ha.turn_off(entity_id)

        name = entity['attributes'].get('friendly_name', entity_id)
        return format_success_message(f"{name} turned off")

    async def _handle_set(self, command: Command) -> str:
        """Handle SET command."""
        entity = self.mapper.get_by_id(command.device_id)
        entity_id = entity['entity_id']
        domain = entity_id.split('.')[0]

        if domain == 'light':
            await self.ha.turn_on(entity_id, brightness=int(command.value))
        elif domain == 'cover':
            await self.ha.call_service('cover', 'set_cover_position',
                                      entity_id=entity_id,
                                      position=int(command.value))
        # ... other domains

        name = entity['attributes'].get('friendly_name', entity_id)
        return format_success_message(f"{name} set to {command.value}")
```

## Design Principles

### Bandwidth Optimization

Commands are designed for 1200 baud transmission:

1. **Single letter commands** - L, S, A, T, H, Q, R
2. **Minimal parameters** - Only what's required
3. **Numeric IDs** - "1" instead of "light.kitchen"
4. **Short responses** - Concise error/success messages

### User Experience

1. **Case insensitive** - "L" or "l" both work
2. **Flexible aliases** - "H", "HELP", "?" all work
3. **Clear errors** - Helpful suggestions for corrections
4. **Predictable parsing** - Consistent token structure

### Type Safety

1. **Strongly typed** - Command dataclass with type hints
2. **Enum command types** - No magic strings
3. **Validation separation** - Parse vs validate phases
4. **Error objects** - Structured error information

## Best Practices

### Command Parsing

**Always check validity:**
```python
command = parse_command(input_text)
if not command.is_valid():
    # Handle parse error
    return command.error
```

**Validate before execution:**
```python
try:
    validate_command(command, mapper)
    # Execute command
except ValidationError as e:
    # Handle validation error
```

### Error Messages

**Be concise but helpful:**
```python
# Good
format_error_message("Device not found", "Use L to list")

# Less good
format_error_message("The device you requested could not be located")
```

### Command Execution

**Use type-safe checks:**
```python
# Good
if command.type == CommandType.ON:
    # Handle ON

# Less good
if command.type.value == "on":
    # String comparison
```

## Further Reading

- [PacketQTH Architecture](../ARCHITECTURE.md)
- [Formatting Module](../formatting/README.md)
- [HomeAssistant Module](../homeassistant/README.md)
- [Server Module](../server/README.md)

---

**73!** 📡 Keep commands short and sweet at 1200 baud!
