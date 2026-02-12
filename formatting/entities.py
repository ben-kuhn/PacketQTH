"""
PacketQTH Entity Formatter

Format HomeAssistant entities for minimal bandwidth display.
Optimized for 1200 baud packet radio connections.
"""

from typing import Dict, Any, Optional, List


# Entity type abbreviations (must be exactly 2 characters for alignment)
ENTITY_ABBREV = {
    'light': 'LT',
    'switch': 'SW',
    'sensor': 'SN',
    'cover': 'BL',  # Blinds
    'automation': 'AU',
    'scene': 'SC',
    'climate': 'CL',
    'fan': 'FN',
    'lock': 'LK',
    'binary_sensor': 'BS',
    'input_boolean': 'IB',
    'script': 'SR',
}


def get_entity_abbrev(entity_id: str) -> str:
    """
    Get abbreviation for entity type.

    Args:
        entity_id: Entity ID (e.g., 'light.kitchen')

    Returns:
        2-character abbreviation (e.g., 'LT')
    """
    domain = entity_id.split('.')[0] if '.' in entity_id else ''
    return ENTITY_ABBREV.get(domain, '??')


def format_state(state: str, attributes: Dict[str, Any] = None) -> str:
    """
    Format entity state compactly.

    Args:
        state: Entity state string
        attributes: Optional entity attributes for additional context

    Returns:
        Formatted state string (max 6 characters for alignment)
    """
    attributes = attributes or {}

    # Normalize state
    state_lower = state.lower()

    # On/Off states
    if state_lower == 'on':
        return '[ON]'
    elif state_lower == 'off':
        return '[--]'

    # Unavailable/Unknown
    elif state_lower in ('unavailable', 'unknown', 'none'):
        return '[??]'

    # Numeric states (temperature, brightness, position, etc.)
    try:
        value = float(state)

        # Check for unit of measurement
        unit = attributes.get('unit_of_measurement', '')

        # Temperature
        if unit in ('°C', '°F', 'C', 'F'):
            return f"{int(value)}{unit[0]}"

        # Percentage (brightness, position, etc.)
        elif unit == '%' or 'brightness' in attributes:
            return f"{int(value)}%"

        # Generic number
        else:
            return f"{int(value)}"

    except (ValueError, TypeError):
        pass

    # Long state strings - truncate
    if len(state) > 6:
        return state[:5] + '…'

    return state


def format_entity_line(
    numeric_id: int,
    entity: Dict[str, Any],
    max_name_len: int = 12
) -> str:
    """
    Format a single entity as a compact line.

    Format: "<id>.<TYPE> <Name>     [STATE]"
    Example: "1.LT Kitchen    [ON]"

    Args:
        numeric_id: Numeric ID for the entity
        entity: Entity dictionary from HomeAssistant
        max_name_len: Maximum length for entity name (default: 12)

    Returns:
        Formatted line string
    """
    entity_id = entity.get('entity_id', 'unknown')
    state = entity.get('state', 'unknown')
    attributes = entity.get('attributes', {})

    # Get friendly name or use entity ID
    name = attributes.get('friendly_name', entity_id.split('.')[-1])

    # Truncate name if needed
    if len(name) > max_name_len:
        name = name[:max_name_len - 1] + '…'

    # Get abbreviation
    abbrev = get_entity_abbrev(entity_id)

    # Format state
    state_str = format_state(state, attributes)

    # Build line with padding for alignment
    # Format: "id.AB Name         [STATE]"
    line = f"{numeric_id}.{abbrev} {name:<{max_name_len}} {state_str}"

    return line


def format_entity_list(
    entities: List[Dict[str, Any]],
    start_id: int = 1,
    max_name_len: int = 12
) -> List[str]:
    """
    Format a list of entities as compact lines.

    Args:
        entities: List of entity dictionaries
        start_id: Starting numeric ID (default: 1)
        max_name_len: Maximum name length (default: 12)

    Returns:
        List of formatted lines
    """
    lines = []

    for i, entity in enumerate(entities, start=start_id):
        line = format_entity_line(i, entity, max_name_len)
        lines.append(line)

    return lines


def format_entity_detail(
    numeric_id: int,
    entity: Dict[str, Any]
) -> List[str]:
    """
    Format detailed entity information.

    Args:
        numeric_id: Numeric ID for the entity
        entity: Entity dictionary from HomeAssistant

    Returns:
        List of detail lines
    """
    entity_id = entity.get('entity_id', 'unknown')
    state = entity.get('state', 'unknown')
    attributes = entity.get('attributes', {})

    lines = []

    # Header
    abbrev = get_entity_abbrev(entity_id)
    name = attributes.get('friendly_name', entity_id.split('.')[-1])
    lines.append(f"#{numeric_id} {abbrev} {name}")

    # State
    state_str = format_state(state, attributes)
    lines.append(f"State: {state_str}")

    # Additional attributes based on domain
    domain = entity_id.split('.')[0] if '.' in entity_id else ''

    if domain == 'light':
        # Brightness
        if 'brightness' in attributes:
            brightness_pct = int(attributes['brightness'] / 255 * 100)
            lines.append(f"Bright: {brightness_pct}%")

        # Color
        if 'rgb_color' in attributes:
            rgb = attributes['rgb_color']
            lines.append(f"Color: RGB({rgb[0]},{rgb[1]},{rgb[2]})")

    elif domain == 'cover':
        # Position
        if 'current_position' in attributes:
            pos = attributes['current_position']
            lines.append(f"Pos: {pos}%")

    elif domain == 'climate':
        # Temperature
        if 'temperature' in attributes:
            temp = attributes['temperature']
            unit = attributes.get('unit_of_measurement', '')
            lines.append(f"Target: {temp}{unit}")

        if 'current_temperature' in attributes:
            curr_temp = attributes['current_temperature']
            unit = attributes.get('unit_of_measurement', '')
            lines.append(f"Current: {curr_temp}{unit}")

    elif domain == 'sensor':
        # Unit of measurement
        unit = attributes.get('unit_of_measurement', '')
        if unit:
            lines.append(f"Unit: {unit}")

    # Entity ID (for reference)
    lines.append(f"ID: {entity_id}")

    return lines


def format_bandwidth_stats(text: str) -> Dict[str, Any]:
    """
    Calculate bandwidth statistics for text output.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with bandwidth stats
    """
    byte_count = len(text.encode('utf-8'))
    char_count = len(text)
    line_count = text.count('\n') + 1

    # Calculate transmission time at different baud rates
    baud_rates = {
        '300 baud': 300 / 10,    # ~30 bytes/sec
        '1200 baud': 1200 / 10,  # ~120 bytes/sec
        '9600 baud': 9600 / 10,  # ~960 bytes/sec
    }

    transmission_times = {}
    for rate_name, bytes_per_sec in baud_rates.items():
        seconds = byte_count / bytes_per_sec
        transmission_times[rate_name] = seconds

    return {
        'bytes': byte_count,
        'characters': char_count,
        'lines': line_count,
        'transmission_times': transmission_times
    }


def estimate_transmission_time(text: str, baud_rate: int = 1200) -> float:
    """
    Estimate transmission time for text at given baud rate.

    Args:
        text: Text to transmit
        baud_rate: Baud rate (default: 1200)

    Returns:
        Estimated time in seconds
    """
    byte_count = len(text.encode('utf-8'))
    bytes_per_sec = baud_rate / 10  # ~10 bits per byte (8 data + start/stop)
    return byte_count / bytes_per_sec


def format_compact(items: List[str], separator: str = ' ') -> str:
    """
    Join items with minimal whitespace.

    Args:
        items: List of items to join
        separator: Separator between items (default: single space)

    Returns:
        Compact string
    """
    return separator.join(items)


def truncate(text: str, max_length: int, suffix: str = '…') -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated (default: '…')

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
