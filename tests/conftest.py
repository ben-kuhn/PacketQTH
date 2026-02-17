"""
PacketQTH Test Configuration and Shared Fixtures
"""

import os
import sys
import tempfile
import yaml
import pyotp
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Shared entity fixtures
# ---------------------------------------------------------------------------

SAMPLE_ENTITIES = [
    {
        'entity_id': 'light.kitchen',
        'state': 'on',
        'attributes': {'friendly_name': 'Kitchen Light', 'brightness': 200}
    },
    {
        'entity_id': 'light.bedroom',
        'state': 'off',
        'attributes': {'friendly_name': 'Bedroom Light', 'brightness': 0}
    },
    {
        'entity_id': 'switch.garage',
        'state': 'on',
        'attributes': {'friendly_name': 'Garage Switch'}
    },
    {
        'entity_id': 'sensor.temperature',
        'state': '72',
        'attributes': {'friendly_name': 'Temperature', 'unit_of_measurement': '°F'}
    },
    {
        'entity_id': 'automation.good_night',
        'state': 'on',
        'attributes': {'friendly_name': 'Good Night'}
    },
    {
        'entity_id': 'cover.blinds',
        'state': 'open',
        'attributes': {'friendly_name': 'Living Room Blinds', 'current_position': 100}
    },
    {
        'entity_id': 'fan.bedroom_fan',
        'state': 'on',
        'attributes': {'friendly_name': 'Bedroom Fan', 'percentage': 50}
    },
    {
        'entity_id': 'climate.thermostat',
        'state': 'heat',
        'attributes': {'friendly_name': 'Thermostat', 'temperature': 72}
    },
]


@pytest.fixture
def sample_entities():
    return list(SAMPLE_ENTITIES)


@pytest.fixture
def users_yaml(tmp_path):
    """Create a temporary users.yaml file with a test user."""
    secret = pyotp.random_base32()
    data = {
        'users': {'KN4XYZ': secret},
        'security': {
            'max_failed_attempts': 5,
            'lockout_duration_seconds': 300,
            'session_timeout_seconds': 300
        }
    }
    filepath = tmp_path / 'users.yaml'
    filepath.write_text(yaml.dump(data))
    return str(filepath), secret
