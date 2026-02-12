#!/usr/bin/env python3
"""
PacketQTH HomeAssistant Client Test Tool

Test HomeAssistant API connectivity, entity filtering, and operations.
"""

import sys
import os
import asyncio
import argparse
import yaml
from typing import Dict, Any

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from homeassistant import (
    HomeAssistantClient,
    EntityFilter,
    ConnectionError,
    AuthenticationError,
    HomeAssistantError
)


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

            # Handle environment variable substitution for token
            ha_config = config.get('homeassistant', {})
            token = ha_config.get('token', '')
            if token.startswith('${') and token.endswith('}'):
                env_var = token[2:-1]
                ha_config['token'] = os.environ.get(env_var, '')

            return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        print("Create one from config.yaml.example")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration: {e}")
        sys.exit(1)


async def test_connection(client: HomeAssistantClient):
    """Test basic connection to HomeAssistant."""
    print("="*60)
    print("Testing Connection")
    print("="*60)

    try:
        success = await client.test_connection()
        if success:
            print("✓ Connection successful")
            return True
        else:
            print("✗ Connection failed")
            return False
    except AuthenticationError:
        print("✗ Authentication failed - check your token")
        return False
    except ConnectionError as e:
        print(f"✗ Connection error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


async def test_get_states(client: HomeAssistantClient):
    """Test fetching and filtering entities."""
    print("\n" + "="*60)
    print("Testing Entity Retrieval")
    print("="*60)

    try:
        entities = await client.get_states(use_cache=False)
        print(f"✓ Fetched {len(entities)} entities (after filtering)")

        # Show cache info
        cache_age = client.get_cache_age()
        if cache_age is not None:
            print(f"  Cache age: {cache_age:.1f} seconds")

        # Show some example entities
        if entities:
            print(f"\nFirst 5 entities:")
            for i, entity in enumerate(entities[:5], 1):
                entity_id = entity.get('entity_id', 'unknown')
                state = entity.get('state', 'unknown')
                friendly_name = entity.get('attributes', {}).get('friendly_name', '')
                numeric_id = client.get_numeric_id(entity_id)
                print(f"  {numeric_id}. {entity_id} = {state}")
                if friendly_name:
                    print(f"     ({friendly_name})")

        return True

    except Exception as e:
        print(f"✗ Error fetching entities: {e}")
        return False


async def test_get_by_domain(client: HomeAssistantClient):
    """Test filtering by domain."""
    print("\n" + "="*60)
    print("Testing Domain Filtering")
    print("="*60)

    domains = ['light', 'switch', 'sensor', 'automation']

    for domain in domains:
        try:
            entities = await client.get_by_domain(domain, use_cache=True)
            print(f"  {domain}: {len(entities)} entities")

            # Show first entity if available
            if entities:
                entity = entities[0]
                entity_id = entity.get('entity_id', 'unknown')
                state = entity.get('state', 'unknown')
                print(f"    Example: {entity_id} = {state}")

        except Exception as e:
            print(f"  {domain}: Error - {e}")

    return True


async def test_entity_operations(client: HomeAssistantClient, entity_id: str):
    """Test turning an entity on/off."""
    print("\n" + "="*60)
    print(f"Testing Entity Operations: {entity_id}")
    print("="*60)

    try:
        # Get initial state
        print(f"\n1. Getting initial state...")
        initial_state = await client.get_state(entity_id)
        initial_value = initial_state.get('state', 'unknown')
        print(f"   Initial state: {initial_value}")

        # Turn on
        print(f"\n2. Turning on...")
        await client.turn_on(entity_id)
        print(f"   ✓ Turn on command sent")

        # Wait a moment
        await asyncio.sleep(1)

        # Check state
        state = await client.get_state(entity_id)
        current_value = state.get('state', 'unknown')
        print(f"   Current state: {current_value}")

        # Turn off
        print(f"\n3. Turning off...")
        await client.turn_off(entity_id)
        print(f"   ✓ Turn off command sent")

        # Wait a moment
        await asyncio.sleep(1)

        # Check state
        state = await client.get_state(entity_id)
        current_value = state.get('state', 'unknown')
        print(f"   Current state: {current_value}")

        print(f"\n✓ Entity operations test complete")
        return True

    except Exception as e:
        print(f"✗ Error during entity operations: {e}")
        return False


async def test_automation(client: HomeAssistantClient, automation_id: str):
    """Test triggering an automation."""
    print("\n" + "="*60)
    print(f"Testing Automation: {automation_id}")
    print("="*60)

    try:
        print(f"Triggering automation...")
        await client.trigger_automation(automation_id)
        print(f"✓ Automation triggered successfully")
        return True

    except Exception as e:
        print(f"✗ Error triggering automation: {e}")
        return False


async def test_numeric_id_lookup(client: HomeAssistantClient):
    """Test numeric ID mapping."""
    print("\n" + "="*60)
    print("Testing Numeric ID Mapping")
    print("="*60)

    # Get entities to populate mapper
    entities = await client.get_states(use_cache=True)

    if not entities:
        print("No entities available for testing")
        return False

    # Test ID lookup
    entity = entities[0]
    entity_id = entity.get('entity_id', '')

    numeric_id = client.get_numeric_id(entity_id)
    print(f"Entity: {entity_id}")
    print(f"Numeric ID: {numeric_id}")

    # Test reverse lookup
    if numeric_id:
        looked_up = client.get_entity_by_id(numeric_id)
        if looked_up:
            looked_up_id = looked_up.get('entity_id', '')
            print(f"Reverse lookup: {looked_up_id}")

            if looked_up_id == entity_id:
                print("✓ Numeric ID mapping works correctly")
                return True
            else:
                print("✗ Numeric ID mapping mismatch")
                return False

    return False


async def interactive_mode(client: HomeAssistantClient):
    """Interactive mode for manual testing."""
    print("\n" + "="*60)
    print("Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  list [domain]  - List entities (optionally filtered by domain)")
    print("  get <id>       - Get entity state by numeric or full ID")
    print("  on <id>        - Turn entity on")
    print("  off <id>       - Turn entity off")
    print("  toggle <id>    - Toggle entity")
    print("  auto           - List automations")
    print("  trigger <id>   - Trigger automation")
    print("  refresh        - Refresh entity cache")
    print("  quit           - Exit")
    print()

    # Initial fetch
    await client.get_states(use_cache=False)

    while True:
        try:
            cmd = input("> ").strip().lower()

            if not cmd:
                continue

            parts = cmd.split()
            command = parts[0]

            if command == 'quit' or command == 'q':
                break

            elif command == 'list' or command == 'l':
                domain = parts[1] if len(parts) > 1 else None

                if domain:
                    entities = await client.get_by_domain(domain, use_cache=True)
                else:
                    entities = await client.get_states(use_cache=True)

                print(f"\nFound {len(entities)} entities:")
                for entity in entities[:20]:  # Show first 20
                    entity_id = entity.get('entity_id', 'unknown')
                    state = entity.get('state', 'unknown')
                    numeric_id = client.get_numeric_id(entity_id)
                    friendly_name = entity.get('attributes', {}).get('friendly_name', '')

                    if friendly_name:
                        print(f"  {numeric_id}. {friendly_name} [{state}]")
                        print(f"     ({entity_id})")
                    else:
                        print(f"  {numeric_id}. {entity_id} [{state}]")

                if len(entities) > 20:
                    print(f"  ... and {len(entities) - 20} more")

            elif command == 'get':
                if len(parts) < 2:
                    print("Usage: get <id>")
                    continue

                entity_ref = parts[1]

                # Try as numeric ID first
                if entity_ref.isdigit():
                    entity = client.get_entity_by_id(int(entity_ref))
                    if not entity:
                        print(f"Entity ID {entity_ref} not found")
                        continue
                    entity_id = entity.get('entity_id', '')
                else:
                    entity_id = entity_ref

                state = await client.get_state(entity_id)
                print(f"\n{entity_id}:")
                print(f"  State: {state.get('state', 'unknown')}")

                attributes = state.get('attributes', {})
                if 'friendly_name' in attributes:
                    print(f"  Name: {attributes['friendly_name']}")
                if 'brightness' in attributes:
                    pct = int(attributes['brightness'] / 255 * 100)
                    print(f"  Brightness: {pct}%")
                if 'position' in attributes:
                    print(f"  Position: {attributes['position']}%")
                if 'temperature' in attributes:
                    print(f"  Temperature: {attributes['temperature']}")

            elif command in ('on', 'off', 'toggle'):
                if len(parts) < 2:
                    print(f"Usage: {command} <id>")
                    continue

                entity_ref = parts[1]

                # Try as numeric ID first
                if entity_ref.isdigit():
                    entity = client.get_entity_by_id(int(entity_ref))
                    if not entity:
                        print(f"Entity ID {entity_ref} not found")
                        continue
                    entity_id = entity.get('entity_id', '')
                else:
                    entity_id = entity_ref

                if command == 'on':
                    await client.turn_on(entity_id)
                    print(f"✓ {entity_id} turned on")
                elif command == 'off':
                    await client.turn_off(entity_id)
                    print(f"✓ {entity_id} turned off")
                elif command == 'toggle':
                    await client.toggle(entity_id)
                    print(f"✓ {entity_id} toggled")

            elif command == 'auto' or command == 'a':
                automations = await client.get_automations(use_cache=True)
                print(f"\nFound {len(automations)} automations:")
                for auto in automations:
                    auto_id = auto.get('entity_id', 'unknown')
                    state = auto.get('state', 'unknown')
                    numeric_id = client.get_numeric_id(auto_id)
                    friendly_name = auto.get('attributes', {}).get('friendly_name', '')

                    print(f"  {numeric_id}. {friendly_name or auto_id} [{state}]")

            elif command == 'trigger' or command == 't':
                if len(parts) < 2:
                    print("Usage: trigger <id>")
                    continue

                entity_ref = parts[1]

                # Try as numeric ID first
                if entity_ref.isdigit():
                    entity = client.get_entity_by_id(int(entity_ref))
                    if not entity:
                        print(f"Automation ID {entity_ref} not found")
                        continue
                    auto_id = entity.get('entity_id', '')
                else:
                    auto_id = entity_ref

                await client.trigger_automation(auto_id)
                print(f"✓ {auto_id} triggered")

            elif command == 'refresh' or command == 'r':
                count = await client.refresh_cache()
                print(f"✓ Cache refreshed ({count} entities)")

            else:
                print(f"Unknown command: {command}")

        except KeyboardInterrupt:
            print("\nInterrupted")
            break
        except Exception as e:
            print(f"Error: {e}")


async def run_tests(
    config_file: str,
    test_entity: str = None,
    test_automation: str = None,
    interactive: bool = False
):
    """Run all tests."""
    # Load configuration
    config = load_config(config_file)

    # Create client
    client = HomeAssistantClient.from_config(config)

    try:
        # Test connection
        if not await test_connection(client):
            print("\n✗ Connection test failed. Cannot proceed.")
            return False

        # Test getting states
        if not await test_get_states(client):
            print("\n✗ Entity retrieval test failed.")
            return False

        # Test domain filtering
        await test_get_by_domain(client)

        # Test numeric ID mapping
        await test_numeric_id_lookup(client)

        # Test entity operations if specified
        if test_entity:
            await test_entity_operations(client, test_entity)

        # Test automation if specified
        if test_automation:
            await test_automation(client, test_automation)

        # Interactive mode
        if interactive:
            await interactive_mode(client)

        print("\n" + "="*60)
        print("All tests complete!")
        print("="*60)

        return True

    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH HomeAssistant client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic connection and entity test
  python test_ha.py

  # Test with specific entity control
  python test_ha.py --entity light.kitchen

  # Test automation triggering
  python test_ha.py --automation automation.good_night

  # Interactive mode
  python test_ha.py --interactive

  # Custom config file
  python test_ha.py --config my_config.yaml
        """
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    parser.add_argument(
        '--entity',
        help='Test entity operations on specific entity (e.g., light.kitchen)'
    )
    parser.add_argument(
        '--automation',
        help='Test triggering specific automation (e.g., automation.good_night)'
    )
    parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help='Run in interactive mode'
    )

    args = parser.parse_args()

    # Run async tests
    success = asyncio.run(run_tests(
        config_file=args.config,
        test_entity=args.entity,
        test_automation=args.automation,
        interactive=args.interactive
    ))

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
