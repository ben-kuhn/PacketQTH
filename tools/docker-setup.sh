#!/bin/bash
# PacketQTH Docker TOTP Setup Script
# Generates TOTP secrets using Docker (no host dependencies needed)

set -e

CALLSIGN=$1
QR_FILE=$2

if [ -z "$CALLSIGN" ]; then
    echo "Usage: $0 <CALLSIGN> [qr-filename]"
    echo ""
    echo "Examples:"
    echo "  $0 KN4XYZ                    # Display QR in terminal"
    echo "  $0 KN4XYZ qr.png             # Save QR to file"
    echo ""
    exit 1
fi

echo "PacketQTH Docker TOTP Setup"
echo "============================"
echo ""
echo "Generating TOTP secret for: $CALLSIGN"
echo ""

# Build setup image if needed
if ! docker image inspect packetqth-setup:latest &>/dev/null; then
    echo "Building setup tools image..."
    docker build -f- -t packetqth-setup:latest . <<EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements-tools.txt .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements-tools.txt
COPY tools/setup_totp.py tools/
COPY auth/ auth/
CMD ["python", "tools/setup_totp.py"]
EOF
    echo ""
fi

# Run setup tool in container
if [ -z "$QR_FILE" ]; then
    # Terminal QR code (no file)
    docker run --rm -it packetqth-setup:latest python tools/setup_totp.py "$CALLSIGN"
else
    # QR code to file (mount current directory)
    docker run --rm -it \
        -v "$(pwd):/output" \
        packetqth-setup:latest \
        python tools/setup_totp.py "$CALLSIGN" --qr-file "/output/$QR_FILE"

    if [ -f "$QR_FILE" ]; then
        echo ""
        echo "QR code saved to: $QR_FILE"
    fi
fi

echo ""
echo "Next steps:"
echo "1. Scan the QR code with your authenticator app"
echo "2. Add the TOTP secret to users.yaml"
echo "3. Run: docker-compose up -d"
echo ""
