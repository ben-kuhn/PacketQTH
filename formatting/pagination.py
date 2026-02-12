"""
PacketQTH Pagination Formatter

Handle pagination for large lists with minimal bandwidth.
"""

from typing import List, Dict, Any, Tuple, Optional
import math


class Paginator:
    """
    Paginate lists for display with minimal bandwidth.

    Features:
    - Configurable page size
    - Page navigation (next/prev)
    - Compact page indicators
    """

    def __init__(self, items: List[Any], page_size: int = 10):
        """
        Initialize paginator.

        Args:
            items: List of items to paginate
            page_size: Items per page (default: 10)
        """
        self.items = items
        self.page_size = page_size
        self.total_items = len(items)
        self.total_pages = math.ceil(self.total_items / page_size) if page_size > 0 else 1

    def get_page(self, page_num: int) -> List[Any]:
        """
        Get items for a specific page.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            List of items for the page
        """
        # Validate page number
        if page_num < 1:
            page_num = 1
        elif page_num > self.total_pages:
            page_num = self.total_pages

        # Calculate slice indices
        start_idx = (page_num - 1) * self.page_size
        end_idx = start_idx + self.page_size

        return self.items[start_idx:end_idx]

    def get_page_info(self, page_num: int) -> Dict[str, Any]:
        """
        Get information about a specific page.

        Args:
            page_num: Page number (1-indexed)

        Returns:
            Dictionary with page information
        """
        # Validate page number
        page_num = max(1, min(page_num, self.total_pages))

        start_idx = (page_num - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_items)

        return {
            'page_num': page_num,
            'total_pages': self.total_pages,
            'page_size': self.page_size,
            'start_index': start_idx,
            'end_index': end_idx,
            'item_count': end_idx - start_idx,
            'total_items': self.total_items,
            'has_next': page_num < self.total_pages,
            'has_prev': page_num > 1
        }

    def format_page_indicator(
        self,
        page_num: int,
        prefix: str = "",
        compact: bool = True
    ) -> str:
        """
        Format page indicator string.

        Args:
            page_num: Current page number
            prefix: Optional prefix text (e.g., "DEVICES")
            compact: Use compact format (default: True)

        Returns:
            Formatted page indicator
        """
        info = self.get_page_info(page_num)

        if compact:
            # Compact format: "DEVICES (pg 1/3)"
            if prefix:
                return f"{prefix} (pg {info['page_num']}/{info['total_pages']})"
            else:
                return f"(pg {info['page_num']}/{info['total_pages']})"
        else:
            # Verbose format: "Page 1 of 3 (10 items)"
            return (
                f"Page {info['page_num']} of {info['total_pages']} "
                f"({info['item_count']} items)"
            )

    def format_navigation(self, page_num: int, compact: bool = True) -> Optional[str]:
        """
        Format navigation prompt.

        Args:
            page_num: Current page number
            compact: Use compact format (default: True)

        Returns:
            Navigation string or None if single page
        """
        if self.total_pages <= 1:
            return None

        info = self.get_page_info(page_num)

        nav_options = []

        if info['has_next']:
            nav_options.append('[N]ext' if not compact else 'N')

        if info['has_prev']:
            nav_options.append('[P]rev' if not compact else 'P')

        if not nav_options:
            return None

        if compact:
            return ' '.join(nav_options) + ':'
        else:
            return ' | '.join(nav_options)


def paginate_and_format(
    items: List[Any],
    formatter_func,
    page_num: int = 1,
    page_size: int = 10,
    title: str = "",
    show_nav: bool = True
) -> List[str]:
    """
    Paginate items and format them with header and navigation.

    Args:
        items: List of items to paginate
        formatter_func: Function to format each item (takes item, returns string)
        page_num: Page number to display (default: 1)
        page_size: Items per page (default: 10)
        title: Optional title for the page
        show_nav: Show navigation prompt (default: True)

    Returns:
        List of formatted lines (header, items, navigation)
    """
    paginator = Paginator(items, page_size)
    page_items = paginator.get_page(page_num)

    lines = []

    # Add header with page indicator
    header = paginator.format_page_indicator(page_num, prefix=title, compact=True)
    lines.append(header)

    # Format items
    for item in page_items:
        formatted = formatter_func(item)
        lines.append(formatted)

    # Add navigation if multiple pages
    if show_nav and paginator.total_pages > 1:
        nav = paginator.format_navigation(page_num, compact=True)
        if nav:
            lines.append(nav)

    return lines


def format_page_with_entities(
    entities: List[Dict[str, Any]],
    entity_formatter_func,
    page_num: int = 1,
    page_size: int = 10,
    title: str = "DEVICES"
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Format a page of entities with header and navigation.

    Args:
        entities: List of entity dictionaries
        entity_formatter_func: Function to format each entity
        page_num: Page number to display
        page_size: Entities per page
        title: Title for the page

    Returns:
        Tuple of (formatted_lines, page_info)
    """
    paginator = Paginator(entities, page_size)
    page_entities = paginator.get_page(page_num)
    page_info = paginator.get_page_info(page_num)

    lines = []

    # Header
    header = paginator.format_page_indicator(page_num, prefix=title)
    lines.append(header)

    # Format entities
    start_id = page_info['start_index'] + 1  # 1-indexed for display
    for i, entity in enumerate(page_entities, start=start_id):
        formatted = entity_formatter_func(i, entity)
        lines.append(formatted)

    # Navigation
    nav = paginator.format_navigation(page_num, compact=True)
    if nav:
        lines.append(nav)

    return lines, page_info


def calculate_optimal_page_size(
    avg_line_length: int,
    max_bytes_per_page: int = 500,
    lines_overhead: int = 3
) -> int:
    """
    Calculate optimal page size based on bandwidth constraints.

    Args:
        avg_line_length: Average characters per line
        max_bytes_per_page: Maximum bytes per page (default: 500)
        lines_overhead: Overhead lines (header, nav) (default: 3)

    Returns:
        Recommended page size
    """
    # Account for overhead (header + navigation)
    overhead_bytes = lines_overhead * 20  # Estimate 20 bytes per overhead line

    # Available bytes for content
    available_bytes = max_bytes_per_page - overhead_bytes

    # Calculate max items
    if avg_line_length > 0:
        max_items = available_bytes // avg_line_length
        return max(1, min(max_items, 20))  # Clamp between 1 and 20

    return 10  # Default fallback
