#!/usr/bin/env python3
"""
PacketQTH BPQ Simulator

Simulates a LinBPQ connection to test BPQ mode.
Automatically sends callsign as first line (like BPQ does).
"""

import asyncio
import sys
import argparse


async def simulate_bpq_connection(
    host: str,
    port: int,
    callsign: str,
    interactive: bool = True
):
    """
    Simulate a LinBPQ connection to PacketQTH.

    Args:
        host: Server host
        port: Server port
        callsign: Callsign to send
        interactive: Enter interactive mode after auth
    """
    print(f"Simulating BPQ connection to {host}:{port}")
    print(f"Callsign: {callsign}")
    print("="*60)

    try:
        # Connect to server
        reader, writer = await asyncio.open_connection(host, port)

        print(f"Connected to {host}:{port}")

        # Read banner
        print("\n--- Server Banner ---")
        for _ in range(5):  # Read a few lines of banner
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=2)
                if not line:
                    break
                print(line.decode('utf-8', errors='replace').rstrip())
            except asyncio.TimeoutError:
                break

        # Send callsign (BPQ does this automatically)
        print(f"\n>>> Sending callsign: {callsign}")
        writer.write(f"{callsign}\r\n".encode('utf-8'))
        await writer.drain()

        # Read response (should be TOTP prompt)
        line = await asyncio.wait_for(reader.readline(), timeout=5)
        prompt = line.decode('utf-8', errors='replace').rstrip()
        print(f"<<< {prompt}")

        if interactive:
            # Interactive mode - let user type
            print("\n--- Interactive Mode ---")
            print("Type your TOTP code and press Enter")
            print("After authentication, you can send commands")
            print("Type 'Q' to quit")
            print()

            # Create tasks for reading from server and stdin
            async def read_from_server():
                try:
                    while True:
                        line = await reader.readline()
                        if not line:
                            print("\n[Connection closed by server]")
                            break
                        print(line.decode('utf-8', errors='replace').rstrip())
                except Exception as e:
                    print(f"\n[Error reading from server: {e}]")

            async def read_from_stdin():
                try:
                    while True:
                        # Read from stdin (blocking)
                        user_input = await asyncio.get_event_loop().run_in_executor(
                            None, sys.stdin.readline
                        )
                        if not user_input:
                            break

                        # Send to server
                        writer.write(user_input.encode('utf-8'))
                        await writer.drain()

                        # Check for quit
                        if user_input.strip().upper() in ('Q', 'QUIT', 'EXIT'):
                            break
                except Exception as e:
                    print(f"\n[Error reading stdin: {e}]")

            # Run both tasks concurrently
            server_task = asyncio.create_task(read_from_server())
            stdin_task = asyncio.create_task(read_from_stdin())

            # Wait for either to complete
            done, pending = await asyncio.wait(
                [server_task, stdin_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        else:
            # Non-interactive mode - just show what happens
            print("\n--- Server Response ---")
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=2)
                    if not line:
                        break
                    print(line.decode('utf-8', errors='replace').rstrip())
                except asyncio.TimeoutError:
                    break

        # Close connection
        writer.close()
        await writer.wait_closed()

        print("\n" + "="*60)
        print("Connection closed")

    except ConnectionRefusedError:
        print(f"\nERROR: Connection refused. Is the server running on {host}:{port}?")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Simulate LinBPQ connection to PacketQTH server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool simulates how LinBPQ connects to PacketQTH:
1. Connects to the telnet port
2. Reads the banner
3. Automatically sends the callsign (no prompt)
4. Waits for TOTP prompt
5. Allows interactive input for testing

Examples:
  # Simulate BPQ connection with callsign TEST
  python simulate_bpq.py TEST

  # Connect to specific host/port
  python simulate_bpq.py KN4XYZ --host 192.168.1.100 --port 8023

  # Non-interactive (just show initial exchange)
  python simulate_bpq.py TEST --non-interactive

Testing BPQ Mode:
  1. Start PacketQTH server with bpq_mode: true
  2. Run: python simulate_bpq.py YOUR_CALLSIGN
  3. Enter TOTP code when prompted
  4. Test commands interactively

Testing Standard Mode:
  1. Start server with bpq_mode: false
  2. Run: python simulate_bpq.py YOUR_CALLSIGN
  3. Notice you get prompted for callsign (duplicate)
  4. This shows why bpq_mode should be true for BPQ
        """
    )

    parser.add_argument(
        'callsign',
        help='Callsign to send (simulates BPQ auto-send)'
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Server host (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8023,
        help='Server port (default: 8023)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Non-interactive mode (show initial exchange only)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(simulate_bpq_connection(
            host=args.host,
            port=args.port,
            callsign=args.callsign.upper(),
            interactive=not args.non_interactive
        ))
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
