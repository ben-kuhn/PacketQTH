#!/usr/bin/env python3
"""
PacketQTH IP Safelist Test Tool

Test IP safelist configuration and CIDR notation parsing.
"""

import sys
import os
import ipaddress
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_safelist(safelist_entries, test_ips):
    """
    Test IP addresses against a safelist.

    Args:
        safelist_entries: List of IP/CIDR entries
        test_ips: List of IP addresses to test
    """
    print("="*60)
    print("IP Safelist Test")
    print("="*60)

    # Parse safelist
    safelist_networks = []
    print("\nParsing safelist entries:")
    for entry in safelist_entries:
        try:
            network = ipaddress.ip_network(entry, strict=False)
            safelist_networks.append(network)
            print(f"  ✓ {entry} → {network}")
        except ValueError as e:
            print(f"  ✗ {entry} → ERROR: {e}")

    if not safelist_networks:
        print("\n⚠️  Empty safelist - all IPs would be allowed")
        return

    # Test IPs
    print(f"\nTesting {len(test_ips)} IP address(es):")
    print("-"*60)

    for test_ip in test_ips:
        try:
            ip = ipaddress.ip_address(test_ip)
            allowed = False
            matching_network = None

            # Check against each network in safelist
            for network in safelist_networks:
                if ip in network:
                    allowed = True
                    matching_network = network
                    break

            status = "✓ ALLOWED" if allowed else "✗ REJECTED"
            match_info = f" (matches {matching_network})" if matching_network else ""

            print(f"  {test_ip:20s} → {status}{match_info}")

        except ValueError as e:
            print(f"  {test_ip:20s} → ERROR: {e}")

    print("-"*60)


def main():
    parser = argparse.ArgumentParser(
        description='Test PacketQTH IP safelist configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test specific IPs against a safelist
  python test_safelist.py \\
    --safelist 192.168.1.0/24 10.0.0.5 \\
    --test 192.168.1.100 10.0.0.5 8.8.8.8

  # Test local network
  python test_safelist.py \\
    --safelist 192.168.0.0/16 \\
    --test 192.168.1.1 192.168.100.50 10.0.0.1

  # Test IPv6
  python test_safelist.py \\
    --safelist 2001:db8::/32 \\
    --test 2001:db8::1 2001:db8:1::1 2001:db9::1

  # Interactive mode (prompts for input)
  python test_safelist.py --interactive

Common CIDR blocks:
  192.168.1.0/24     - 192.168.1.0 to 192.168.1.255 (256 IPs)
  192.168.0.0/16     - 192.168.0.0 to 192.168.255.255 (65,536 IPs)
  10.0.0.0/8         - 10.0.0.0 to 10.255.255.255 (16M IPs)
  127.0.0.1/32       - Single IP (127.0.0.1 only)
        """
    )

    parser.add_argument(
        '--safelist',
        nargs='+',
        help='IP addresses or CIDR networks for safelist'
    )
    parser.add_argument(
        '--test',
        nargs='+',
        help='IP addresses to test against safelist'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode (prompt for input)'
    )

    args = parser.parse_args()

    if args.interactive:
        # Interactive mode
        print("="*60)
        print("IP Safelist Test - Interactive Mode")
        print("="*60)
        print()

        # Get safelist entries
        print("Enter safelist entries (IP addresses or CIDR networks)")
        print("Press Enter on empty line when done:")
        safelist_entries = []
        while True:
            entry = input(f"  Entry {len(safelist_entries) + 1}: ").strip()
            if not entry:
                break
            safelist_entries.append(entry)

        if not safelist_entries:
            print("\n⚠️  No safelist entries provided!")
            return

        # Get test IPs
        print("\nEnter IP addresses to test")
        print("Press Enter on empty line when done:")
        test_ips = []
        while True:
            ip = input(f"  Test IP {len(test_ips) + 1}: ").strip()
            if not ip:
                break
            test_ips.append(ip)

        if not test_ips:
            print("\n⚠️  No test IPs provided!")
            return

        print()
        test_safelist(safelist_entries, test_ips)

    elif args.safelist and args.test:
        # Command-line mode
        test_safelist(args.safelist, args.test)

    else:
        parser.print_help()
        print("\nError: Provide --safelist and --test, or use --interactive")
        sys.exit(1)


if __name__ == '__main__':
    main()
