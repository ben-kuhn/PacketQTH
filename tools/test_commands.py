#!/usr/bin/env python3
"""
PacketQTH Command Parser Test Tool

Test and demonstrate command parsing and validation.
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands import parse_command, CommandType, validate_command, ValidationError
from homeassistant.filters import EntityMapper


# Sample entities for validation testing
SAMPLE_ENTITIES = [
    {
        'entity_id': 'light.kitchen',
        'state': 'on',
        'attributes': {'friendly_name': 'Kitchen Light', 'brightness': 200}
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
]


def test_basic_parsing():
    """Test basic command parsing."""
    print("=" * 60)
    print("Basic Parsing Tests")
    print("=" * 60)
    print()

    test_cases = [
        # LIST command
        ("L", "List devices (page 1)"),
        ("L 2", "List devices page 2"),
        ("LIST", "List devices (long form)"),
        ("list 3", "List devices page 3 (lowercase)"),

        # SHOW command
        ("S 1", "Show device #1"),
        ("SHOW 5", "Show device #5 (long form)"),

        # ON/OFF commands
        ("ON 1", "Turn on device #1"),
        ("OFF 2", "Turn off device #2"),
        ("on 3", "Turn on device #3 (lowercase)"),

        # SET command
        ("SET 1 75", "Set device #1 to 75"),
        ("SET 2 100", "Set device #2 to 100"),
        ("set 3 50.5", "Set device #3 to 50.5"),

        # AUTOMATIONS command
        ("A", "List automations"),
        ("A 2", "List automations page 2"),
        ("AUTO", "List automations (alias)"),

        # TRIGGER command
        ("T 1", "Trigger automation #1"),
        ("TRIGGER 5", "Trigger automation #5"),

        # HELP command
        ("H", "Help"),
        ("HELP", "Help (long form)"),
        ("?", "Help (? alias)"),

        # QUIT command
        ("Q", "Quit"),
        ("QUIT", "Quit (long form)"),
        ("EXIT", "Quit (exit alias)"),

        # REFRESH command
        ("R", "Refresh cache"),
        ("REFRESH", "Refresh cache (long form)"),
    ]

    for input_text, description in test_cases:
        command = parse_command(input_text)
        status = "✓" if command.is_valid() else "✗"
        print(f"{status} {description:40s}")
        print(f"  Input:   '{input_text}'")
        print(f"  Parsed:  {command}")
        print()


def test_error_handling():
    """Test error handling for invalid commands."""
    print("=" * 60)
    print("Error Handling Tests")
    print("=" * 60)
    print()

    test_cases = [
        ("", "Empty command"),
        ("INVALID", "Unknown command"),
        ("XYZ 123", "Invalid command word"),
        ("S", "SHOW without device ID"),
        ("ON", "ON without device ID"),
        ("OFF", "OFF without device ID"),
        ("SET 1", "SET without value"),
        ("SET", "SET without device ID or value"),
        ("T", "TRIGGER without automation ID"),
        ("L abc", "LIST with non-numeric page"),
        ("S abc", "SHOW with non-numeric ID"),
        ("SET 1 abc", "SET with non-numeric value (should allow)"),
    ]

    for input_text, description in test_cases:
        command = parse_command(input_text)
        status = "✓" if not command.is_valid() else "✗"
        print(f"{status} {description:40s}")
        print(f"  Input:   '{input_text}'")
        print(f"  Result:  {command.type.value}")
        if command.error:
            print(f"  Error:   {command.error}")
        print()


def test_validation():
    """Test command validation against entity state."""
    print("=" * 60)
    print("Command Validation Tests")
    print("=" * 60)
    print()

    # Create entity mapper
    mapper = EntityMapper()
    mapper.add_entities(SAMPLE_ENTITIES)

    test_cases = [
        # Valid commands
        ("S 1", True, "Show light #1"),
        ("ON 1", True, "Turn on light #1"),
        ("OFF 1", True, "Turn off light #1"),
        ("SET 1 128", True, "Set light #1 brightness"),
        ("ON 2", True, "Turn on switch #2"),
        ("SET 4 75", True, "Set cover #4 position"),
        ("T 5", True, "Trigger automation #5"),

        # Invalid commands
        ("S 99", False, "Show non-existent device"),
        ("ON 3", False, "Turn on sensor (not switchable)"),
        ("SET 3 100", False, "Set sensor value (not settable)"),
        ("T 1", False, "Trigger light (not automation)"),
        ("SET 1 300", False, "Set brightness out of range"),
        ("SET 4 150", False, "Set cover position out of range"),
    ]

    for input_text, should_be_valid, description in test_cases:
        command = parse_command(input_text)

        # Check parsing
        if not command.is_valid():
            print(f"✗ {description:40s}")
            print(f"  Input:      '{input_text}'")
            print(f"  Parse error: {command.error}")
            print()
            continue

        # Check validation
        try:
            validate_command(command, mapper)
            is_valid = True
        except ValidationError as e:
            is_valid = False
            validation_error = str(e)

        # Check if result matches expectation
        if is_valid == should_be_valid:
            status = "✓"
        else:
            status = "✗"

        print(f"{status} {description:40s}")
        print(f"  Input:    '{input_text}'")
        print(f"  Expected: {'Valid' if should_be_valid else 'Invalid'}")
        print(f"  Got:      {'Valid' if is_valid else 'Invalid'}")
        if not is_valid:
            print(f"  Error:    {validation_error}")
        print()


def test_interactive():
    """Interactive command parsing test."""
    print("=" * 60)
    print("Interactive Command Parser Test")
    print("=" * 60)
    print()
    print("Enter commands to parse (Q to quit)")
    print()

    # Create entity mapper for validation
    mapper = EntityMapper()
    mapper.add_entities(SAMPLE_ENTITIES)

    print("Available test entities:")
    for i, entity in enumerate(SAMPLE_ENTITIES, 1):
        entity_id = entity['entity_id']
        name = entity['attributes']['friendly_name']
        print(f"  {i}. {entity_id:25s} ({name})")
    print()

    while True:
        try:
            user_input = input("> ").strip()

            if not user_input:
                continue

            # Parse command
            command = parse_command(user_input)

            print(f"Parsed: {command}")

            if not command.is_valid():
                print(f"Parse Error: {command.error}")
                print()
                continue

            # Try validation
            try:
                validate_command(command, mapper)
                print("Validation: ✓ Valid")
            except ValidationError as e:
                print(f"Validation Error: {e}")

            print()

            # Quit if Q command
            if command.type == CommandType.QUIT:
                print("73!")
                break

        except KeyboardInterrupt:
            print("\n73!")
            break
        except EOFError:
            print("\n73!")
            break


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH command parsing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python test_commands.py

  # Run specific test
  python test_commands.py --test parsing

  # Interactive mode
  python test_commands.py --interactive
        """
    )

    parser.add_argument(
        '--test',
        choices=['parsing', 'errors', 'validation'],
        help='Run specific test'
    )
    parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help='Interactive mode'
    )

    args = parser.parse_args()

    if args.interactive:
        test_interactive()
    elif args.test:
        if args.test == 'parsing':
            test_basic_parsing()
        elif args.test == 'errors':
            test_error_handling()
        elif args.test == 'validation':
            test_validation()
    else:
        # Run all tests
        test_basic_parsing()
        test_error_handling()
        test_validation()


if __name__ == '__main__':
    main()
