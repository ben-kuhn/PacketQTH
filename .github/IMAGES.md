# PacketQTH Container Images

PacketQTH publishes two container images to GitHub Container Registry.

## Image Comparison

| Feature | Runtime Image | Tools Image |
|---------|---------------|-------------|
| **Image Name** | `ghcr.io/ben-kuhn/packetqth` | `ghcr.io/ben-kuhn/packetqth-tools` |
| **Purpose** | Running the server | TOTP setup, development |
| **Dependencies** | Core only (~200KB) | Core + tools (~3.2MB) |
| **Includes QR codes** | ❌ No | ✅ Yes (qrcode, Pillow) |
| **Size (amd64)** | ~150MB compressed | ~180MB compressed |
| **Use for** | Production deployment | Initial setup, testing |
| **Dockerfile** | `Dockerfile` | `Dockerfile.tools` |

## When to Use Each Image

### Runtime Image: `ghcr.io/ben-kuhn/packetqth`

**Use for:**
- Running the PacketQTH server in production
- Docker Compose deployments
- Minimal container size
- Production environments

**Example:**
```bash
# Pull runtime image
docker pull ghcr.io/ben-kuhn/packetqth:latest

# Run server
docker-compose up -d
```

### Tools Image: `ghcr.io/ben-kuhn/packetqth-tools`

**Use for:**
- Interactive setup wizard (generates all config files)
- Generating TOTP secrets with QR codes
- Running security audits
- Development and testing
- Any operation requiring tools dependencies

**Example:**
```bash
# Full setup wizard (Podman):
podman run --rm -it --userns=keep-id -v $(pwd):/config \
  ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml

# Generate TOTP with QR code (Docker/Podman, no volume mount needed):
docker run --rm -it ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/setup_totp.py YOUR_CALLSIGN

# Run security audit
docker run --rm ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/security_audit.py

# Run server audit
docker run --rm ghcr.io/ben-kuhn/packetqth-tools:latest \
  python tools/audit_server.py
```

## Typical Workflow

1. **Setup phase** - Use tools image interactive wizard:
   ```bash
   # Podman (rootless):
   podman run --rm -it --userns=keep-id -v $(pwd):/config \
     ghcr.io/ben-kuhn/packetqth-tools:latest \
     python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml
   # Docker:
   docker run --rm -it --user $(id -u):$(id -g) -v $(pwd):/config \
     ghcr.io/ben-kuhn/packetqth-tools:latest \
     python tools/configure.py --config /config/config.yaml --env /config/.env --users /config/users.yaml
   ```
   Wizard generates `config.yaml`, `.env`, `users.yaml`, and `docker-compose.generated.yml`.

2. **Production** - Use runtime image:
   ```bash
   docker-compose up -d
   ```

## Available Tags

Both images use the same tagging strategy:

| Tag Pattern | Example | Description |
|-------------|---------|-------------|
| `latest` | `packetqth:latest` | Latest stable release |
| `main` | `packetqth:main` | Latest from main branch |
| `1.0.0` | `packetqth:1.0.0` | Specific version |
| `1.0` | `packetqth:1.0` | Latest patch (1.0.x) |
| `1` | `packetqth:1` | Latest minor (1.x.x) |
| `main-abc123` | `packetqth:main-abc123` | Specific commit |

Add `-tools` suffix for tools image:
- `ghcr.io/ben-kuhn/packetqth-tools:latest`
- `ghcr.io/ben-kuhn/packetqth-tools:1.0.0`
- etc.

## Platform Support

Both images support multiple platforms:
- `linux/amd64` - x86_64 servers, desktops
- `linux/arm64` - Raspberry Pi 4, Apple M1/M2
- `linux/arm/v7` - Raspberry Pi 3

Docker automatically selects the right platform.

## Build Process

Both images are built automatically by GitHub Actions:

**Triggers:**
- Push to `main` branch → builds both images
- Version tags (e.g., `v1.0.0`) → builds both images
- Pull requests → builds both (test only, not published)

**Workflow:** `.github/workflows/docker-publish.yml`

See [workflows/README.md](workflows/README.md) for details.

## Local Development

### Building Locally

**Runtime image:**
```bash
docker build -t packetqth:local .
```

**Tools image:**
```bash
docker build -f Dockerfile.tools -t packetqth-tools:local .
```

### Using Local Builds

**With docker-compose:**
```yaml
services:
  packetqth:
    # Comment out pre-built image
    # image: ghcr.io/ben-kuhn/packetqth:latest

    # Use local build
    build: .
    image: packetqth:local
```

Or use `docker-compose.dev.yml`:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## FAQ

**Q: Which image should I use for production?**
A: Runtime image (`packetqth`) - it's smaller and has only required dependencies.

**Q: Can I run the server with the tools image?**
A: Yes, but it's larger (~30MB extra). Use runtime image for production.

**Q: How do I generate QR codes without the tools image?**
A: Use `tools/generate_secret.py` (no dependencies) and manually enter the secret in your authenticator app.

**Q: Are both images updated together?**
A: Yes, both are built from the same commit at the same time.

**Q: Can I use different versions for runtime and tools?**
A: Yes, but it's recommended to use matching versions to avoid compatibility issues.

**Q: Which image does docker-compose.yml use?**
A: Runtime image by default. Tools image is only needed for setup.

---

**73!** 🐳📦
