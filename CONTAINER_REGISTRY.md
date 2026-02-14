# Container Registry Guide

PacketQTH automatically publishes two Docker images to GitHub Container Registry (ghcr.io):

1. **Runtime Image** - Minimal dependencies for running the server
2. **Tools Image** - Includes QR code support for TOTP setup

## Using Published Images

### Quick Start

**Runtime image (running the server):**
```bash
# Pull the latest image
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Run with docker-compose (uses pre-built image by default)
docker-compose up -d
```

**Tools image (TOTP setup):**
```bash
# Generate TOTP secret with QR code
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN

# Save QR code to file
docker run --rm -v $(pwd):/output \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN --qr-file /output/qr.png
```

### Available Images

#### Runtime Image

**Image URL:** `ghcr.io/ben-kuhn/packetqth`

Minimal image for running the PacketQTH server (~200KB dependencies).

**Available tags:**
| Tag | Description | Example |
|-----|-------------|---------|
| `latest` | Latest stable release | `ghcr.io/ben-kuhn/packetqth:latest` |
| `main` | Latest build from main branch | `ghcr.io/ben-kuhn/packetqth:main` |
| `1.0.0` | Specific version | `ghcr.io/ben-kuhn/packetqth:1.0.0` |
| `1.0` | Latest patch for major.minor | `ghcr.io/ben-kuhn/packetqth:1.0` |
| `1` | Latest minor for major | `ghcr.io/ben-kuhn/packetqth:1` |
| `main-abc123` | Specific commit from main | `ghcr.io/ben-kuhn/packetqth:main-abc123` |

#### Tools Image

**Image URL:** `ghcr.io/ben-kuhn/packetqth-tools`

Includes tools dependencies (qrcode, Pillow) for TOTP setup with QR codes (~3MB extra).

**Available tags:** Same as runtime image (latest, main, version tags, etc.)

**When to use:**
- Generating TOTP secrets with QR codes
- Running security audits
- Development and testing

### Platform Support

All images are multi-platform and work on:
- **AMD64** (x86_64) - Standard servers, desktops
- **ARM64** (aarch64) - Raspberry Pi 4, Apple M1/M2, AWS Graviton
- **ARMv7** - Raspberry Pi 3

Docker automatically pulls the correct platform for your system.

## Usage Examples

### docker-compose (Recommended)

The default `docker-compose.yml` uses the pre-built image:

```yaml
services:
  packetqth:
    image: ghcr.io/ben-kuhn/packetqth:latest
    # ... rest of config
```

**Run:**
```bash
docker-compose up -d
```

### docker run

```bash
docker run -d \
  --name packetqth \
  -p 127.0.0.1:8023:8023 \
  -v ./config.yaml:/app/config.yaml:ro \
  -v ./users.yaml:/app/users.yaml:ro \
  -v ./logs:/app/logs \
  -e HA_TOKEN=your_token_here \
  --read-only \
  --tmpfs /tmp \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  ghcr.io/ben-kuhn/packetqth:latest
```

### Specific Version

Pin to a specific version for production:

```yaml
services:
  packetqth:
    image: ghcr.io/ben-kuhn/packetqth:1.0.0  # Pin to v1.0.0
```

### Development/Testing

Use the main branch for testing unreleased features:

```yaml
services:
  packetqth:
    image: ghcr.io/ben-kuhn/packetqth:main
```

## Updating

### Update to Latest

```bash
# Pull the new image
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Restart with the new image
docker-compose up -d
```

Docker Compose will automatically use the new image.

### Update to Specific Version

```bash
# Pull specific version
docker pull ghcr.io/ben-kuhn/packetqth:1.1.0

# Update docker-compose.yml to use 1.1.0
# Then restart
docker-compose up -d
```

### Automatic Updates

Use Watchtower for automatic updates:

```yaml
services:
  packetqth:
    image: ghcr.io/ben-kuhn/packetqth:latest
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 86400  # Check daily
```

## Building Locally

### When to Build Locally

Build locally if you:
- Want to modify the code
- Need to test changes before a release
- Prefer not to use pre-built images

### Building from Source

**Option 1: Using docker-compose.dev.yml**
```bash
# Uses docker-compose.dev.yml for local builds
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Option 2: Manual build**
```bash
# Build the image
docker build -t packetqth:local .

# Update docker-compose.yml to use local image
# image: packetqth:local

# Run
docker-compose up -d
```

**Option 3: Build in docker-compose.yml**
```yaml
services:
  packetqth:
    build: .
    image: packetqth:latest
```

## Image Details

### Size

**Runtime Image** (compressed):
- AMD64: ~150MB
- ARM64: ~145MB
- ARMv7: ~140MB

**Tools Image** (compressed):
- AMD64: ~180MB (+30MB for qrcode/Pillow)
- ARM64: ~175MB
- ARMv7: ~170MB

### Layers

**Runtime Image:**
- Base: `python:3.11-slim`
- Dependencies: Core requirements (~200KB)
- Application: Source code (~350KB)
- Total uncompressed: ~250MB

**Tools Image:**
- Base: `python:3.11-slim`
- Dependencies: Core + tools requirements (~3.2MB)
- Application: Source code (~350KB)
- Total uncompressed: ~280MB

### Security

**Hardening features:**
- Non-root user (UID 1000)
- Read-only root filesystem
- All capabilities dropped
- No new privileges
- Minimal base image (slim variant)

**Build attestation:**
- Each image has cryptographic build provenance
- Verifies the image was built by this repository
- Ensures supply chain integrity

## Permissions

### Making Images Public

By default, GitHub packages are private to the repository owner.

**To make images public:**
1. Go to https://github.com/ben-kuhn?tab=packages
2. Find `packetqth` package
3. Click on it → Settings
4. Change visibility to Public

### Pulling Private Images

If images are private, authenticate with GitHub:

```bash
# Create a GitHub Personal Access Token with read:packages scope
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull the image
docker pull ghcr.io/ben-kuhn/packetqth:latest
```

## Troubleshooting

### Pull Rate Limits

GitHub Container Registry has generous rate limits, but if you hit them:
- Authenticate with GitHub (see above)
- Use a specific version tag instead of `latest`

### Platform Mismatch

If you get "no matching manifest" errors:
```bash
# Specify platform explicitly
docker pull --platform linux/amd64 ghcr.io/ben-kuhn/packetqth:latest
```

### Outdated Image

If you're not getting the latest version:
```bash
# Force pull new image
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Remove old containers and images
docker-compose down
docker rmi ghcr.io/ben-kuhn/packetqth:latest

# Re-pull and start
docker pull ghcr.io/ben-kuhn/packetqth:latest
docker-compose up -d
```

### Build Failures

Check the GitHub Actions status:
1. Go to https://github.com/ben-kuhn/packetqth/actions
2. Look for the latest "Build and Publish Docker Image" workflow
3. Check logs for errors

## Release Process

For maintainers: How to publish a new version.

### Creating a Release

```bash
# Ensure main branch is ready
git checkout main
git pull

# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0

- Feature 1
- Feature 2
- Bug fix 3
"

# Push the tag
git push origin v1.0.0
```

GitHub Actions will automatically:
1. Build multi-platform images
2. Push to ghcr.io with multiple tags:
   - `1.0.0`
   - `1.0`
   - `1`
   - `latest`
3. Generate build attestation

### Pre-Release Testing

Test before tagging:
```bash
# Push to main branch
git push origin main

# Wait for build to complete
# Test with the main tag
docker pull ghcr.io/ben-kuhn/packetqth:main
docker run ghcr.io/ben-kuhn/packetqth:main --version

# If good, tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## Verification

### Verify Image Integrity

Check the image digest:
```bash
# Get the image digest
docker inspect ghcr.io/ben-kuhn/packetqth:latest \
  --format='{{index .RepoDigests 0}}'

# Compare with GitHub Actions output
```

### Verify Build Provenance

GitHub generates attestations for each build:
```bash
# View attestation (requires gh CLI)
gh attestation verify oci://ghcr.io/ben-kuhn/packetqth:latest \
  --owner ben-kuhn
```

## Further Reading

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Multi-Platform Images](https://docs.docker.com/build/building/multi-platform/)
- [GitHub Actions Workflow](.github/workflows/README.md)
- [Docker Guide](DOCKER.md)

---

**73!** 📦🐳
