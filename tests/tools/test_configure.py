# tests/tools/test_configure.py
import os
import pytest
import tempfile
import yaml
from pathlib import Path


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
