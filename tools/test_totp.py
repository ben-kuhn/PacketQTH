#!/usr/bin/env python3
"""
PacketQTH TOTP Test Tool

Test TOTP authentication with automated or interactive modes.
"""

import sys
import os
import argparse
import pyotp

# Add parent directory to path to import auth module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.totp import TOTPAuthenticator, SessionManager


def test_automated(users_file: str):
    """
    Automated test mode.

    Tests TOTP authentication by generating valid codes from users.yaml secrets.
    """
    print("="*60)
    print("PacketQTH TOTP - Automated Test Mode")
    print("="*60)

    # Initialize authenticator
    auth = TOTPAuthenticator(users_file)

    if not auth.users:
        print("❌ No users found in users.yaml")
        print("   Run: python tools/setup_totp.py CALLSIGN")
        return False

    print(f"\nFound {len(auth.users)} user(s) in {users_file}")

    all_passed = True

    for callsign, secret in auth.users.items():
        print(f"\n{'─'*60}")
        print(f"Testing: {callsign}")
        print(f"{'─'*60}")

        # Generate current valid TOTP code
        totp = pyotp.TOTP(secret)
        token = totp.now()

        print(f"Generated token: {token}")

        # Test authentication
        success, message = auth.verify_totp(callsign, token)

        if success:
            print(f"✓ {message}")
        else:
            print(f"❌ {message}")
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60)

    return all_passed


def test_interactive(users_file: str):
    """
    Interactive test mode.

    Prompts user to enter callsign and TOTP code from their authenticator app.
    """
    print("="*60)
    print("PacketQTH TOTP - Interactive Test Mode")
    print("="*60)
    print()
    print("This simulates the authentication flow users will experience")
    print("when connecting via packet radio.")
    print()

    # Initialize authenticator and session manager
    auth = TOTPAuthenticator(users_file)
    sessions = SessionManager(timeout_minutes=30)

    if not auth.users:
        print("❌ No users found in users.yaml")
        print("   Run: python tools/setup_totp.py CALLSIGN")
        return False

    print(f"Available callsigns: {', '.join(auth.users.keys())}")
    print()

    # Get callsign
    callsign = input("Enter callsign: ").strip().upper()

    if not callsign:
        print("❌ Callsign required")
        return False

    # Get TOTP token
    token = input("Enter 6-digit TOTP code from authenticator: ").strip()

    if not token or len(token) != 6:
        print("❌ Invalid token format (must be 6 digits)")
        return False

    # Verify
    print()
    print("Authenticating...")
    success, message = auth.verify_totp(callsign, token)

    print()
    if success:
        print(f"✓ {message}")

        # Create session
        session_id = sessions.create_session(callsign)
        session = sessions.get_session(session_id)

        print(f"\nSession created:")
        print(f"  Session ID: {session_id}")
        print(f"  Callsign: {session.callsign}")
        print(f"  Authenticated: {session.authenticated_at}")
        print(f"  Timeout: {30} minutes")
        print()
        print("✓ Ready to connect to HomeAssistant!")
    else:
        print(f"❌ {message}")

        # Check if rate limited
        if auth.is_rate_limited(callsign):
            print("\n⚠️  Rate limit active: Too many failed attempts")
            print("   Wait 5 minutes before trying again")

    print()
    return success


def test_rate_limiting(users_file: str):
    """Test rate limiting functionality"""
    print("="*60)
    print("PacketQTH TOTP - Rate Limiting Test")
    print("="*60)
    print()

    auth = TOTPAuthenticator(users_file)

    if not auth.users:
        print("❌ No users found in users.yaml")
        return False

    # Get first user
    callsign = list(auth.users.keys())[0]

    print(f"Testing rate limiting for: {callsign}")
    print(f"Attempting 6 failed authentications...\n")

    # Try 6 invalid tokens
    for i in range(1, 7):
        success, message = auth.verify_totp(callsign, "000000")

        is_limited = auth.is_rate_limited(callsign)
        status = "RATE LIMITED" if is_limited else "allowed"

        print(f"Attempt {i}: {message} [{status}]")

        if i == 5:
            print("\n⚠️  After 5 failed attempts, rate limiting should activate...")
            print()

    print("\n✓ Rate limiting test complete")
    print("  (Failed attempts cleared after 5 minutes)")
    print()

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH TOTP authentication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  --automated    Generate tokens from users.yaml and test (default)
  --interactive  Manual testing with authenticator app
  --rate-limit   Test rate limiting functionality

Examples:
  # Automated test (generates codes from secrets)
  python test_totp.py --automated

  # Interactive test (use authenticator app)
  python test_totp.py --interactive

  # Test rate limiting
  python test_totp.py --rate-limit
        """
    )

    parser.add_argument(
        '--automated',
        action='store_true',
        help='Automated test mode (generates valid codes)'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive test mode (manual token entry)'
    )
    parser.add_argument(
        '--rate-limit',
        action='store_true',
        help='Test rate limiting functionality'
    )
    parser.add_argument(
        '--users-file',
        default='users.yaml',
        help='Path to users.yaml file (default: users.yaml)'
    )

    args = parser.parse_args()

    # Determine test mode (default to automated)
    if args.interactive:
        success = test_interactive(args.users_file)
    elif args.rate_limit:
        success = test_rate_limiting(args.users_file)
    else:
        success = test_automated(args.users_file)

    print()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
