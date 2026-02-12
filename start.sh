#!/bin/bash
# PacketQTH Quick Start Script

set -e

echo "PacketQTH - HomeAssistant for Packet Radio"
echo "=========================================="
echo

# Check for config file
if [ ! -f "config.yaml" ]; then
    echo "ERROR: config.yaml not found"
    echo "Copy config.yaml.example to config.yaml and customize it"
    exit 1
fi

# Check for users file
if [ ! -f "users.yaml" ]; then
    echo "ERROR: users.yaml not found"
    echo "Copy users.yaml.example to users.yaml and add your users"
    exit 1
fi

# Check for HA_TOKEN
if [ -z "$HA_TOKEN" ]; then
    echo "WARNING: HA_TOKEN environment variable not set"
    echo "Set it via: export HA_TOKEN=your_token"
    echo "Or add it to config.yaml"
    echo
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Check for dependencies
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "Installing core dependencies..."
    pip3 install -r requirements.txt
    echo
    echo "Note: For TOTP setup tools, also install: pip3 install -r requirements-tools.txt"
    echo
fi

# Start the application
echo "Starting PacketQTH..."
python3 main.py
