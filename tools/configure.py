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
import aiohttp
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
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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

    while True:
        url = prompt(
            HTML(f"HomeAssistant URL [<ansigreen>{current_url}</ansigreen>]: "),
        ).strip() or current_url

        token_hint = f"***{current_token[-6:]}" if len(current_token) > 6 else ("(set)" if current_token else "(not set)")
        token = prompt(
            HTML(f"HA Long-Lived Access Token [<ansigreen>{token_hint}</ansigreen>]: "),
            is_password=True,
        ).strip() or current_token

        print("\nTesting connection...", end=" ", flush=True)
        count, err = asyncio.run(test_ha_connection(url, token))
        if not err:
            print(f"Connected ({count} entities found)")
            break
        print(f"FAILED\n  {err}")
        if prompt("Retry? [y/N]: ").strip().lower() != "y":
            print("Skipping connection test — continuing with provided values.")
            break
        current_url = url
        current_token = token

    env["HA_TOKEN"] = token
    save_env(env, env_path)
    config.setdefault("homeassistant", {})
    config["homeassistant"]["url"] = url
    config["homeassistant"]["token"] = "${HA_TOKEN}"
    save_config(config, config_path)
    print(f"  Wrote {env_path}")
    print(f"  Wrote {config_path}")
    return url, token


# ---------------------------------------------------------------------------
# Step 2: Server Config
# ---------------------------------------------------------------------------

def parse_server_inputs(port: str, timeout: str, max_attempts: str) -> dict:
    """Parse and validate server config inputs. Uses defaults for empty strings."""
    def _int(val: str, default: int, name: str) -> int:
        if not val.strip():
            return default
        try:
            return int(val.strip())
        except ValueError:
            raise ValueError(f"Invalid {name}: {val!r} — must be an integer")

    return {
        "port": _int(port, 8023, "port"),
        "timeout_seconds": _int(timeout, 300, "timeout"),
        "max_auth_attempts": _int(max_attempts, 3, "max_attempts"),
    }


def step_server_config(config: dict, config_path: Path) -> None:
    """Prompt for server settings and write to config.yaml."""
    from prompt_toolkit import prompt
    from prompt_toolkit.formatted_text import HTML

    print("\n" + "=" * 60)
    print("Step 2/5: Server Settings")
    print("=" * 60)

    telnet = config.get("telnet", {})
    security = config.get("security", {})

    cur_port = telnet.get("port", 8023)
    cur_timeout = telnet.get("timeout_seconds", 300)
    cur_attempts = security.get("max_auth_attempts", 3)

    while True:
        try:
            inputs = parse_server_inputs(
                port=prompt(HTML(f"Telnet port [<ansigreen>{cur_port}</ansigreen>]: ")).strip(),
                timeout=prompt(HTML(f"Session timeout in seconds [<ansigreen>{cur_timeout}</ansigreen>]: ")).strip(),
                max_attempts=prompt(HTML(f"Max failed auth attempts [<ansigreen>{cur_attempts}</ansigreen>]: ")).strip(),
            )
            break
        except ValueError as e:
            print(f"  Error: {e} — please try again")

    config.setdefault("telnet", {}).update({
        "port": inputs["port"],
        "timeout_seconds": inputs["timeout_seconds"],
    })
    config.setdefault("security", {})["max_auth_attempts"] = inputs["max_auth_attempts"]
    save_config(config, config_path)
    print(f"  Wrote {config_path}")


# ---------------------------------------------------------------------------
# Step 3: Entity Filter
# ---------------------------------------------------------------------------

async def fetch_all_entities(url: str, token: str) -> list[dict]:
    """Fetch all entity states from HA API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        resp = await session.get(f"{url.rstrip('/')}/api/states", headers=headers)
        resp.raise_for_status()
        return await resp.json()


def group_entities_by_domain(entities: list[dict]) -> dict[str, list[str]]:
    """Group entity_ids by domain, sorted within each domain."""
    grouped: dict[str, list[str]] = {}
    for entity in entities:
        eid = entity.get("entity_id", "")
        if "." not in eid:
            continue
        domain = eid.split(".")[0]
        grouped.setdefault(domain, []).append(eid)
    for domain in grouped:
        grouped[domain].sort()
    return grouped


def build_entity_filter(
    all_entities: list[dict],
    selected_domains: list[str],
    selected_entities: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """
    Build include_domains and exclude_entities lists from selections.
    Entities within selected domains that were NOT chosen become exclude_entities.
    """
    grouped = group_entities_by_domain(all_entities)
    exclude_entities = []
    for domain in selected_domains:
        domain_entities = grouped.get(domain, [])
        chosen = set(selected_entities.get(domain, []))
        for eid in domain_entities:
            if eid not in chosen:
                exclude_entities.append(eid)
    return sorted(selected_domains), sorted(exclude_entities)


def step_entity_filter(config: dict, config_path: Path, ha_url: str, ha_token: str) -> None:
    """
    Interactively build entity filter. Skippable if HA unreachable.
    Writes entity_filter section to config.yaml.
    """
    from prompt_toolkit import prompt
    from prompt_toolkit.shortcuts import checkboxlist_dialog
    from prompt_toolkit.styles import Style

    print("\n" + "=" * 60)
    print("Step 3/5: Entity Filter")
    print("  (Enter 'n' to skip if HomeAssistant is unavailable)")
    print("=" * 60)

    skip = prompt("Fetch entities from HomeAssistant now? [Y/n]: ").strip().lower()
    if skip == "n":
        print("  Skipped — keeping existing entity_filter config.")
        return

    # Fetch entities
    print("Fetching entities...", end=" ", flush=True)
    try:
        entities = asyncio.run(fetch_all_entities(ha_url, ha_token))
        print(f"{len(entities)} entities found")
    except Exception as e:
        print(f"FAILED: {e}")
        print("  Skipping entity filter step.")
        return

    grouped = group_entities_by_domain(entities)
    all_domains = sorted(grouped.keys())

    # Current selections from config
    ef = config.get("homeassistant", {}).get("entity_filter", {})
    current_inc_domains = set(ef.get("include_domains") or [])
    current_exc_entities = set(ef.get("exclude_entities") or [])

    # Domain selection dialog
    style = Style.from_dict({"dialog": "bg:#1e1e2e", "dialog.body": "bg:#1e1e2e fg:#cdd6f4"})
    domain_choices = [(d, f"{d}  ({len(grouped[d])} entities)") for d in all_domains]
    default_domains = [d for d in all_domains if d in current_inc_domains] or \
                      [d for d in all_domains if d in {"light", "switch", "automation", "cover", "sensor", "climate", "fan", "lock"}]

    selected_domains = checkboxlist_dialog(
        title="Select domains to include",
        text="Space to toggle, Enter to confirm:",
        values=domain_choices,
        default_values=default_domains,
        style=style,
    ).run()

    if selected_domains is None:
        print("  Cancelled — keeping existing entity_filter config.")
        return

    # Per-domain entity selection
    selected_entities: dict[str, list[str]] = {}
    for domain in selected_domains:
        domain_eids = grouped[domain]
        entity_choices = [(eid, eid) for eid in domain_eids]
        default_eids = [eid for eid in domain_eids if eid not in current_exc_entities]

        chosen = checkboxlist_dialog(
            title=f"Select entities to include — {domain} ({len(domain_eids)} total)",
            text="Space to toggle, Enter to confirm:",
            values=entity_choices,
            default_values=default_eids,
            style=style,
        ).run()

        if chosen is None:
            print(f"  Cancelled on domain '{domain}' — keeping existing config.")
            return
        selected_entities[domain] = chosen

    inc_domains, exc_entities = build_entity_filter(entities, selected_domains, selected_entities)

    config.setdefault("homeassistant", {}).setdefault("entity_filter", {}).update({
        "include_domains": inc_domains,
        "exclude_domains": None,
        "include_entities": None,
        "exclude_entities": exc_entities,
    })
    save_config(config, config_path)
    print(f"  {len(inc_domains)} domains, {len(exc_entities)} excluded entities")
    print(f"  Wrote {config_path}")


if __name__ == "__main__":
    print("PacketQTH Setup Wizard — run with: python tools/configure.py")
