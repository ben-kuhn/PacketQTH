"""
PacketQTH Formatting Module

Text formatting utilities for minimal bandwidth display.
Optimized for 1200 baud packet radio connections.
"""

# Entity formatting
from .entities import (
    ENTITY_ABBREV,
    get_entity_abbrev,
    format_state,
    format_entity_line,
    format_entity_list,
    format_entity_detail,
    format_bandwidth_stats,
    estimate_transmission_time,
    format_compact,
    truncate
)

# Pagination
from .pagination import (
    Paginator,
    paginate_and_format,
    format_page_with_entities,
    calculate_optimal_page_size
)

# Help and messages
from .help import (
    format_main_menu,
    format_command_help,
    format_abbreviations,
    format_error_message,
    format_success_message,
    format_info_message,
    format_status_line,
    format_table,
    format_welcome_message,
    format_disconnect_message,
    format_prompt,
    format_list_header,
    format_compact_list
)

__all__ = [
    # Entity formatting
    'ENTITY_ABBREV',
    'get_entity_abbrev',
    'format_state',
    'format_entity_line',
    'format_entity_list',
    'format_entity_detail',
    'format_bandwidth_stats',
    'estimate_transmission_time',
    'format_compact',
    'truncate',

    # Pagination
    'Paginator',
    'paginate_and_format',
    'format_page_with_entities',
    'calculate_optimal_page_size',

    # Help and messages
    'format_main_menu',
    'format_command_help',
    'format_abbreviations',
    'format_error_message',
    'format_success_message',
    'format_info_message',
    'format_status_line',
    'format_table',
    'format_welcome_message',
    'format_disconnect_message',
    'format_prompt',
    'format_list_header',
    'format_compact_list'
]
