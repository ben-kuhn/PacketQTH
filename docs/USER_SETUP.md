# User Setup: Generating TOTP Secrets

Each PacketQTH user needs a TOTP secret registered in `users.yaml`. Choose the method that best fits your environment.

## Option A: Tools Image (Recommended — no host dependencies)

Uses the pre-built tools container. Prints the secret and an ASCII QR code to your terminal.

```bash
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN
```

**Save QR code as a PNG file** (requires a host directory mount):

```bash
# Podman (rootless):
podman run --rm --userns=keep-id -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png

# Docker:
docker run --rm --user $(id -u):$(id -g) -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png
```

## Option B: Build the Tools Image Locally

If you prefer not to pull from the registry:

```bash
docker build -f Dockerfile.tools -t packetqth-tools:local .
docker run --rm -it packetqth-tools:local python tools/setup_totp.py YOUR_CALLSIGN
```

Or use the convenience script:

```bash
./tools/docker-setup.sh YOUR_CALLSIGN
```

## Option C: Python Standard Library Only (No Dependencies)

Generates a secret without any pip packages. Outputs a setup key for manual entry into your authenticator app — no QR code.

```bash
python3 tools/generate_secret.py YOUR_CALLSIGN
```

## Option D: Run Locally with Packages

If you have Python and the tools dependencies installed on the host:

```bash
pip3 install -r requirements-tools.txt
python3 tools/setup_totp.py YOUR_CALLSIGN
```

---

## Adding the Secret to users.yaml

After generating a secret, add it to `users.yaml`:

```yaml
users:
  KN4XYZ: "JBSWY3DPEHPK3PXP"
  W1ABC: "HXDMVJECJJWSRB3H"
```

Each key is the callsign (uppercase); the value is the base32 TOTP secret shown by the setup tool.

Restart the server after editing `users.yaml`:

```bash
docker compose restart
```
