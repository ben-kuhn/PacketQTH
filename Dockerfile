FROM python:3.11-slim

# Metadata
LABEL maintainer="PacketQTH Project"
LABEL description="HomeAssistant Packet Radio Interface"
LABEL version="0.1.0"

# Create non-root user
RUN useradd -m -u 1000 packetqth && \
    mkdir -p /app /app/logs && \
    chown -R packetqth:packetqth /app

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY --chown=packetqth:packetqth . .

# Drop to non-root user
USER packetqth

# Expose telnet port
EXPOSE 8023

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 8023)); s.close()" || exit 1

# Run application
CMD ["python", "main.py"]
