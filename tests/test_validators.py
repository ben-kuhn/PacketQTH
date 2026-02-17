"""
Tests for commands/validators.py

Covers: ValidationError, CommandValidator (all _validate_* methods),
        validate_command convenience function, value range edge cases.
"""

import pytest
from commands.models import Command, CommandType
from commands.validators import CommandValidator, ValidationError, validate_command
from homeassistant.filters import EntityMapper


def make_entity(entity_id, state='on', **attrs):
    return {'entity_id': entity_id, 'state': state, 'attributes': attrs}


def make_mapper(*entities):
    """Create an EntityMapper loaded with the given entities."""
    em = EntityMapper()
    em.add_entities(list(entities))
    return em


def make_command(cmd_type, device_id=None, value=None, page=None):
    return Command(
        type=cmd_type,
        raw_input='',
        device_id=device_id,
        value=value,
        page=page
    )


# ---------------------------------------------------------------------------
# ValidationError tests
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_str_without_suggestion(self):
        e = ValidationError("Something went wrong")
        assert str(e) == "Something went wrong"

    def test_str_with_suggestion(self):
        e = ValidationError("Bad command", "Try L to list devices")
        assert "Bad command" in str(e)
        assert "Try L to list devices" in str(e)

    def test_message_attribute(self):
        e = ValidationError("Msg", "Hint")
        assert e.message == "Msg"
        assert e.suggestion == "Hint"


# ---------------------------------------------------------------------------
# CommandValidator - commands that skip validation
# ---------------------------------------------------------------------------

class TestCommandValidatorSkippedTypes:
    """LIST, AUTOMATIONS, HELP, QUIT, REFRESH, UNKNOWN are always valid."""

    @pytest.mark.parametrize("cmd_type", [
        CommandType.LIST,
        CommandType.AUTOMATIONS,
        CommandType.HELP,
        CommandType.QUIT,
        CommandType.REFRESH,
        CommandType.UNKNOWN,
    ])
    def test_skipped_commands_never_raise(self, cmd_type):
        v = CommandValidator()
        cmd = make_command(cmd_type)
        v.validate(cmd)  # should not raise


# ---------------------------------------------------------------------------
# CommandValidator - no entity mapper
# ---------------------------------------------------------------------------

class TestCommandValidatorNoMapper:
    def test_no_mapper_does_not_raise(self):
        v = CommandValidator(entity_mapper=None)
        cmd = make_command(CommandType.ON, device_id=1)
        v.validate(cmd)  # should not raise - can't validate without mapper


# ---------------------------------------------------------------------------
# CommandValidator - device not found
# ---------------------------------------------------------------------------

class TestCommandValidatorDeviceNotFound:
    def test_device_not_found_raises(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.ON, device_id=999)
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert '999' in exc_info.value.message

    def test_suggestion_mentions_list(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.ON, device_id=999)
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert 'L' in (exc_info.value.suggestion or '')


# ---------------------------------------------------------------------------
# CommandValidator - SHOW
# ---------------------------------------------------------------------------

class TestValidateShow:
    def test_show_any_entity_is_valid(self):
        entities = [
            make_entity('light.kitchen'),
            make_entity('sensor.temp'),
            make_entity('switch.garage'),
        ]
        em = make_mapper(*entities)
        v = CommandValidator(em)
        for i in range(1, len(entities) + 1):
            cmd = make_command(CommandType.SHOW, device_id=i)
            v.validate(cmd)  # should not raise


# ---------------------------------------------------------------------------
# CommandValidator - ON / OFF
# ---------------------------------------------------------------------------

class TestValidateOnOff:
    @pytest.mark.parametrize("entity_id", [
        'light.kitchen',
        'switch.garage',
        'fan.bedroom',
        'automation.night',
        'scene.movie',
        'script.hello',
    ])
    def test_on_valid_domains(self, entity_id):
        em = make_mapper(make_entity(entity_id))
        v = CommandValidator(em)
        cmd = make_command(CommandType.ON, device_id=1)
        v.validate(cmd)  # should not raise

    @pytest.mark.parametrize("entity_id", [
        'sensor.temperature',
        'cover.blinds',
        'climate.thermostat',
        'input_number.setpoint',
    ])
    def test_on_invalid_domains(self, entity_id):
        em = make_mapper(make_entity(entity_id))
        v = CommandValidator(em)
        cmd = make_command(CommandType.ON, device_id=1)
        with pytest.raises(ValidationError):
            v.validate(cmd)

    @pytest.mark.parametrize("entity_id", [
        'light.kitchen',
        'switch.garage',
    ])
    def test_off_valid_domains(self, entity_id):
        em = make_mapper(make_entity(entity_id))
        v = CommandValidator(em)
        cmd = make_command(CommandType.OFF, device_id=1)
        v.validate(cmd)  # should not raise

    def test_off_invalid_domain(self):
        em = make_mapper(make_entity('sensor.temp'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.OFF, device_id=1)
        with pytest.raises(ValidationError):
            v.validate(cmd)


# ---------------------------------------------------------------------------
# CommandValidator - SET
# ---------------------------------------------------------------------------

class TestValidateSet:
    @pytest.mark.parametrize("entity_id", [
        'light.kitchen',
        'cover.blinds',
        'climate.thermostat',
        'fan.bedroom',
        'input_number.setpoint',
        'number.setpoint',
    ])
    def test_set_valid_domains(self, entity_id):
        em = make_mapper(make_entity(entity_id))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='50')
        v.validate(cmd)  # should not raise

    def test_set_invalid_domain(self):
        em = make_mapper(make_entity('switch.garage'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='50')
        with pytest.raises(ValidationError):
            v.validate(cmd)


# ---------------------------------------------------------------------------
# CommandValidator - value range validation
# ---------------------------------------------------------------------------

class TestValidateValueRange:
    # Light brightness (0-255)
    def test_light_brightness_valid(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        for val in [0, 1, 128, 254, 255]:
            cmd = make_command(CommandType.SET, device_id=1, value=str(val))
            v.validate(cmd)

    def test_light_brightness_too_high(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='256')
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert '0-255' in exc_info.value.message

    def test_light_brightness_negative(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='-1')
        with pytest.raises(ValidationError):
            v.validate(cmd)

    # Cover position (0-100)
    def test_cover_position_valid(self):
        em = make_mapper(make_entity('cover.blinds'))
        v = CommandValidator(em)
        for val in [0, 50, 100]:
            cmd = make_command(CommandType.SET, device_id=1, value=str(val))
            v.validate(cmd)

    def test_cover_position_out_of_range(self):
        em = make_mapper(make_entity('cover.blinds'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='101')
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert '0-100' in exc_info.value.message

    # Climate temperature (-50 to 120)
    def test_climate_temperature_valid(self):
        em = make_mapper(make_entity('climate.thermostat'))
        v = CommandValidator(em)
        for val in [-50, 0, 72, 120]:
            cmd = make_command(CommandType.SET, device_id=1, value=str(val))
            v.validate(cmd)

    def test_climate_temperature_too_hot(self):
        em = make_mapper(make_entity('climate.thermostat'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='121')
        with pytest.raises(ValidationError):
            v.validate(cmd)

    def test_climate_temperature_too_cold(self):
        em = make_mapper(make_entity('climate.thermostat'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='-51')
        with pytest.raises(ValidationError):
            v.validate(cmd)

    # Fan percentage (0-100)
    def test_fan_percentage_valid(self):
        em = make_mapper(make_entity('fan.bedroom'))
        v = CommandValidator(em)
        for val in [0, 50, 100]:
            cmd = make_command(CommandType.SET, device_id=1, value=str(val))
            v.validate(cmd)

    def test_fan_percentage_out_of_range(self):
        em = make_mapper(make_entity('fan.bedroom'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='101')
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert '0-100' in exc_info.value.message

    # Non-numeric values
    def test_non_numeric_value_accepted(self):
        em = make_mapper(make_entity('input_number.x'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value='hello')
        v.validate(cmd)  # non-numeric skips range check

    # None value (no range check)
    def test_none_value_skips_range_check(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.SET, device_id=1, value=None)
        v.validate(cmd)  # should not raise


# ---------------------------------------------------------------------------
# CommandValidator - TRIGGER
# ---------------------------------------------------------------------------

class TestValidateTrigger:
    def test_trigger_automation_valid(self):
        em = make_mapper(make_entity('automation.good_night'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.TRIGGER, device_id=1)
        v.validate(cmd)  # should not raise

    def test_trigger_non_automation_raises(self):
        em = make_mapper(make_entity('light.kitchen'))
        v = CommandValidator(em)
        cmd = make_command(CommandType.TRIGGER, device_id=1)
        with pytest.raises(ValidationError) as exc_info:
            v.validate(cmd)
        assert 'automation' in exc_info.value.message.lower() or 'A' in (exc_info.value.suggestion or '')


# ---------------------------------------------------------------------------
# validate_command convenience function
# ---------------------------------------------------------------------------

class TestValidateCommandFunction:
    def test_valid_command_no_raise(self):
        em = make_mapper(make_entity('light.kitchen'))
        cmd = make_command(CommandType.ON, device_id=1)
        validate_command(cmd, em)  # should not raise

    def test_invalid_command_raises(self):
        em = make_mapper(make_entity('sensor.temp'))
        cmd = make_command(CommandType.ON, device_id=1)
        with pytest.raises(ValidationError):
            validate_command(cmd, em)

    def test_no_mapper_no_raise(self):
        cmd = make_command(CommandType.ON, device_id=1)
        validate_command(cmd, None)  # no mapper = no validation
