"""
PacketQTH Help Formatter

Format help menus and documentation for minimal bandwidth.
"""

from typing import List, Dict, Tuple, Optional


def format_main_menu() -> List[str]:
    """
    Format the main menu/help screen.

    Returns:
        List of formatted lines
    """
    return [
        "COMMANDS",
        "L [pg]    List devices",
        "S <id>    Show device",
        "ON <id>   Turn on",
        "OFF <id>  Turn off",
        "SET <id> <val> Set value",
        "A [pg]    List automations",
        "T <id>    Trigger automation",
        "N / P     Next/prev page",
        "H         Help (this menu)",
        "Q         Quit"
    ]


def format_command_help(command: str) -> List[str]:
    """
    Format detailed help for a specific command.

    Args:
        command: Command name

    Returns:
        List of help lines
    """
    help_text = {
        'L': [
            "LIST DEVICES",
            "Usage: L [page]",
            "Examples:",
            "  L       First page",
            "  L 2     Page 2",
            "Shows devices with IDs"
        ],
        'S': [
            "SHOW DEVICE",
            "Usage: S <id>",
            "Examples:",
            "  S 1     Show device #1",
            "Shows detailed info"
        ],
        'ON': [
            "TURN ON",
            "Usage: ON <id>",
            "Examples:",
            "  ON 1    Turn on device #1",
            "Works with lights, switches"
        ],
        'OFF': [
            "TURN OFF",
            "Usage: OFF <id>",
            "Examples:",
            "  OFF 1   Turn off device #1",
            "Works with lights, switches"
        ],
        'SET': [
            "SET VALUE",
            "Usage: SET <id> <value>",
            "Examples:",
            "  SET 1 50    Set to 50%",
            "  SET 2 75    Set to 75",
            "For: brightness, position, temp"
        ],
        'A': [
            "LIST AUTOMATIONS",
            "Usage: A [page]",
            "Examples:",
            "  A       First page",
            "  A 2     Page 2",
            "Shows available automations"
        ],
        'T': [
            "TRIGGER AUTOMATION",
            "Usage: T <id>",
            "Examples:",
            "  T 1     Trigger automation #1",
            "Runs the automation"
        ],
        'Q': [
            "QUIT",
            "Usage: Q",
            "Disconnects from server"
        ]
    }

    cmd_upper = command.upper()
    return help_text.get(cmd_upper, [f"No help for: {command}"])


def format_abbreviations() -> List[str]:
    """
    Format entity type abbreviations reference.

    Returns:
        List of formatted lines
    """
    return [
        "ABBREVIATIONS",
        "LT  Light",
        "SW  Switch",
        "SN  Sensor",
        "BL  Blind/Cover",
        "AU  Automation",
        "SC  Scene",
        "CL  Climate",
        "FN  Fan",
        "LK  Lock"
    ]


def format_error_message(error: str, context: Optional[str] = None) -> List[str]:
    """
    Format error message.

    Args:
        error: Error message
        context: Optional context/hint

    Returns:
        List of formatted lines
    """
    lines = [f"ERR: {error}"]

    if context:
        lines.append(context)

    return lines


def format_success_message(message: str) -> str:
    """
    Format success message.

    Args:
        message: Success message

    Returns:
        Formatted message
    """
    return f"OK: {message}"


def format_info_message(message: str) -> str:
    """
    Format informational message.

    Args:
        message: Info message

    Returns:
        Formatted message
    """
    return f"INFO: {message}"


def format_status_line(
    items: List[Tuple[str, str]],
    separator: str = " | "
) -> str:
    """
    Format a status line with key-value pairs.

    Args:
        items: List of (key, value) tuples
        separator: Separator between items

    Returns:
        Formatted status line
    """
    formatted_items = [f"{key}: {value}" for key, value in items]
    return separator.join(formatted_items)


def format_table(
    rows: List[List[str]],
    headers: Optional[List[str]] = None,
    compact: bool = True
) -> List[str]:
    """
    Format a simple table.

    Args:
        rows: List of rows (each row is list of strings)
        headers: Optional header row
        compact: Use compact format (default: True)

    Returns:
        List of formatted lines
    """
    if not rows:
        return []

    lines = []

    # Calculate column widths
    all_rows = [headers] + rows if headers else rows
    col_widths = []

    if all_rows:
        num_cols = len(all_rows[0])
        for col_idx in range(num_cols):
            max_width = max(len(str(row[col_idx])) for row in all_rows if col_idx < len(row))
            col_widths.append(max_width)

    # Format header
    if headers and not compact:
        header_parts = []
        for i, header in enumerate(headers):
            if i < len(col_widths):
                header_parts.append(header.ljust(col_widths[i]))
        lines.append(' '.join(header_parts))
        lines.append('-' * len(lines[0]))

    # Format rows
    for row in rows:
        row_parts = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                if compact:
                    row_parts.append(str(cell))
                else:
                    row_parts.append(str(cell).ljust(col_widths[i]))

        if compact:
            lines.append(' '.join(row_parts))
        else:
            lines.append(' '.join(row_parts))

    return lines


def format_welcome_message(callsign: str) -> List[str]:
    """
    Format welcome message after authentication.

    Args:
        callsign: User's callsign

    Returns:
        List of formatted lines
    """
    return [
        f"Welcome {callsign}!",
        "Type H for help"
    ]


def format_disconnect_message() -> str:
    """
    Format disconnect message.

    Returns:
        Farewell message
    """
    return "73!"


def format_prompt(prompt_char: str = ">") -> str:
    """
    Format command prompt.

    Args:
        prompt_char: Prompt character (default: ">")

    Returns:
        Formatted prompt
    """
    return f"{prompt_char} "


def format_list_header(
    title: str,
    count: int,
    item_type: str = "items"
) -> str:
    """
    Format list header with count.

    Args:
        title: List title
        count: Number of items
        item_type: Type of items (default: "items")

    Returns:
        Formatted header
    """
    return f"{title} ({count} {item_type})"


def format_compact_list(
    items: List[str],
    prefix: str = "- ",
    max_items: Optional[int] = None
) -> List[str]:
    """
    Format a compact bulleted list.

    Args:
        items: List of items
        prefix: Line prefix (default: "- ")
        max_items: Maximum items to show (default: None = all)

    Returns:
        List of formatted lines
    """
    display_items = items[:max_items] if max_items else items

    lines = [f"{prefix}{item}" for item in display_items]

    if max_items and len(items) > max_items:
        remaining = len(items) - max_items
        lines.append(f"... and {remaining} more")

    return lines
