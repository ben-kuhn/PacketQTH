#!/usr/bin/env python3
"""
PacketQTH Formatting Test Tool

Test and demonstrate text formatting capabilities.
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from formatting import *


# Sample entity data for testing
SAMPLE_ENTITIES = [
    {
        'entity_id': 'light.kitchen',
        'state': 'on',
        'attributes': {'friendly_name': 'Kitchen Light', 'brightness': 200}
    },
    {
        'entity_id': 'light.bedroom',
        'state': 'off',
        'attributes': {'friendly_name': 'Bedroom Light'}
    },
    {
        'entity_id': 'switch.garage',
        'state': 'on',
        'attributes': {'friendly_name': 'Garage Door'}
    },
    {
        'entity_id': 'sensor.temperature',
        'state': '72',
        'attributes': {'friendly_name': 'Living Room Temp', 'unit_of_measurement': '°F'}
    },
    {
        'entity_id': 'cover.blinds',
        'state': 'open',
        'attributes': {'friendly_name': 'Window Blinds', 'current_position': 75}
    },
    {
        'entity_id': 'automation.good_night',
        'state': 'on',
        'attributes': {'friendly_name': 'Good Night Routine'}
    },
    {
        'entity_id': 'switch.porch_light',
        'state': 'off',
        'attributes': {'friendly_name': 'Porch Light'}
    },
    {
        'entity_id': 'sensor.humidity',
        'state': '45',
        'attributes': {'friendly_name': 'Humidity', 'unit_of_measurement': '%'}
    },
]


def test_entity_formatting():
    """Test entity formatting functions."""
    print("="*60)
    print("Entity Formatting Tests")
    print("="*60)
    print()

    # Test abbreviations
    print("1. Entity Abbreviations:")
    for entity_id in ['light.kitchen', 'switch.garage', 'sensor.temp', 'cover.blinds']:
        abbrev = get_entity_abbrev(entity_id)
        print(f"   {entity_id:20s} → {abbrev}")
    print()

    # Test state formatting
    print("2. State Formatting:")
    states = [
        ('on', {}),
        ('off', {}),
        ('72', {'unit_of_measurement': '°F'}),
        ('45', {'unit_of_measurement': '%'}),
        ('unavailable', {}),
    ]
    for state, attrs in states:
        formatted = format_state(state, attrs)
        print(f"   {state:15s} → {formatted}")
    print()

    # Test entity line formatting
    print("3. Entity Line Formatting:")
    for i, entity in enumerate(SAMPLE_ENTITIES[:5], 1):
        line = format_entity_line(i, entity)
        print(f"   {line}")
    print()

    # Test entity detail formatting
    print("4. Entity Detail:")
    lines = format_entity_detail(1, SAMPLE_ENTITIES[0])
    for line in lines:
        print(f"   {line}")
    print()


def test_pagination():
    """Test pagination functions."""
    print("="*60)
    print("Pagination Tests")
    print("="*60)
    print()

    paginator = Paginator(SAMPLE_ENTITIES, page_size=3)

    print(f"Total items: {paginator.total_items}")
    print(f"Page size: {paginator.page_size}")
    print(f"Total pages: {paginator.total_pages}")
    print()

    # Test page 1
    print("Page 1:")
    page1 = paginator.get_page(1)
    for i, entity in enumerate(page1, 1):
        line = format_entity_line(i, entity)
        print(f"   {line}")

    indicator = paginator.format_page_indicator(1, prefix="DEVICES")
    print(f"   {indicator}")

    nav = paginator.format_navigation(1)
    if nav:
        print(f"   {nav}")
    print()

    # Test page 2
    print("Page 2:")
    page2 = paginator.get_page(2)
    for i, entity in enumerate(page2, 4):  # Continue numbering
        line = format_entity_line(i, entity)
        print(f"   {line}")

    indicator = paginator.format_page_indicator(2, prefix="DEVICES")
    print(f"   {indicator}")

    nav = paginator.format_navigation(2)
    if nav:
        print(f"   {nav}")
    print()


def test_help_formatting():
    """Test help formatting functions."""
    print("="*60)
    print("Help Formatting Tests")
    print("="*60)
    print()

    # Main menu
    print("1. Main Menu:")
    menu = format_main_menu()
    for line in menu:
        print(f"   {line}")
    print()

    # Command help
    print("2. Command Help (SET):")
    help_lines = format_command_help('SET')
    for line in help_lines:
        print(f"   {line}")
    print()

    # Abbreviations
    print("3. Abbreviations:")
    abbrev_lines = format_abbreviations()
    for line in abbrev_lines:
        print(f"   {line}")
    print()

    # Messages
    print("4. Messages:")
    print(f"   {format_success_message('Light turned on')}")
    print(f"   {format_info_message('Cache refreshed')}")
    error = format_error_message('Device not found', 'Use L to list devices')
    for line in error:
        print(f"   {line}")
    print()


def test_bandwidth_stats():
    """Test bandwidth calculation."""
    print("="*60)
    print("Bandwidth Statistics")
    print("="*60)
    print()

    # Create a sample output
    lines = []
    lines.append("DEVICES (pg 1/1)")
    for i, entity in enumerate(SAMPLE_ENTITIES[:5], 1):
        lines.append(format_entity_line(i, entity))

    output = '\n'.join(lines)

    print("Sample Output:")
    print(output)
    print()

    stats = format_bandwidth_stats(output)
    print(f"Bytes: {stats['bytes']}")
    print(f"Characters: {stats['characters']}")
    print(f"Lines: {stats['lines']}")
    print()
    print("Transmission Times:")
    for rate, time in stats['transmission_times'].items():
        print(f"  {rate:15s}: {time:.2f} seconds")
    print()


def test_complete_page():
    """Test complete page formatting."""
    print("="*60)
    print("Complete Page Example")
    print("="*60)
    print()

    lines, page_info = format_page_with_entities(
        entities=SAMPLE_ENTITIES,
        entity_formatter_func=format_entity_line,
        page_num=1,
        page_size=5,
        title="DEVICES"
    )

    for line in lines:
        print(line)

    print()
    print(f"Page info: {page_info}")
    print()

    # Calculate bandwidth
    output = '\n'.join(lines)
    time = estimate_transmission_time(output, baud_rate=1200)
    print(f"Transmission time @ 1200 baud: {time:.2f} seconds")
    print()


def test_interactive():
    """Interactive formatting test."""
    print("="*60)
    print("Interactive Formatting Test")
    print("="*60)
    print()

    while True:
        print("\nOptions:")
        print("  1 - Entity formatting")
        print("  2 - Pagination")
        print("  3 - Help menus")
        print("  4 - Bandwidth stats")
        print("  5 - Complete page")
        print("  Q - Quit")

        choice = input("\nChoice: ").strip().upper()

        if choice == '1':
            test_entity_formatting()
        elif choice == '2':
            test_pagination()
        elif choice == '3':
            test_help_formatting()
        elif choice == '4':
            test_bandwidth_stats()
        elif choice == '5':
            test_complete_page()
        elif choice == 'Q':
            print("73!")
            break
        else:
            print("Invalid choice")


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH text formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_formatting.py

  # Run specific test
  python test_formatting.py --test entity

  # Interactive mode
  python test_formatting.py --interactive

  # Show complete page demo
  python test_formatting.py --demo
        """
    )

    parser.add_argument(
        '--test',
        choices=['entity', 'pagination', 'help', 'bandwidth', 'page'],
        help='Run specific test'
    )
    parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help='Interactive mode'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Show complete page demo'
    )

    args = parser.parse_args()

    if args.interactive:
        test_interactive()
    elif args.demo:
        test_complete_page()
    elif args.test:
        if args.test == 'entity':
            test_entity_formatting()
        elif args.test == 'pagination':
            test_pagination()
        elif args.test == 'help':
            test_help_formatting()
        elif args.test == 'bandwidth':
            test_bandwidth_stats()
        elif args.test == 'page':
            test_complete_page()
    else:
        # Run all tests
        test_entity_formatting()
        test_pagination()
        test_help_formatting()
        test_bandwidth_stats()
        test_complete_page()


if __name__ == '__main__':
    main()
