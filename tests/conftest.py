import json
from unittest.mock import MagicMock

import pytest

import vault_adb_wrapper

SERIAL = "TESTSERIAL"


@pytest.fixture
def fake_device():
    device = MagicMock()
    device.serial = SERIAL
    device.shell.return_value = "shell-ok"
    device.push.return_value = "push-ok"
    device.pull.return_value = "pull-ok"
    device.forward.return_value = "forward-ok"
    return device


@pytest.fixture
def fake_client(fake_device):
    client = MagicMock()
    client.devices.return_value = [fake_device]
    return client


@pytest.fixture
def patch_adb_client(monkeypatch, fake_client):
    monkeypatch.setattr(
        vault_adb_wrapper.adbutils, "AdbClient", MagicMock(return_value=fake_client)
    )
    return fake_client


@pytest.fixture
def config_data():
    return {
        SERIAL: {
            "greet": [["shell", "echo hello $ARG0"]],
            "tap_center": [["tap", "500 300"]],
            "wait_a_bit": [["sleep", "0.01"]],
            "chain": [["action", "greet"]],
            "copy_in": [["push", "$ARG0", "$ARG1"]],
            "copy_out": [["pull", "$ARG0", "$ARG1"]],
            "expose_port": [["forward", "$ARG0", "$ARG1"]],
            "copy_in_missing_dest": [["push", "$ARG0"]],
            "unknown_step": [["frobnicate", "x"]],
            "broken_step": [["shell"]],
        }
    }


@pytest.fixture
def config_file(tmp_path, config_data):
    path = tmp_path / "phone.json"
    path.write_text(json.dumps(config_data))
    return path
