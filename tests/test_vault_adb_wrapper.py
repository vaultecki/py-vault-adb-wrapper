from unittest.mock import MagicMock

import pytest

from vault_adb_wrapper import (
    ActionNotFoundException,
    ConfigNotFoundException,
    DeviceNotFoundException,
    InsufficientArgumentsException,
    VaultPhone,
    VaultPhoneException,
)

SERIAL = "TESTSERIAL"


class TestConstruction:
    def test_connects_by_serial(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        assert phone.status() is True
        assert phone.uuid == SERIAL

    def test_device_not_found(self, patch_adb_client, config_file):
        patch_adb_client.devices.return_value = []

        with pytest.raises(DeviceNotFoundException):
            VaultPhone(uuid=SERIAL, config=config_file)

    def test_config_file_missing(self, patch_adb_client, tmp_path):
        missing = tmp_path / "does-not-exist.json"

        with pytest.raises(ConfigNotFoundException):
            VaultPhone(uuid=SERIAL, config=missing)

    def test_config_invalid_json(self, patch_adb_client, tmp_path):
        bad_config = tmp_path / "phone.json"
        bad_config.write_text("{not valid json")

        with pytest.raises(ConfigNotFoundException):
            VaultPhone(uuid=SERIAL, config=bad_config)

    def test_config_missing_entry_for_device(self, patch_adb_client, tmp_path):
        other_config = tmp_path / "phone.json"
        other_config.write_text('{"OTHER_SERIAL": {"noop": [["sleep", "0"]]}}')

        with pytest.raises(ConfigNotFoundException):
            VaultPhone(uuid=SERIAL, config=other_config)

    def test_wifi_connect_success(self, patch_adb_client, fake_device, tmp_path):
        fake_device.serial = "192.168.1.100:5555"
        patch_adb_client.connect = MagicMock()
        wifi_config = tmp_path / "phone.json"
        wifi_config.write_text('{"192.168.1.100:5555": {"noop": [["sleep", "0"]]}}')

        phone = VaultPhone(uuid=["192.168.1.100", "5555"], config=wifi_config)

        patch_adb_client.connect.assert_called_once_with("192.168.1.100:5555", timeout=1.0)
        assert phone.uuid == "192.168.1.100:5555"

    def test_wifi_connect_failure_wraps_original_exception(self, patch_adb_client, config_file):
        patch_adb_client.connect = MagicMock(side_effect=RuntimeError("no route"))

        with pytest.raises(DeviceNotFoundException) as exc_info:
            VaultPhone(uuid=["192.168.1.100", "5555"], config=config_file)

        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_wifi_uuid_requires_two_elements(self, patch_adb_client, config_file):
        with pytest.raises(ValueError):
            VaultPhone(uuid=["192.168.1.100"], config=config_file)


class TestSubstituteArgs:
    def test_replaces_multiple_placeholders(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        result = phone._substitute_args("$ARG0 and $ARG1", ("foo", "bar"))

        assert result == "foo and bar"

    def test_escapes_quotes(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        result = phone._substitute_args('say "$ARG0"', ("it's",))

        assert result == 'say "it\\\'s"'


class TestAction:
    def test_shell_action_substitutes_and_runs(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("greet", "world")

        fake_device.shell.assert_called_once_with("echo hello world")
        assert results == ["shell-ok"]

    def test_tap_action_runs_input_tap(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("tap_center")

        fake_device.shell.assert_called_once_with("input tap 500 300")
        assert results == ["shell-ok"]

    def test_tap_action_substitutes_args(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("tap_at", "120", "480")

        fake_device.shell.assert_called_once_with("input tap 120 480")
        assert results == ["shell-ok"]

    def test_sleep_action_waits(self, patch_adb_client, config_file, monkeypatch):
        sleep_mock = MagicMock()
        monkeypatch.setattr("vault_adb_wrapper.time.sleep", sleep_mock)
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("wait_a_bit")

        sleep_mock.assert_called_once_with(0.01)
        assert results == [True]

    def test_sleep_action_substitutes_args(self, patch_adb_client, config_file, monkeypatch):
        sleep_mock = MagicMock()
        monkeypatch.setattr("vault_adb_wrapper.time.sleep", sleep_mock)
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("wait_dynamic", "0.5")

        sleep_mock.assert_called_once_with(0.5)
        assert results == [True]

    def test_nested_action_runs_referenced_action(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("chain", "world")

        fake_device.shell.assert_called_once_with("echo hello world")
        assert results == [["shell-ok"]]

    def test_push_with_enough_args(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("copy_in", "local.apk", "/sdcard/app.apk")

        fake_device.push.assert_called_once_with("local.apk", "/sdcard/app.apk")
        assert results == ["push-ok"]

    def test_push_with_missing_config_field_is_caught(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("copy_in_missing_dest", "local.apk")

        assert results == [None]

    def test_pull_with_enough_args(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("copy_out", "/sdcard/app.apk", "local.apk")

        fake_device.pull.assert_called_once_with("/sdcard/app.apk", "local.apk")
        assert results == ["pull-ok"]

    def test_forward_with_enough_args(self, patch_adb_client, fake_device, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("expose_port", "8080", "8080")

        fake_device.forward.assert_called_once_with("tcp:8080", "tcp:8080")
        assert results == ["forward-ok"]

    def test_unknown_action_type_yields_none(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("unknown_step")

        assert results == [None]

    def test_invalid_element_is_skipped(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        results = phone.action("broken_step")

        assert results == []

    def test_missing_action_raises(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        with pytest.raises(ActionNotFoundException):
            phone.action("does_not_exist")

    def test_direct_execute_push_raises_without_action_wrapper(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        with pytest.raises(InsufficientArgumentsException):
            phone._execute_push(["$ARG0"], ())


class TestIntrospection:
    def test_get_available_actions(self, patch_adb_client, config_file, config_data):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        assert sorted(phone.get_available_actions()) == sorted(config_data[SERIAL].keys())

    def test_repr_reports_status(self, patch_adb_client, config_file):
        phone = VaultPhone(uuid=SERIAL, config=config_file)

        assert repr(phone) == f"VaultPhone(uuid={SERIAL}, status=connected)"


def test_exception_hierarchy():
    assert issubclass(DeviceNotFoundException, VaultPhoneException)
    assert issubclass(ConfigNotFoundException, VaultPhoneException)
    assert issubclass(ActionNotFoundException, VaultPhoneException)
    assert issubclass(InsufficientArgumentsException, VaultPhoneException)
