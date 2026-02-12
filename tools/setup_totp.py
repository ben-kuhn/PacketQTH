#!/usr/bin/env python3
"""
PacketQTH TOTP Setup Tool

Generate TOTP secrets and QR codes for new users.
"""

import pyotp
import argparse
import sys

# QR code generation is optional (requires qrcode[pil] package)
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("Warning: qrcode module not found. QR code generation disabled.", file=sys.stderr)
    print("Install with: pip install qrcode[pil]", file=sys.stderr)
    print("Or: pip install -r requirements-tools.txt", file=sys.stderr)
    print()


def generate_totp_secret(callsign: str, issuer: str = "PacketQTH") -> tuple:
    """
    Generate a TOTP secret for a user.

    Args:
        callsign: Ham radio callsign
        issuer: Issuer name for authenticator apps

    Returns:
        Tuple of (secret, provisioning_uri)
    """
    # Generate a random base32 secret
    secret = pyotp.random_base32()

    # Create TOTP instance
    totp = pyotp.TOTP(secret)

    # Generate provisioning URI for QR code
    uri = totp.provisioning_uri(
        name=callsign.upper(),
        issuer_name=issuer
    )

    return secret, uri


def print_qr_terminal(uri: str):
    """Print QR code to terminal"""
    if not QRCODE_AVAILABLE:
        print("QR code generation not available (qrcode module not installed)")
        print(f"Manual setup URI: {uri}")
        return

    qr = qrcode.QRCode()
    qr.add_data(uri)
    qr.print_ascii(invert=True)


def save_qr_image(uri: str, filename: str):
    """Save QR code as PNG image"""
    if not QRCODE_AVAILABLE:
        print(f"Error: Cannot save QR code - qrcode module not installed")
        print(f"Install with: pip install qrcode[pil]")
        return False

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"✓ QR code saved to: {filename}")
    return True


def print_config_entry(callsign: str, secret: str):
    """Print the YAML configuration to add to users.yaml"""
    print("\n" + "="*60)
    print("Add this to your users.yaml file:")
    print("="*60)
    print(f"  {callsign.upper()}: \"{secret}\"")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate TOTP secrets for PacketQTH users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate secret and show QR in terminal
  python setup_totp.py KN4XYZ

  # Generate secret and save QR code to file
  python setup_totp.py KN4XYZ --qr-file qr_kn4xyz.png

  # Generate without QR code
  python setup_totp.py KN4XYZ --no-qr
        """
    )

    parser.add_argument(
        'callsign',
        help='Ham radio callsign for the new user'
    )
    parser.add_argument(
        '--qr-file',
        help='Save QR code to PNG file instead of printing to terminal'
    )
    parser.add_argument(
        '--no-qr',
        action='store_true',
        help='Do not generate QR code (only show secret)'
    )
    parser.add_argument(
        '--issuer',
        default='PacketQTH',
        help='Issuer name for authenticator apps (default: PacketQTH)'
    )

    args = parser.parse_args()

    # Generate secret and URI
    secret, uri = generate_totp_secret(args.callsign, args.issuer)

    # Display secret information
    print(f"\n{'='*60}")
    print(f"TOTP Setup for {args.callsign.upper()}")
    print(f"{'='*60}")
    print(f"Secret: {secret}")
    print(f"\nProvisioning URI:")
    print(f"{uri}")

    # Generate QR code
    if not args.no_qr:
        print()
        if args.qr_file:
            save_qr_image(uri, args.qr_file)
            print("\nScan this QR code with Google Authenticator or similar app.")
        else:
            print("QR Code (scan with authenticator app):")
            print()
            print_qr_terminal(uri)

    # Print config entry
    print_config_entry(args.callsign, secret)

    print("\nNext steps:")
    print("1. Scan the QR code with an authenticator app (or enter secret manually)")
    print("2. Add the configuration entry to users.yaml")
    print("3. Test authentication with: python tools/test_totp.py")
    print("\n73!")


if __name__ == '__main__':
    main()
