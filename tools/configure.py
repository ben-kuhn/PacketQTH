#!/usr/bin/env python3
"""
PacketQTH Setup Wizard

Interactive TUI wizard for initial configuration. Produces:
  .env              - HA token and secrets
  config.yaml       - Full application config
  users.yaml        - Initial user TOTP setup
  docker-compose.generated.yml - Ready-to-use compose file
"""

import copy
import os
import sys
import asyncio
import subprocess
import yaml
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: dict[str, Any] = {
    "telnet": {
        "host": "0.0.0.0",
        "port": 8023,
        "max_connections": 10,
        "timeout_seconds": 300,
        "bpq_mode": True,
    },
    "homeassistant": {
        "url": "http://homeassistant.local:8123",
        "token": "${HA_TOKEN}",
        "cache_ttl": 60,
        "entity_filter": {
            "include_domains": ["light", "switch", "automation", "cover", "sensor", "climate", "fan", "lock"],
            "exclude_domains": None,
            "include_entities": None,
            "exclude_entities": [],
        },
    },
    "auth": {"users_file": "users.yaml"},
    "display": {"page_size": 10},
    "security": {
        "welcome_banner": "PacketQTH v0.1.0",
        "max_auth_attempts": 3,
        "ip_safelist": [],
    },
}

# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict[str, str]:
    """Load .env file into dict. Returns empty dict if file missing."""
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


def save_env(values: dict[str, str], path: Path) -> None:
    """Write dict to .env file."""
    lines = [f"{k}={v}\n" for k, v in values.items()]
    path.write_text("".join(lines))


def load_config(path: Path) -> dict[str, Any]:
    """Load config.yaml. Returns DEFAULT_CONFIG structure if file missing."""
    defaults = copy.deepcopy(DEFAULT_CONFIG)
    if not path.exists():
        return defaults
    loaded = yaml.safe_load(path.read_text()) or {}
    # Deep merge loaded values over defaults
    _deep_merge(defaults, loaded)
    return defaults


def save_config(config: dict[str, Any], path: Path) -> None:
    """Write config dict to YAML file."""
    path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))


def load_users(path: Path) -> dict[str, str]:
    """Load users.yaml. Returns empty dict if missing."""
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text()) or {}
    return loaded.get("users", {})


def save_users(users: dict[str, str], path: Path) -> None:
    """Write users dict to users.yaml under 'users' key."""
    path.write_text(yaml.dump({"users": users}, default_flow_style=False))


def _deep_merge(base: dict, override: dict) -> None:
    """Merge override into base in-place (recursive for nested dicts)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Step 1: HomeAssistant Connection
# ---------------------------------------------------------------------------

async def test_ha_connection(url: str, token: str) -> tuple[int | None, str | None]:
    """
    Test HA connection by fetching /api/states.
    Returns (entity_count, None) on success or (None, error_message) on failure.
    """
    import aiohttp
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"{url.rstrip('/')}/api/states", headers=headers)
            if resp.status == 401:
                return None, "Unauthorized (401) — check your token"
            if resp.status != 200:
                return None, f"Unexpected status {resp.status}"
            states = await resp.json()
            return len(states), None
    except aiohttp.ClientConnectorError as e:
        return None, f"Connection failed: {e}"
    except Exception as e:
        return None, f"Error: {e}"


def step_ha_connection(config: dict, env: dict, config_path: Path, env_path: Path) -> tuple[str, str]:
    """
    Prompt for HA URL and token. Test connection. Write .env and config.yaml.
    Returns (url, token) for use in later steps.
    """
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML

    print("\n" + "=" * 60)
    print("Step 1/5: HomeAssistant Connection")
    print("=" * 60)

    current_url = config.get("homeassistant", {}).get("url", DEFAULT_CONFIG["homeassistant"]["url"])
    current_token = env.get("HA_TOKEN", "")

    url = prompt(
        HTML(f"HomeAssistant URL [<ansigreen>{current_url}</ansigreen>]: "),
    ).strip() or current_url

    token_hint = f"***{current_token[-6:]}" if len(current_token) > 6 else ("(set)" if current_token else "(not set)")
    token = prompt(
        HTML(f"HA Long-Lived Access Token [<ansigreen>{token_hint}</ansigreen>]: "),
        is_password=True,
    ).strip() or current_token

    # Test connection
    print("\nTesting connection...", end=" ", flush=True)
    count, err = asyncio.run(test_ha_connection(url, token))
    if err:
        print(f"FAILED\n  {err}")
        retry = prompt("Retry? [y/N]: ").strip().lower()
        if retry == "y":
            return step_ha_connection(config, env, config_path, env_path)
        print("Skipping connection test — continuing with provided values.")
    else:
        print(f"Connected ({count} entities found)")

    # Write outputs
    env["HA_TOKEN"] = token
    save_env(env, env_path)
    config.setdefault("homeassistant", {})["url"] = url
    config["homeassistant"]["token"] = "${HA_TOKEN}"
    save_config(config, config_path)
    print(f"  Wrote {env_path}")
    print(f"  Wrote {config_path}")

    return url, token


if __name__ == "__main__":
    print("PacketQTH Setup Wizard — run with: python tools/configure.py")
