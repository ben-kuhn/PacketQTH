# PacketQTH Formatting Module

Text formatting utilities optimized for minimal bandwidth display over 1200 baud packet radio.

## Overview

This module provides compact, bandwidth-optimized text formatting for PacketQTH. Every byte counts at 1200 baud (~120 bytes/second), so all output is designed to be as concise as possible while remaining readable.

**Key Features:**

- ✅ **Ultra-compact entity display** - 2-character abbreviations
- ✅ **Efficient state formatting** - `[ON]`, `[--]`, `72F`
- ✅ **Smart pagination** - Configurable page sizes
- ✅ **Bandwidth calculation** - Estimate transmission times
- ✅ **Help menus** - Concise command reference
- ✅ **Consistent formatting** - Predictable output structure

## Modules

### entities.py

Format HomeAssistant entities compactly.

**Entity Abbreviations:**
- `LT` - Light
- `SW` - Switch
- `SN` - Sensor
- `BL` - Blind/Cover
- `AU` - Automation
- `SC` - Scene
- `CL` - Climate
- `FN` - Fan
- `LK` - Lock

**Example Output:**
```
DEVICES (pg 1/1)
1.LT Kitchen    [ON]
2.SW Garage     [--]
3.SN Temp       72F
4.BL Blinds     75%
```

### pagination.py

Handle pagination for large lists.

**Features:**
- Configurable page size
- Page indicators: `(pg 1/3)`
- Navigation: `N P:`
- Automatic page calculation

### help.py

Format help menus and messages.

**Types:**
- Main menu
- Command help
- Error messages
- Success messages
- Status lines

## Usage

### Basic Entity Formatting

```python
from formatting import format_entity_line

entity = {
    'entity_id': 'light.kitchen',
    'state': 'on',
    'attributes': {'friendly_name': 'Kitchen Light'}
}

line = format_entity_line(1, entity)
# Output: "1.LT Kitchen    [ON]"
```

### Entity List with Pagination

```python
from formatting import format_page_with_entities, format_entity_line

lines, page_info = format_page_with_entities(
    entities=my_entities,
    entity_formatter_func=format_entity_line,
    page_num=1,
    page_size=10,
    title="DEVICES"
)

for line in lines:
    print(line)

# Output:
# DEVICES (pg 1/2)
# 1.LT Kitchen    [ON]
# 2.SW Garage     [--]
# ...
# N:
```

### Help Menu

```python
from formatting import format_main_menu

menu = format_main_menu()
for line in menu:
    print(line)

# Output:
# COMMANDS
# L [pg]    List devices
# S <id>    Show device
# ...
```

### Error Messages

```python
from formatting import format_error_message, format_success_message

# Error
error = format_error_message('Device not found', 'Use L to list')
# Returns: ['ERR: Device not found', 'Use L to list']

# Success
success = format_success_message('Light turned on')
# Returns: 'OK: Light turned on'
```

## API Reference

### Entity Formatting

#### `get_entity_abbrev(entity_id: str) -> str`

Get 2-character abbreviation for entity type.

```python
abbrev = get_entity_abbrev('light.kitchen')  # 'LT'
```

#### `format_state(state: str, attributes: dict) -> str`

Format entity state compactly (max 6 chars).

```python
format_state('on', {})                                    # '[ON]'
format_state('72', {'unit_of_measurement': '°F'})        # '72F'
format_state('45', {'unit_of_measurement': '%'})         # '45%'
```

#### `format_entity_line(numeric_id: int, entity: dict, max_name_len: int = 12) -> str`

Format entity as single line.

```python
line = format_entity_line(1, entity)
# "1.LT Kitchen    [ON]"
```

#### `format_entity_list(entities: list, start_id: int = 1) -> list`

Format list of entities.

```python
lines = format_entity_list(entities)
# ['1.LT Kitchen    [ON]', '2.SW Garage     [--]', ...]
```

#### `format_entity_detail(numeric_id: int, entity: dict) -> list`

Format detailed entity info.

```python
lines = format_entity_detail(1, entity)
# ['#1 LT Kitchen', 'State: [ON]', 'Bright: 78%', ...]
```

### Bandwidth Functions

#### `format_bandwidth_stats(text: str) -> dict`

Calculate bandwidth statistics.

```python
stats = format_bandwidth_stats(output_text)
# {
#     'bytes': 245,
#     'characters': 245,
#     'lines': 12,
#     'transmission_times': {
#         '300 baud': 8.17,
#         '1200 baud': 2.04,
#         '9600 baud': 0.26
#     }
# }
```

#### `estimate_transmission_time(text: str, baud_rate: int = 1200) -> float`

Estimate transmission time in seconds.

```python
time = estimate_transmission_time(text, 1200)
# 2.04 seconds @ 1200 baud
```

### Pagination

#### `Paginator(items: list, page_size: int = 10)`

Create paginator instance.

```python
paginator = Paginator(entities, page_size=10)

# Get page
page_items = paginator.get_page(1)

# Page info
info = paginator.get_page_info(1)
# {
#     'page_num': 1,
#     'total_pages': 3,
#     'has_next': True,
#     'has_prev': False,
#     ...
# }

# Format indicator
indicator = paginator.format_page_indicator(1, prefix="DEVICES")
# "DEVICES (pg 1/3)"

# Navigation
nav = paginator.format_navigation(1)
# "N:"
```

#### `format_page_with_entities(entities, formatter_func, page_num, page_size, title) -> tuple`

Format complete page with header and navigation.

```python
lines, page_info = format_page_with_entities(
    entities=my_entities,
    entity_formatter_func=format_entity_line,
    page_num=1,
    page_size=10,
    title="DEVICES"
)
```

### Help and Messages

#### `format_main_menu() -> list`

Get main menu/help screen.

```python
menu = format_main_menu()
# ['COMMANDS', 'L [pg]    List devices', ...]
```

#### `format_command_help(command: str) -> list`

Get detailed help for command.

```python
help = format_command_help('SET')
# ['SET VALUE', 'Usage: SET <id> <value>', ...]
```

#### `format_abbreviations() -> list`

Get entity type abbreviations reference.

```python
abbrevs = format_abbreviations()
# ['ABBREVIATIONS', 'LT  Light', 'SW  Switch', ...]
```

#### `format_error_message(error: str, context: str = None) -> list`

Format error message.

```python
msg = format_error_message('Device not found', 'Use L to list')
# ['ERR: Device not found', 'Use L to list']
```

#### `format_success_message(message: str) -> str`

Format success message.

```python
msg = format_success_message('Light turned on')
# 'OK: Light turned on'
```

#### `format_info_message(message: str) -> str`

Format info message.

```python
msg = format_info_message('Cache refreshed')
# 'INFO: Cache refreshed'
```

## Bandwidth Optimization

### Design Principles

1. **Abbreviate aggressively** - 2-char entity types
2. **Minimize whitespace** - Only for alignment
3. **Compact states** - Max 6 characters
4. **Short messages** - Under 30 chars when possible
5. **Paginate wisely** - Default 10 items/page

### Bandwidth Examples

**Entity list (10 items):**
```
DEVICES (pg 1/1)
1.LT Kitchen    [ON]
2.SW Garage     [--]
3.SN Temp       72F
4.BL Blinds     75%
5.AU GoodNight  [ON]
6.LT Bedroom    [--]
7.SW Porch      [ON]
8.SN Humidity   45%
9.CL Thermostat 70F
10.FN Ceiling   50%
```

**Stats:**
- Bytes: ~280
- Time @ 1200 baud: ~2.3 seconds
- Time @ 300 baud: ~9.3 seconds

### Optimization Tips

**Do:**
- Use entity numeric IDs (1, 2, 3...)
- Abbreviate entity types (LT, SW, SN...)
- Format states compactly (`[ON]`, `72F`)
- Paginate large lists
- Omit unnecessary labels

**Don't:**
- Use full entity IDs (`light.kitchen` = 13 chars!)
- Spell out states (`on` vs `[ON]` saves 1 char but brackets provide context)
- Show all entities at once
- Add decorative elements
- Use verbose messages

## Testing

### Run Tests

```bash
# All tests
python tools/test_formatting.py

# Specific test
python tools/test_formatting.py --test entity
python tools/test_formatting.py --test pagination
python tools/test_formatting.py --test help

# Interactive mode
python tools/test_formatting.py --interactive

# Complete page demo
python tools/test_formatting.py --demo
```

### Example Test Output

```
Entity Formatting Tests
===========================================================

1. Entity Abbreviations:
   light.kitchen        → LT
   switch.garage        → SW
   sensor.temp          → SN
   cover.blinds         → BL

2. State Formatting:
   on              → [ON]
   off             → [--]
   72              → 72F
   45              → 45%
   unavailable     → [??]

3. Entity Line Formatting:
   1.LT Kitchen    [ON]
   2.LT Bedroom    [--]
   3.SW Garage     [ON]
   4.SN Temperature 72F
   5.BL Blinds     75%
```

## Integration Example

### Complete Page Display

```python
from formatting import (
    format_page_with_entities,
    format_entity_line,
    estimate_transmission_time
)

# Format page
lines, page_info = format_page_with_entities(
    entities=entities,
    entity_formatter_func=format_entity_line,
    page_num=1,
    page_size=10,
    title="DEVICES"
)

# Send to user
output = '\n'.join(lines)
await session.send(output)

# Log bandwidth usage
time = estimate_transmission_time(output, 1200)
logger.info(f"Sent {len(output)} bytes in ~{time:.1f}s @ 1200 baud")
```

## Best Practices

### Entity Names

**Truncate long names:**
```python
# Good
"Kitchen Ligh…"  # 12 chars

# Bad
"Kitchen Light Main Overhead"  # 28 chars!
```

### State Display

**Use brackets for visual clarity:**
```python
# Good
"[ON]", "[--]", "[??]"  # Clear, aligned

# Less good
"on", "off", "unknown"  # Inconsistent length
```

### Pagination

**Optimal page size for 1200 baud:**
- **10 items** - Good balance (~2-3 seconds)
- **5 items** - Very fast (~1-2 seconds)
- **20 items** - Slower (~4-5 seconds)

### Error Messages

**Be concise but helpful:**
```python
# Good
format_error_message('Device not found', 'Use L to list')
# "ERR: Device not found"
# "Use L to list"

# Less good
format_error_message(
    'The device you requested could not be found in the system'
)
# Too verbose!
```

## Performance

### Transmission Times @ 1200 Baud

| Content | Bytes | Time |
|---------|-------|------|
| Single entity | ~25 | 0.2s |
| 10 entities | ~280 | 2.3s |
| Help menu | ~180 | 1.5s |
| Error message | ~30 | 0.3s |
| Detail view | ~120 | 1.0s |

### Memory Usage

- Minimal - all functions are stateless
- No caching - format on demand
- ~1KB per paginator instance

## Further Reading

- [PacketQTH Architecture](../ARCHITECTURE.md)
- [HomeAssistant Module](../homeassistant/README.md)
- [Server Module](../server/README.md)

---

**73!** 📡 Every byte counts at 1200 baud!
