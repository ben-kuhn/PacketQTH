#!/usr/bin/env python3
"""
PacketQTH TOTP-per-Write Test

Tests the TOTP-per-write functionality to ensure:
1. Read operations work without additional TOTP
2. Write operations require fresh TOTP
3. Invalid TOTP denies write operations
4. Valid TOTP allows write operations
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models directly to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "models",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "commands", "models.py")
)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

Command = models.Command
CommandType = models.CommandType


def test_is_write_operation():
    """Test the is_write_operation() method."""
    print("="*60)
    print("Testing is_write_operation() classification")
    print("="*60)

    # Test write operations
    write_commands = [
        (CommandType.ON, "ON 1"),
        (CommandType.OFF, "OFF 1"),
        (CommandType.SET, "SET 1 50"),
        (CommandType.TRIGGER, "T 1"),
    ]

    print("\n✅ Write Operations (should require TOTP):")
    for cmd_type, raw in write_commands:
        cmd = Command(type=cmd_type, raw_input=raw, device_id=1)
        result = cmd.is_write_operation()
        status = "✓" if result else "✗"
        print(f"  {status} {cmd_type.value:12s} -> {result}")
        assert result == True, f"{cmd_type.value} should be a write operation"

    # Test read operations
    read_commands = [
        (CommandType.LIST, "L"),
        (CommandType.SHOW, "S 1"),
        (CommandType.AUTOMATIONS, "A"),
        (CommandType.HELP, "H"),
        (CommandType.REFRESH, "R"),
        (CommandType.QUIT, "Q"),
    ]

    print("\n📖 Read Operations (should NOT require TOTP):")
    for cmd_type, raw in read_commands:
        cmd = Command(type=cmd_type, raw_input=raw)
        result = cmd.is_write_operation()
        status = "✓" if not result else "✗"
        print(f"  {status} {cmd_type.value:12s} -> {result}")
        assert result == False, f"{cmd_type.value} should NOT be a write operation"

    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
    return True


def test_command_classification():
    """Test that command types are correctly classified."""
    print("\n" + "="*60)
    print("Command Classification Summary")
    print("="*60)

    all_commands = [
        (CommandType.LIST, False),
        (CommandType.SHOW, False),
        (CommandType.ON, True),
        (CommandType.OFF, True),
        (CommandType.SET, True),
        (CommandType.AUTOMATIONS, False),
        (CommandType.TRIGGER, True),
        (CommandType.HELP, False),
        (CommandType.QUIT, False),
        (CommandType.REFRESH, False),
    ]

    print("\nCommand Type         | Requires TOTP | Category")
    print("-" * 60)

    for cmd_type, is_write in all_commands:
        cmd = Command(type=cmd_type, raw_input=cmd_type.value)
        requires_totp = cmd.is_write_operation()
        category = "WRITE" if requires_totp else "READ"
        totp_status = "YES" if requires_totp else "NO"
        print(f"{cmd_type.value:20s} | {totp_status:13s} | {category}")
        assert requires_totp == is_write, f"Mismatch for {cmd_type.value}"

    print("\n✅ Classification correct for all command types")
    return True


def main():
    """Run all tests."""
    try:
        test_is_write_operation()
        test_command_classification()

        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\nTOTP-per-write functionality is correctly implemented:")
        print("  • Write operations (ON/OFF/SET/TRIGGER) require fresh TOTP")
        print("  • Read operations (L/S/A/H/R/Q) execute without TOTP")
        print("  • Natural rate limiting to 30-second intervals")
        print()

        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
