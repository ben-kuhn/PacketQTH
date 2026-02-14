# GitHub Configuration

This directory contains GitHub-specific configuration files.

## Workflows

Automated workflows using GitHub Actions:

### docker-publish.yml

Automatically builds and publishes Docker images to GitHub Container Registry (ghcr.io).

**Triggers:**
- Push to `main` branch
- Version tags (e.g., `v1.0.0`)
- Pull requests (build only, no publish)

**Published to:** `ghcr.io/ben-kuhn/packetqth`

**Platforms:**
- linux/amd64
- linux/arm64
- linux/arm/v7

See [workflows/README.md](workflows/README.md) for details.

## Package Registry

PacketQTH images are published to GitHub Container Registry:
- View packages: https://github.com/ben-kuhn?tab=packages
- Pull images: `docker pull ghcr.io/ben-kuhn/packetqth:latest`

See [CONTAINER_REGISTRY.md](../CONTAINER_REGISTRY.md) for usage guide.
