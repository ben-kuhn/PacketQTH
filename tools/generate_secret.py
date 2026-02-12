#!/usr/bin/env python3
"""
Simple TOTP Secret Generator (No Dependencies)

Generates a TOTP secret for manual entry into authenticator apps.
No external dependencies required - uses only Python standard library.
"""

import secrets
import base64
import sys


def generate_secret():
    """Generate a random TOTP secret (Base32 encoded)."""
    # Generate 20 random bytes (160 bits)
    random_bytes = secrets.token_bytes(20)

    # Encode as Base32 (RFC 4648)
    secret = base64.b32encode(random_bytes).decode('ascii').rstrip('=')

    return secret


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_secret.py <CALLSIGN>")
        print("")
        print("Example:")
        print("  python generate_secret.py KN4XYZ")
        print("")
        sys.exit(1)

    callsign = sys.argv[1].upper()

    # Generate secret
    secret = generate_secret()

    # Generate provisioning URI (for manual entry)
    issuer = "PacketQTH"
    uri = f"otpauth://totp/{callsign}?secret={secret}&issuer={issuer}"

    # Display results
    print("=" * 70)
    print(f"TOTP Setup for {callsign}")
    print("=" * 70)
    print("")
    print("Generated TOTP Secret:")
    print(f"  {secret}")
    print("")
    print("Manual Entry Instructions:")
    print("  1. Open your authenticator app (Google Authenticator, Authy, etc.)")
    print("  2. Tap '+' or 'Add account'")
    print("  3. Choose 'Enter a setup key' or 'Manual entry'")
    print("  4. Enter these details:")
    print(f"     Account name: {issuer} - {callsign}")
    print(f"     Key: {secret}")
    print("     Time-based: Yes")
    print("     Algorithm: SHA1")
    print("     Digits: 6")
    print("     Period: 30 seconds")
    print("")
    print("Or use this URI (for QR code generators):")
    print(f"  {uri}")
    print("")
    print("Add to users.yaml:")
    print("  users:")
    print(f"    {callsign}: \"{secret}\"")
    print("")
    print("=" * 70)


if __name__ == '__main__':
    main()
