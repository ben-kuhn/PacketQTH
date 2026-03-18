# tests/tools/test_configure.py
import os
import pytest
import yaml
from pathlib import Path
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock


def test_load_env_returns_empty_dict_when_file_missing(tmp_path):
    from tools.configure import load_env
    result = load_env(tmp_path / ".env")
    assert result == {}


def test_load_env_parses_key_value_pairs(tmp_path):
    from tools.configure import load_env
    env_file = tmp_path / ".env"
    env_file.write_text("HA_TOKEN=abc123\nLOG_LEVEL=INFO\n")
    result = load_env(env_file)
    assert result == {"HA_TOKEN": "abc123", "LOG_LEVEL": "INFO"}


def test_save_env_writes_key_value_pairs(tmp_path):
    from tools.configure import save_env
    env_file = tmp_path / ".env"
    save_env({"HA_TOKEN": "mytoken"}, env_file)
    content = env_file.read_text()
    assert "HA_TOKEN=mytoken" in content


def test_load_config_returns_defaults_when_file_missing(tmp_path):
    from tools.configure import load_config, DEFAULT_CONFIG
    result = load_config(tmp_path / "config.yaml")
    assert result["telnet"]["port"] == DEFAULT_CONFIG["telnet"]["port"]


def test_load_config_reads_existing_file(tmp_path):
    from tools.configure import load_config
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("telnet:\n  port: 9999\n")
    result = load_config(cfg_file)
    assert result["telnet"]["port"] == 9999


def test_save_config_writes_yaml(tmp_path):
    from tools.configure import save_config
    cfg_file = tmp_path / "config.yaml"
    save_config({"telnet": {"port": 8023}}, cfg_file)
    loaded = yaml.safe_load(cfg_file.read_text())
    assert loaded["telnet"]["port"] == 8023


def test_load_users_returns_empty_when_missing(tmp_path):
    from tools.configure import load_users
    result = load_users(tmp_path / "users.yaml")
    assert result == {}


def test_save_users_writes_yaml_with_users_key(tmp_path):
    from tools.configure import save_users
    users_file = tmp_path / "users.yaml"
    save_users({"W1AW": "SECRETBASE32"}, users_file)
    loaded = yaml.safe_load(users_file.read_text())
    assert loaded["users"]["W1AW"] == "SECRETBASE32"


@pytest.mark.asyncio
async def test_test_ha_connection_returns_count_on_success():
    from tools.configure import test_ha_connection
    mock_states = [{"entity_id": "light.kitchen"}, {"entity_id": "switch.fan"}]
    with patch("tools.configure.aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_states)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "mytoken")
    assert count == 2
    assert err is None


@pytest.mark.asyncio
async def test_test_ha_connection_returns_error_on_auth_failure():
    from tools.configure import test_ha_connection
    with patch("tools.configure.aiohttp.ClientSession") as MockSession:
        mock_resp = AsyncMock()
        mock_resp.status = 401
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_resp
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "badtoken")
    assert count is None
    assert "401" in err or "Unauthorized" in err.lower()


@pytest.mark.asyncio
async def test_test_ha_connection_returns_error_on_network_failure():
    from tools.configure import test_ha_connection
    with patch("tools.configure.aiohttp.ClientSession") as MockSession:
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientConnectorError(
            MagicMock(), OSError("connection refused")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        MockSession.return_value = mock_session
        count, err = await test_ha_connection("http://ha.local:8123", "token")
    assert count is None
    assert err is not None


def test_parse_server_inputs_uses_defaults_for_empty():
    from tools.configure import parse_server_inputs
    result = parse_server_inputs(port="", timeout="", max_attempts="")
    assert result["port"] == 8023
    assert result["timeout_seconds"] == 300
    assert result["max_auth_attempts"] == 3


def test_parse_server_inputs_uses_provided_values():
    from tools.configure import parse_server_inputs
    result = parse_server_inputs(port="9000", timeout="600", max_attempts="5")
    assert result["port"] == 9000
    assert result["timeout_seconds"] == 600
    assert result["max_auth_attempts"] == 5


def test_parse_server_inputs_rejects_invalid_port():
    from tools.configure import parse_server_inputs
    with pytest.raises(ValueError, match="port"):
        parse_server_inputs(port="notanumber", timeout="300", max_attempts="3")


def test_parse_server_inputs_rejects_out_of_range_port():
    from tools.configure import parse_server_inputs
    with pytest.raises(ValueError, match="port"):
        parse_server_inputs(port="0", timeout="300", max_attempts="3")
    with pytest.raises(ValueError, match="port"):
        parse_server_inputs(port="65536", timeout="300", max_attempts="3")


def test_build_entity_filter_includes_only_selected():
    from tools.configure import build_entity_filter
    all_entities = [
        {"entity_id": "light.kitchen"},
        {"entity_id": "light.living_room"},
        {"entity_id": "switch.fan"},
    ]
    selected_domains = ["light"]
    selected_entities = {"light": ["light.kitchen"]}  # only kitchen selected
    inc_domains, inc_entities = build_entity_filter(all_entities, selected_domains, selected_entities)
    assert inc_domains == ["light"]
    assert "light.kitchen" in inc_entities
    assert "light.living_room" not in inc_entities
    assert "switch.fan" not in inc_entities


def test_build_entity_filter_includes_all_selected():
    from tools.configure import build_entity_filter
    all_entities = [{"entity_id": "light.kitchen"}, {"entity_id": "light.hall"}]
    selected_domains = ["light"]
    selected_entities = {"light": ["light.kitchen", "light.hall"]}
    inc_domains, inc_entities = build_entity_filter(all_entities, selected_domains, selected_entities)
    assert inc_domains == ["light"]
    assert sorted(inc_entities) == ["light.hall", "light.kitchen"]


def test_migrate_exclusion_to_inclusion_removes_excluded():
    from tools.configure import migrate_exclusion_to_inclusion
    grouped = {
        "light": ["light.kitchen", "light.living_room", "light.bedroom"],
        "switch": ["switch.fan"],
    }
    include_domains = ["light"]
    exclude_entities = ["light.living_room"]
    result = migrate_exclusion_to_inclusion(grouped, include_domains, exclude_entities)
    assert "light.kitchen" in result
    assert "light.bedroom" in result
    assert "light.living_room" not in result
    assert "switch.fan" not in result  # not in include_domains


def test_migrate_exclusion_to_inclusion_supports_glob():
    from tools.configure import migrate_exclusion_to_inclusion
    grouped = {
        "sensor": ["sensor.temp", "sensor.last_boot", "sensor.uptime_seconds"],
    }
    include_domains = ["sensor"]
    exclude_entities = ["sensor.*_boot", "sensor.uptime*"]
    result = migrate_exclusion_to_inclusion(grouped, include_domains, exclude_entities)
    assert "sensor.temp" in result
    assert "sensor.last_boot" not in result
    assert "sensor.uptime_seconds" not in result


def test_migrate_exclusion_to_inclusion_empty_exclusions():
    from tools.configure import migrate_exclusion_to_inclusion
    grouped = {
        "light": ["light.kitchen", "light.bedroom"],
    }
    include_domains = ["light"]
    exclude_entities = []
    result = migrate_exclusion_to_inclusion(grouped, include_domains, exclude_entities)
    assert result == {"light.kitchen", "light.bedroom"}


def test_group_entities_by_domain_groups_and_sorts():
    from tools.configure import group_entities_by_domain
    entities = [
        {"entity_id": "switch.fan"},
        {"entity_id": "light.kitchen"},
        {"entity_id": "light.hall"},
    ]
    grouped = group_entities_by_domain(entities)
    assert "light" in grouped
    assert "switch" in grouped
    assert grouped["light"] == sorted(grouped["light"])


def test_parse_totp_secret_from_output_extracts_secret():
    from tools.configure import parse_totp_secret_from_output
    output = (
        "============================================================\n"
        "Add this to your users.yaml file:\n"
        "============================================================\n"
        '  W1AW: "JBSWY3DPEHPK3PXP"\n'
        "============================================================\n"
    )
    secret = parse_totp_secret_from_output("W1AW", output)
    assert secret == "JBSWY3DPEHPK3PXP"


def test_parse_totp_secret_returns_none_when_not_found():
    from tools.configure import parse_totp_secret_from_output
    secret = parse_totp_secret_from_output("W1AW", "no secret here")
    assert secret is None


def test_generate_compose_uses_provided_port_and_path():
    from tools.configure import generate_compose
    result = generate_compose(host_port=9000, config_dir="/home/user/pqth", logs_dir="/home/user/pqth/logs", uid=1000, gid=1000)
    loaded = yaml.safe_load(result)
    svc = loaded["services"]["packetqth"]
    assert "9000:8023" in svc["ports"][0]
    assert "/home/user/pqth/config.yaml" in svc["volumes"][0]
    assert "/home/user/pqth/logs:/app/logs" in svc["volumes"][2]
    assert svc["user"] == "1000:1000"


def test_generate_compose_custom_logs_dir():
    from tools.configure import generate_compose
    result = generate_compose(host_port=8023, config_dir="/opt/pqth", logs_dir="/var/log/packetqth", uid=1001, gid=1002)
    loaded = yaml.safe_load(result)
    svc = loaded["services"]["packetqth"]
    assert "8023:8023" in svc["ports"][0]
    assert "/var/log/packetqth:/app/logs" in svc["volumes"][2]
    assert svc["user"] == "1001:1002"


def test_load_config_preserves_null_values_from_file(tmp_path):
    from tools.configure import load_config
    cfg_file = tmp_path / "config.yaml"
    # Write a config with explicit null for exclude_domains
    cfg_file.write_text("homeassistant:\n  entity_filter:\n    exclude_domains: null\n")
    result = load_config(cfg_file)
    # null from file should override DEFAULT_CONFIG's value
    assert result["homeassistant"]["entity_filter"]["exclude_domains"] is None
