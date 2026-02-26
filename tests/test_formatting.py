"""
Tests for formatting/help.py and formatting/pagination.py

Covers: format_status_line, format_table, format_welcome_message,
        format_disconnect_message, format_prompt, format_list_header,
        format_compact_list, Paginator (all methods), paginate_and_format,
        format_page_with_entities, calculate_optimal_page_size
"""

import pytest
from formatting.help import (
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
    format_compact_list,
)
from formatting.pagination import (
    Paginator,
    paginate_and_format,
    format_page_with_entities,
    calculate_optimal_page_size,
)


def make_entity(entity_id, state='on', **attrs):
    return {'entity_id': entity_id, 'state': state, 'attributes': attrs}


# ---------------------------------------------------------------------------
# format_status_line
# ---------------------------------------------------------------------------

class TestFormatStatusLine:
    def test_single_item(self):
        result = format_status_line([('Key', 'Value')])
        assert 'Key: Value' in result

    def test_multiple_items_separated(self):
        result = format_status_line([('A', '1'), ('B', '2')])
        assert 'A: 1' in result
        assert 'B: 2' in result
        assert ' | ' in result

    def test_custom_separator(self):
        result = format_status_line([('X', 'a'), ('Y', 'b')], separator=' - ')
        assert ' - ' in result
        assert ' | ' not in result

    def test_empty_items(self):
        result = format_status_line([])
        assert result == ''


# ---------------------------------------------------------------------------
# format_table
# ---------------------------------------------------------------------------

class TestFormatTable:
    def test_empty_rows(self):
        assert format_table([]) == []

    def test_single_row(self):
        lines = format_table([['Alice', '30']])
        assert len(lines) == 1
        assert 'Alice' in lines[0]
        assert '30' in lines[0]

    def test_multiple_rows(self):
        rows = [['Alice', '30'], ['Bob', '25']]
        lines = format_table(rows)
        assert len(lines) == 2

    def test_with_headers_compact(self):
        rows = [['Alice', '30']]
        headers = ['Name', 'Age']
        lines = format_table(rows, headers=headers, compact=True)
        # compact=True: headers not added as separate row
        assert len(lines) == 1

    def test_with_headers_not_compact(self):
        rows = [['Alice', '30']]
        headers = ['Name', 'Age']
        lines = format_table(rows, headers=headers, compact=False)
        # headers + separator + row = 3 lines
        assert len(lines) == 3
        assert 'Name' in lines[0]
        assert '-' in lines[1]  # separator

    def test_compact_default_true(self):
        rows = [['A', 'B']]
        result_compact = format_table(rows, headers=['X', 'Y'], compact=True)
        result_verbose = format_table(rows, headers=['X', 'Y'], compact=False)
        assert len(result_compact) < len(result_verbose)


# ---------------------------------------------------------------------------
# format_welcome_message
# ---------------------------------------------------------------------------

class TestFormatWelcomeMessage:
    def test_contains_callsign(self):
        lines = format_welcome_message('KN4XYZ')
        full = ' '.join(lines)
        assert 'KN4XYZ' in full

    def test_contains_help_hint(self):
        lines = format_welcome_message('KN4XYZ')
        full = ' '.join(lines)
        assert 'H' in full  # "Type H for help"

    def test_returns_list(self):
        assert isinstance(format_welcome_message('KN4XYZ'), list)


# ---------------------------------------------------------------------------
# format_disconnect_message
# ---------------------------------------------------------------------------

class TestFormatDisconnectMessage:
    def test_returns_73(self):
        assert '73' in format_disconnect_message()

    def test_returns_string(self):
        assert isinstance(format_disconnect_message(), str)


# ---------------------------------------------------------------------------
# format_prompt
# ---------------------------------------------------------------------------

class TestFormatPrompt:
    def test_default_prompt(self):
        result = format_prompt()
        assert '>' in result

    def test_custom_prompt_char(self):
        result = format_prompt('#')
        assert '#' in result
        assert '>' not in result

    def test_has_trailing_space(self):
        result = format_prompt('>')
        assert result.endswith(' ')


# ---------------------------------------------------------------------------
# format_list_header
# ---------------------------------------------------------------------------

class TestFormatListHeader:
    def test_includes_title(self):
        result = format_list_header('DEVICES', 5)
        assert 'DEVICES' in result

    def test_includes_count(self):
        result = format_list_header('DEVICES', 5)
        assert '5' in result

    def test_includes_item_type(self):
        result = format_list_header('DEVICES', 5, 'gadgets')
        assert 'gadgets' in result

    def test_default_item_type(self):
        result = format_list_header('DEVICES', 5)
        assert 'items' in result


# ---------------------------------------------------------------------------
# format_compact_list
# ---------------------------------------------------------------------------

class TestFormatCompactList:
    def test_basic_list(self):
        lines = format_compact_list(['a', 'b', 'c'])
        assert len(lines) == 3
        assert all(line.startswith('- ') for line in lines)

    def test_custom_prefix(self):
        lines = format_compact_list(['x'], prefix='* ')
        assert lines[0] == '* x'

    def test_max_items_truncates(self):
        lines = format_compact_list(['a', 'b', 'c', 'd', 'e'], max_items=3)
        assert len(lines) == 4  # 3 items + "... and X more"
        assert 'more' in lines[-1]

    def test_max_items_exact(self):
        lines = format_compact_list(['a', 'b', 'c'], max_items=3)
        assert len(lines) == 3  # no overflow

    def test_empty_list(self):
        assert format_compact_list([]) == []

    def test_no_max_items_shows_all(self):
        items = [str(i) for i in range(50)]
        lines = format_compact_list(items)
        assert len(lines) == 50


# ---------------------------------------------------------------------------
# format_main_menu (quick sanity)
# ---------------------------------------------------------------------------

class TestFormatMainMenu:
    def test_returns_list_of_strings(self):
        menu = format_main_menu()
        assert isinstance(menu, list)
        assert all(isinstance(line, str) for line in menu)

    def test_contains_key_commands(self):
        menu_text = '\n'.join(format_main_menu())
        for cmd in ['L', 'S', 'ON', 'OFF', 'SET', 'A', 'T', 'N', 'P', 'H', 'Q']:
            assert cmd in menu_text


# ---------------------------------------------------------------------------
# format_command_help
# ---------------------------------------------------------------------------

class TestFormatCommandHelp:
    @pytest.mark.parametrize("cmd", ['L', 'S', 'ON', 'OFF', 'SET', 'A', 'T', 'Q'])
    def test_known_commands(self, cmd):
        result = format_command_help(cmd)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_unknown_command_graceful(self):
        result = format_command_help('UNKNOWN_CMD')
        assert isinstance(result, list)
        assert len(result) == 1

    def test_case_insensitive(self):
        lower = format_command_help('on')
        upper = format_command_help('ON')
        assert lower == upper


# ---------------------------------------------------------------------------
# format_error / success / info messages
# ---------------------------------------------------------------------------

class TestMessageFormatters:
    def test_error_message_prefix(self):
        lines = format_error_message('Something failed')
        assert lines[0].startswith('ERR:')

    def test_error_with_context(self):
        lines = format_error_message('Oops', 'Try again')
        assert len(lines) == 2
        assert 'Try again' in lines[1]

    def test_success_message_prefix(self):
        assert format_success_message('Done').startswith('OK:')

    def test_info_message_prefix(self):
        assert format_info_message('Loading').startswith('INFO:')


# ---------------------------------------------------------------------------
# format_abbreviations
# ---------------------------------------------------------------------------

class TestFormatAbbreviations:
    def test_returns_list(self):
        result = format_abbreviations()
        assert isinstance(result, list)

    def test_contains_light(self):
        text = '\n'.join(format_abbreviations())
        assert 'LT' in text

    def test_contains_switch(self):
        text = '\n'.join(format_abbreviations())
        assert 'SW' in text


# ---------------------------------------------------------------------------
# Paginator
# ---------------------------------------------------------------------------

class TestPaginator:
    def test_total_pages_exact_fit(self):
        p = Paginator(list(range(10)), page_size=5)
        assert p.total_pages == 2

    def test_total_pages_remainder(self):
        p = Paginator(list(range(11)), page_size=5)
        assert p.total_pages == 3

    def test_total_pages_empty_list(self):
        p = Paginator([], page_size=5)
        assert p.total_pages == 0

    def test_total_pages_single_item(self):
        p = Paginator([1], page_size=5)
        assert p.total_pages == 1

    def test_get_page_first(self):
        items = list(range(15))
        p = Paginator(items, page_size=5)
        page = p.get_page(1)
        assert page == [0, 1, 2, 3, 4]

    def test_get_page_second(self):
        items = list(range(15))
        p = Paginator(items, page_size=5)
        page = p.get_page(2)
        assert page == [5, 6, 7, 8, 9]

    def test_get_page_last_partial(self):
        items = list(range(12))
        p = Paginator(items, page_size=5)
        page = p.get_page(3)
        assert page == [10, 11]

    def test_get_page_clamps_below_1(self):
        items = list(range(10))
        p = Paginator(items, page_size=5)
        assert p.get_page(0) == p.get_page(1)
        assert p.get_page(-1) == p.get_page(1)

    def test_get_page_clamps_above_max(self):
        items = list(range(10))
        p = Paginator(items, page_size=5)
        assert p.get_page(999) == p.get_page(2)

    def test_get_page_empty_list(self):
        p = Paginator([], page_size=5)
        assert p.get_page(1) == []

    def test_get_page_info_first_page(self):
        p = Paginator(list(range(25)), page_size=10)
        info = p.get_page_info(1)
        assert info['page_num'] == 1
        assert info['total_pages'] == 3
        assert info['start_index'] == 0
        assert info['end_index'] == 10
        assert info['item_count'] == 10
        assert info['has_next'] is True
        assert info['has_prev'] is False

    def test_get_page_info_last_page(self):
        p = Paginator(list(range(25)), page_size=10)
        info = p.get_page_info(3)
        assert info['item_count'] == 5  # remainder
        assert info['has_next'] is False
        assert info['has_prev'] is True

    def test_get_page_info_middle_page(self):
        p = Paginator(list(range(30)), page_size=10)
        info = p.get_page_info(2)
        assert info['has_next'] is True
        assert info['has_prev'] is True

    def test_format_page_indicator_compact_with_prefix(self):
        p = Paginator(list(range(20)), page_size=10)
        indicator = p.format_page_indicator(1, prefix='DEVICES')
        assert 'DEVICES' in indicator
        assert '1/2' in indicator

    def test_format_page_indicator_compact_no_prefix(self):
        p = Paginator(list(range(20)), page_size=10)
        indicator = p.format_page_indicator(1)
        assert '(pg 1/2)' in indicator

    def test_format_page_indicator_verbose(self):
        p = Paginator(list(range(20)), page_size=10)
        indicator = p.format_page_indicator(1, compact=False)
        assert 'Page 1 of 2' in indicator

    def test_format_navigation_single_page_returns_none(self):
        p = Paginator(list(range(5)), page_size=10)
        assert p.format_navigation(1) is None

    def test_format_navigation_first_page_has_next(self):
        p = Paginator(list(range(20)), page_size=10)
        nav = p.format_navigation(1)
        assert 'N' in nav
        assert 'P' not in nav

    def test_format_navigation_last_page_has_prev(self):
        p = Paginator(list(range(20)), page_size=10)
        nav = p.format_navigation(2)
        assert 'P' in nav
        assert 'N' not in nav

    def test_format_navigation_middle_page_has_both(self):
        p = Paginator(list(range(30)), page_size=10)
        nav = p.format_navigation(2)
        assert 'N' in nav
        assert 'P' in nav

    def test_format_navigation_verbose(self):
        p = Paginator(list(range(30)), page_size=10)
        nav = p.format_navigation(2, compact=False)
        assert '[N]ext' in nav or '[P]rev' in nav


# ---------------------------------------------------------------------------
# paginate_and_format
# ---------------------------------------------------------------------------

class TestPaginateAndFormat:
    def test_basic_formatting(self):
        items = ['apple', 'banana', 'cherry']
        lines = paginate_and_format(items, lambda x: x.upper(), page_num=1, page_size=10)
        assert 'APPLE' in lines
        assert 'BANANA' in lines

    def test_includes_header(self):
        items = list(range(5))
        lines = paginate_and_format(items, str, title='STUFF')
        assert 'STUFF' in lines[0]

    def test_navigation_on_multiple_pages(self):
        items = list(range(15))
        lines = paginate_and_format(items, str, page_num=1, page_size=5)
        nav = lines[-1]
        assert 'N' in nav  # next page navigation

    def test_no_navigation_single_page(self):
        items = list(range(5))
        lines = paginate_and_format(items, str, page_num=1, page_size=10)
        # No navigation line at end when single page
        # Navigation only shown when multiple pages
        assert len(lines) == 6  # 1 header + 5 items; no nav
        # Verify the last line is an item, not a navigation hint
        assert 'next' not in lines[-1].lower()


# ---------------------------------------------------------------------------
# format_page_with_entities
# ---------------------------------------------------------------------------

class TestFormatPageWithEntities:
    def _make_entities(self, count):
        return [
            {'entity_id': f'light.light_{i}', 'state': 'on', 'attributes': {'friendly_name': f'Light {i}'}}
            for i in range(1, count + 1)
        ]

    def test_returns_tuple(self):
        result = format_page_with_entities(self._make_entities(3), lambda i, e: f"{i}. {e['entity_id']}")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_lines_and_page_info(self):
        entities = self._make_entities(5)
        lines, info = format_page_with_entities(entities, lambda i, e: str(i))
        assert isinstance(lines, list)
        assert isinstance(info, dict)
        assert 'total_pages' in info

    def test_entity_ids_are_1_indexed(self):
        entities = self._make_entities(3)
        lines, _ = format_page_with_entities(entities, lambda i, e: str(i))
        # First line is header, entities start at line[1]
        assert '1' in lines[1]

    def test_pagination_correct_page(self):
        entities = self._make_entities(15)
        lines, info = format_page_with_entities(entities, lambda i, e: str(i), page_num=2, page_size=10)
        assert info['page_num'] == 2
        # Navigation: has_prev
        assert info['has_prev'] is True


# ---------------------------------------------------------------------------
# calculate_optimal_page_size
# ---------------------------------------------------------------------------

class TestCalculateOptimalPageSize:
    def test_returns_int(self):
        result = calculate_optimal_page_size(avg_line_length=30)
        assert isinstance(result, int)

    def test_minimum_is_1(self):
        # Very long lines → should still return at least 1
        result = calculate_optimal_page_size(avg_line_length=10000)
        assert result >= 1

    def test_maximum_is_20(self):
        # Very short lines → should cap at 20
        result = calculate_optimal_page_size(avg_line_length=1)
        assert result <= 20

    def test_larger_budget_bigger_page(self):
        small = calculate_optimal_page_size(avg_line_length=30, max_bytes_per_page=200)
        large = calculate_optimal_page_size(avg_line_length=30, max_bytes_per_page=2000)
        assert large >= small

    def test_zero_line_length_returns_default(self):
        result = calculate_optimal_page_size(avg_line_length=0)
        assert result == 10  # default fallback
