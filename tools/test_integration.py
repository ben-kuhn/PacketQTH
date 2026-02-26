#!/usr/bin/env python3
"""
PacketQTH Integration Test

Test the complete flow without requiring real HomeAssistant connection.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from commands import parse_command, validate_command, CommandHandler, CommandType
from homeassistant.filters import EntityMapper
from formatting import format_entity_line


# Mock entities for testing
MOCK_ENTITIES = [
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
]


class MockHomeAssistantClient:
    """Mock HA client for testing."""

    def __init__(self):
        self.entities = MOCK_ENTITIES.copy()
        self.call_log = []

    async def get_states(self, use_cache=True):
        """Get all entities."""
        self.call_log.append(('get_states', use_cache))
        return self.entities

    async def turn_on(self, entity_id, **kwargs):
        """Turn on entity."""
        self.call_log.append(('turn_on', entity_id, kwargs))
        # Update mock state
        for entity in self.entities:
            if entity['entity_id'] == entity_id:
                entity['state'] = 'on'
                if 'brightness' in kwargs:
                    entity['attributes']['brightness'] = kwargs['brightness']

    async def turn_off(self, entity_id, **kwargs):
        """Turn off entity."""
        self.call_log.append(('turn_off', entity_id, kwargs))
        # Update mock state
        for entity in self.entities:
            if entity['entity_id'] == entity_id:
                entity['state'] = 'off'

    async def call_service(self, domain, service, **kwargs):
        """Call service."""
        self.call_log.append(('call_service', domain, service, kwargs))

    async def trigger_automation(self, automation_id):
        """Trigger automation."""
        self.call_log.append(('trigger_automation', automation_id))

    async def close(self):
        """Close client."""
        pass


async def test_parsing():
    """Test command parsing."""
    print("=" * 60)
    print("Command Parsing Tests")
    print("=" * 60)
    print()

    test_cases = [
        ('L', CommandType.LIST, True),
        ('S 1', CommandType.SHOW, True),
        ('ON 1', CommandType.ON, True),
        ('OFF 2', CommandType.OFF, True),
        ('SET 1 128', CommandType.SET, True),
        ('A', CommandType.AUTOMATIONS, True),
        ('T 6', CommandType.TRIGGER, True),
        ('H', CommandType.HELP, True),
        ('Q', CommandType.QUIT, True),
        ('INVALID', CommandType.UNKNOWN, False),
        ('S', None, False),  # Missing device ID
    ]

    passed = 0
    failed = 0

    for input_text, expected_type, should_be_valid in test_cases:
        command = parse_command(input_text)

        if should_be_valid:
            if command.is_valid() and command.type == expected_type:
                print(f"✓ Parse '{input_text}' -> {command.type.value}")
                passed += 1
            else:
                print(f"✗ Parse '{input_text}' failed")
                failed += 1
        else:
            if not command.is_valid():
                print(f"✓ Parse '{input_text}' -> error (expected)")
                passed += 1
            else:
                print(f"✗ Parse '{input_text}' should have failed")
                failed += 1

    print()
    print(f"Parsing: {passed} passed, {failed} failed")
    print()
    return failed == 0


async def test_entity_mapper():
    """Test entity mapper."""
    print("=" * 60)
    print("Entity Mapper Tests")
    print("=" * 60)
    print()

    mapper = EntityMapper()
    mapper.add_entities(MOCK_ENTITIES)

    passed = 0
    failed = 0

    # Test getting by ID
    entity = mapper.get_by_id(1)
    if entity and entity['entity_id'] == 'light.kitchen':
        print(f"✓ Get by ID: 1 -> {entity['entity_id']}")
        passed += 1
    else:
        print(f"✗ Get by ID: 1 failed")
        failed += 1

    # Test getting ID
    entity_id = mapper.get_id('light.kitchen')
    if entity_id == 1:
        print(f"✓ Get ID: light.kitchen -> {entity_id}")
        passed += 1
    else:
        print(f"✗ Get ID: light.kitchen failed")
        failed += 1

    # Test all entities
    all_entities = mapper.get_all()
    if len(all_entities) == len(MOCK_ENTITIES):
        print(f"✓ Get all: {len(all_entities)} entities")
        passed += 1
    else:
        print(f"✗ Get all: expected {len(MOCK_ENTITIES)}, got {len(all_entities)}")
        failed += 1

    print()
    print(f"Entity Mapper: {passed} passed, {failed} failed")
    print()
    return failed == 0


async def test_command_execution():
    """Test command execution."""
    print("=" * 60)
    print("Command Execution Tests")
    print("=" * 60)
    print()

    # Setup
    mock_ha = MockHomeAssistantClient()
    mapper = EntityMapper()
    mapper.add_entities(MOCK_ENTITIES)
    handler = CommandHandler(mock_ha, mapper, page_size=5)

    passed = 0
    failed = 0

    # Test LIST command
    command = parse_command('L')
    response = await handler.handle(command)
    if response and 'DEVICES' in response[0]:
        print(f"✓ LIST command")
        passed += 1
    else:
        print(f"✗ LIST command failed")
        failed += 1

    # Test SHOW command
    command = parse_command('S 1')
    response = await handler.handle(command)
    if response and any('Kitchen' in line for line in response):
        print(f"✓ SHOW command")
        passed += 1
    else:
        print(f"✗ SHOW command failed")
        failed += 1

    # Test ON command
    mock_ha.call_log = []
    command = parse_command('ON 2')  # Bedroom light
    response = await handler.handle(command)
    if response and 'OK:' in response[0] and ('turn_on', 'light.bedroom', {}) in mock_ha.call_log:
        print(f"✓ ON command")
        passed += 1
    else:
        print(f"✗ ON command failed")
        failed += 1

    # Test OFF command
    mock_ha.call_log = []
    command = parse_command('OFF 1')  # Kitchen light
    response = await handler.handle(command)
    if response and 'OK:' in response[0] and ('turn_off', 'light.kitchen', {}) in mock_ha.call_log:
        print(f"✓ OFF command")
        passed += 1
    else:
        print(f"✗ OFF command failed")
        failed += 1

    # Test SET command
    mock_ha.call_log = []
    command = parse_command('SET 1 128')  # Set kitchen light brightness
    response = await handler.handle(command)
    if response and 'OK:' in response[0]:
        # Check if turn_on was called with brightness
        called = any(call[0] == 'turn_on' and call[1] == 'light.kitchen'
                    and 'brightness' in call[2] for call in mock_ha.call_log)
        if called:
            print(f"✓ SET command")
            passed += 1
        else:
            print(f"✗ SET command: didn't call turn_on with brightness")
            failed += 1
    else:
        print(f"✗ SET command failed")
        failed += 1

    # Test AUTOMATIONS command
    command = parse_command('A')
    response = await handler.handle(command)
    if response and 'AUTOMATIONS' in response[0]:
        print(f"✓ AUTOMATIONS command")
        passed += 1
    else:
        print(f"✗ AUTOMATIONS command failed")
        failed += 1

    # Test TRIGGER command
    mock_ha.call_log = []
    command = parse_command('T 6')  # Trigger automation
    response = await handler.handle(command)
    if response and 'OK:' in response[0] and ('trigger_automation', 'automation.good_night') in mock_ha.call_log:
        print(f"✓ TRIGGER command")
        passed += 1
    else:
        print(f"✗ TRIGGER command failed")
        failed += 1

    # Test HELP command
    command = parse_command('H')
    response = await handler.handle(command)
    if response and 'COMMANDS' in response[0]:
        print(f"✓ HELP command")
        passed += 1
    else:
        print(f"✗ HELP command failed")
        failed += 1

    print()
    print(f"Command Execution: {passed} passed, {failed} failed")
    print()
    return failed == 0


async def test_formatting():
    """Test formatting."""
    print("=" * 60)
    print("Formatting Tests")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    # Test entity line formatting
    line = format_entity_line(1, MOCK_ENTITIES[0])
    if '1.LT' in line and 'Kitchen' in line and '[ON]' in line:
        print(f"✓ Format entity line: {line}")
        passed += 1
    else:
        print(f"✗ Format entity line failed: {line}")
        failed += 1

    print()
    print(f"Formatting: {passed} passed, {failed} failed")
    print()
    return failed == 0


async def main():
    """Run all integration tests."""
    print()
    print("PacketQTH Integration Tests")
    print("=" * 60)
    print()

    all_passed = True

    # Run tests
    all_passed &= await test_parsing()
    all_passed &= await test_entity_mapper()
    all_passed &= await test_command_execution()
    all_passed &= await test_formatting()

    # Summary
    print("=" * 60)
    if all_passed:
        print("✓ All integration tests passed!")
        print()
        return 0
    else:
        print("✗ Some tests failed")
        print()
        return 1


if __name__ == '__main__':
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
