# Copyright [2025] [ecki]
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import adbutils

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Enum for supported action types"""

    SHELL = "shell"
    TAP = "tap"
    ACTION = "action"
    SLEEP = "sleep"
    PUSH = "push"
    PULL = "pull"
    FORWARD = "forward"


class VaultPhoneException(Exception):
    """Base exception for VaultPhone errors"""


class DeviceNotFoundException(VaultPhoneException):
    """Exception raised when device is not found"""


class ConfigNotFoundException(VaultPhoneException):
    """Exception raised when config is missing or empty"""


class ActionNotFoundException(VaultPhoneException):
    """Exception raised when action is not found in config"""


class InsufficientArgumentsException(VaultPhoneException):
    """Exception raised when insufficient arguments are provided"""


class VaultPhone:
    """
    Wrapper class for ADB operations on Android devices.

    Uses JSON configuration for predefined actions.
    """

    def __init__(
        self,
        uuid: Union[str, list[str]],
        config: Union[str, Path],
        host_ip: str = "127.0.0.1",
        host_port: int = 5037,
        connect_timeout: float = 1.0,
    ):
        """
        Initialize VaultPhone instance.

        Args:
            uuid: Device serial or [IP, Port] for WiFi connection
            config: Path to JSON configuration file
            host_ip: ADB server IP address
            host_port: ADB server port
            connect_timeout: Timeout for connection establishment

        Raises:
            DeviceNotFoundException: When device is not found
            ConfigNotFoundException: When config is missing
        """
        self.client = adbutils.AdbClient(host=host_ip, port=host_port)
        self.device: Optional[adbutils.AdbDevice] = None
        self._connect_timeout = connect_timeout

        # Handle WiFi connection
        if isinstance(uuid, list):
            if len(uuid) != 2:
                raise ValueError("UUID list must contain exactly 2 elements: [IP, Port]")
            uuid_str = f"{uuid[0]}:{uuid[1]}"
            try:
                self.client.connect(uuid_str, timeout=connect_timeout)
                logger.info(f"Connected to {uuid_str}")
            except Exception as e:
                raise DeviceNotFoundException(f"Connection to {uuid_str} failed: {e}") from e
        else:
            uuid_str = uuid

        self.__uuid = uuid_str

        # Find device
        self._find_device()

        # Load config
        self.data = self._load_config(config)

        if not self.data:
            raise ConfigNotFoundException(f"No configuration found for device {self.__uuid}")

        logger.info(f"VaultPhone initialized for {self.__uuid}")

    def _find_device(self) -> None:
        """Find the device in the list of connected devices."""
        devices = self.client.devices()
        for device in devices:
            if device.serial == self.__uuid:
                self.device = device
                return

        raise DeviceNotFoundException(
            f"Device {self.__uuid} not found. Available devices: {[d.serial for d in devices]}"
        )

    def _load_config(self, filename: Union[str, Path]) -> dict[str, Any]:
        """
        Load JSON configuration from file.

        Args:
            filename: Path to config file

        Returns:
            Dictionary with device configuration
        """
        config_path = Path(filename)

        if not config_path.exists():
            logger.error(f"Config file not found: {config_path}")
            return {}

        try:
            with config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(self.__uuid, {})
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing config: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    @property
    def uuid(self) -> str:
        """Return the UUID of the device."""
        return self.__uuid

    def status(self) -> bool:
        """
        Check if device is connected.

        Returns:
            True if connected, False otherwise
        """
        return self.device is not None

    def _substitute_args(self, expression: str, args: tuple[Any, ...]) -> str:
        """
        Replace $ARG0, $ARG1, ... in expression with provided arguments.

        Args:
            expression: String with placeholders
            args: Tuple of arguments

        Returns:
            String with replaced placeholders
        """
        result = expression
        for idx, arg in enumerate(args):
            placeholder = f"$ARG{idx}"
            # Basic escaping strategy for shell security
            safe_arg = str(arg).replace('"', '\\"').replace("'", "\\'")
            result = result.replace(placeholder, safe_arg)
        return result

    def _execute_shell(self, command: str, args: tuple[Any, ...]) -> str:
        """Execute shell command."""
        expr = self._substitute_args(command, args)
        logger.debug(f"Shell: {expr}")
        return self.device.shell(expr)

    def _execute_tap(self, coordinates: str) -> str:
        """Execute tap action."""
        expr = f"input tap {coordinates}"
        logger.debug(f"Tap: {expr}")
        return self.device.shell(expr)

    def _execute_action(self, action_name: str, args: tuple[Any, ...]) -> Any:
        """Execute nested action."""
        return self.action(action_name, *args)

    def _execute_sleep(self, duration: str) -> bool:
        """Wait for specified duration."""
        sleep_time = float(duration)
        logger.debug(f"Sleep: {sleep_time}s")
        time.sleep(sleep_time)
        return True

    def _execute_push(self, args: tuple[Any, ...]) -> Any:
        """Push file to device."""
        if len(args) < 2:
            raise InsufficientArgumentsException("Push requires 2 arguments: source, destination")
        logger.debug(f"Push: {args[0]} -> {args[1]}")
        return self.device.push(args[0], args[1])

    def _execute_pull(self, args: tuple[Any, ...]) -> Any:
        """Pull file from device."""
        if len(args) < 2:
            raise InsufficientArgumentsException("Pull requires 2 arguments: source, destination")
        logger.debug(f"Pull: {args[0]} -> {args[1]}")
        return self.device.pull(args[0], args[1])

    def _execute_forward(self, args: tuple[Any, ...]) -> Any:
        """Set up port forwarding."""
        if len(args) < 2:
            raise InsufficientArgumentsException(
                "Forward requires 2 arguments: local_port, remote_port"
            )
        logger.debug(f"Forward: {args[0]} -> {args[1]}")
        return self.device.forward(f"tcp:{args[0]}", f"tcp:{args[1]}")

    def action(self, action: str, *args: Any) -> list[Any]:
        """
        Execute predefined action from config.

        Args:
            action: Name of the action from config
            *args: Variable arguments for action

        Returns:
            List of results from all steps

        Raises:
            ActionNotFoundException: When action doesn't exist in config
        """
        todo_list = self.data.get(action, [])

        if not todo_list:
            raise ActionNotFoundException(
                f"Action '{action}' not found in config. "
                f"Available actions: {list(self.data.keys())}"
            )

        results = []

        for element in todo_list:
            if not isinstance(element, list) or len(element) < 2:
                logger.warning(f"Invalid action element: {element}")
                continue

            action_type = element[0]
            action_data = element[1]

            try:
                if action_type == ActionType.SHELL.value:
                    result = self._execute_shell(action_data, args)
                elif action_type == ActionType.TAP.value:
                    result = self._execute_tap(action_data)
                elif action_type == ActionType.ACTION.value:
                    result = self._execute_action(action_data, args)
                elif action_type == ActionType.SLEEP.value:
                    result = self._execute_sleep(action_data)
                elif action_type == ActionType.PUSH.value:
                    result = self._execute_push(args)
                elif action_type == ActionType.PULL.value:
                    result = self._execute_pull(args)
                elif action_type == ActionType.FORWARD.value:
                    result = self._execute_forward(args)
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    result = None

                results.append(result)

            except Exception as e:
                logger.error(f"Error in action step {action_type}: {e}")
                results.append(None)

        return results

    def get_available_actions(self) -> list[str]:
        """
        Get list of available actions.

        Returns:
            List of action names
        """
        return list(self.data.keys())

    def __repr__(self) -> str:
        """String representation of the instance."""
        status = "connected" if self.status() else "disconnected"
        return f"VaultPhone(uuid={self.__uuid}, status={status})"


if __name__ == "__main__":
    # Example usage
    try:
        phone = VaultPhone(
            uuid="TA986027DH",  # or ["192.168.1.100", "5555"] for WiFi
            config="phone.json",
            host_ip="127.0.0.1",
            host_port=5037,
        )

        if phone.status():
            print(f"Phone connected: {phone}")
            print(f"Available actions: {phone.get_available_actions()}")

            # Example actions (commented out)
            # phone.action("call_start", "+491234567890")
            # phone.action("call_end")
            # phone.action("bt_pairing")
            # phone.action("sms_send", "+491234567890", "Test SMS")

    except VaultPhoneException as e:
        logger.error(f"VaultPhone error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
