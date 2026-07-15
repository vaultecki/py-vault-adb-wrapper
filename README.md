# py-vault-adb_wrapper

A Python wrapper for Android Debug Bridge (ADB) operations with JSON-based action configuration.

## Features

- 🔌 **Flexible Connection**: Supports both USB and WiFi connections
- 📝 **JSON Configuration**: Define reusable actions in JSON format
- 🎯 **Type-Safe**: Full type hints for better IDE support
- 🚨 **Exception Handling**: Specific exceptions for different error scenarios
- 📊 **Logging**: Structured logging for debuggingja
- 🔄 **Action Chaining**: Support for nested and sequential actions

## Installation

```bash
pip install .

# or, for development (adds pytest and ruff):
pip install -e ".[dev]"
```

## Requirements

- Python 3.7+
- adbutils >= 2.8.0
- ADB server running (usually part of Android SDK Platform Tools)

## Quick Start

### 1. Create a Configuration File

Create a `phone.json` file with your device configuration:

```json
{
  "TA986027DH": {
    "call_start": [
      ["shell", "am start -a android.intent.action.CALL -d tel:$ARG0"]
    ],
    "call_end": [
      ["shell", "input keyevent KEYCODE_ENDCALL"]
    ],
    "sms_send": [
      ["shell", "am start -a android.intent.action.SENDTO -d sms:$ARG0 --es sms_body \"$ARG1\" --ez exit_on_sent true"],
      ["sleep", "1"],
      ["shell", "input keyevent KEYCODE_ENTER"]
    ],
    "bt_pairing": [
      ["shell", "am start -a android.settings.BLUETOOTH_SETTINGS"],
      ["sleep", "2"],
      ["tap", "500 300"]
    ],
    "screenshot": [
      ["shell", "screencap -p /sdcard/screenshot.png"],
      ["pull", "/sdcard/screenshot.png", "./screenshot.png"]
    ],
    "install_app": [
      ["push", "$ARG0", "/sdcard/app.apk"],
      ["shell", "pm install /sdcard/app.apk"]
    ]
  }
}
```

### 2. Basic Usage

```python
from vault_adb_wrapper import VaultPhone, VaultPhoneException

try:
    # Connect via USB
    phone = VaultPhone(
        uuid="TA986027DH",
        config="phone.json"
    )
    
    # Check connection
    if phone.status():
        print(f"Connected: {phone}")
        print(f"Available actions: {phone.get_available_actions()}")
        
        # Execute actions
        phone.action("call_start", "+491234567890")
        phone.action("call_end")
        
except VaultPhoneException as e:
    print(f"Error: {e}")
```

### 3. WiFi Connection

```python
# Connect via WiFi (requires device to be in WiFi debugging mode)
phone = VaultPhone(
    uuid=["192.168.1.100", "5555"],
    config="phone.json",
    connect_timeout=5.0
)
```

## Configuration Format

The JSON configuration file uses the following structure:

```json
{
  "DEVICE_SERIAL": {
    "action_name": [
      ["action_type", "action_data"],
      ["action_type", "action_data"]
    ]
  }
}
```

### Supported Action Types

| Action Type | Description | Example |
|-------------|-------------|---------|
| `shell` | Execute shell command | `["shell", "am start ..."]` |
| `tap` | Simulate screen tap | `["tap", "500 300"]` or `["tap", "$ARG0 $ARG1"]` |
| `action` | Execute another action | `["action", "other_action"]` |
| `sleep` | Wait for seconds | `["sleep", "2"]` |
| `push` | Push file to device | `["push", "source", "destination"]` |
| `pull` | Pull file from device | `["pull", "source", "destination"]` |
| `forward` | Port forwarding | `["forward", "local_port", "remote_port"]` |

### Argument Substitution

Use `$ARG0`, `$ARG1`, etc. in your action data to substitute runtime arguments:

```json
{
  "send_notification": [
    ["shell", "am broadcast -a android.intent.action.NOTIFY --es title \"$ARG0\" --es message \"$ARG1\""]
  ]
}
```

Then call it with:
```python
phone.action("send_notification", "Hello", "This is a test message")
```

## API Reference

### VaultPhone Class

#### Constructor

```python
VaultPhone(
    uuid: Union[str, List[str]],
    config: Union[str, Path],
    host_ip: str = "127.0.0.1",
    host_port: int = 5037,
    connect_timeout: float = 1.0
)
```

**Parameters:**
- `uuid`: Device serial number or `[IP, Port]` list for WiFi
- `config`: Path to JSON configuration file
- `host_ip`: ADB server IP (default: "127.0.0.1")
- `host_port`: ADB server port (default: 5037)
- `connect_timeout`: Connection timeout in seconds

#### Methods

**`status() -> bool`**
- Returns `True` if device is connected

**`action(action: str, *args) -> List[Any]`**
- Execute a predefined action
- Returns list of results from all action steps
- Raises `ActionNotFoundException` if action not found

**`get_available_actions() -> List[str]`**
- Returns list of available action names

**`uuid` (property)**
- Returns the device UUID

## Exception Hierarchy

```
VaultPhoneException (base)
├── DeviceNotFoundException
├── ConfigNotFoundException
├── ActionNotFoundException
└── InsufficientArgumentsException
```

## Advanced Examples

### Complex Action with Multiple Steps

```json
{
  "install_and_open_app": [
    ["push", "$ARG0", "/sdcard/temp.apk"],
    ["shell", "pm install -r /sdcard/temp.apk"],
    ["sleep", "2"],
    ["shell", "am start -n $ARG1"],
    ["shell", "rm /sdcard/temp.apk"]
  ]
}
```

```python
phone.action(
    "install_and_open_app",
    "myapp.apk",
    "com.example.myapp/.MainActivity"
)
```

### Chained Actions

```json
{
  "setup_device": [
    ["action", "unlock_screen"],
    ["action", "disable_animations"],
    ["action", "clear_notifications"]
  ],
  "unlock_screen": [
    ["shell", "input keyevent KEYCODE_WAKEUP"],
    ["sleep", "0.5"],
    ["shell", "input keyevent KEYCODE_MENU"]
  ],
  "disable_animations": [
    ["shell", "settings put global window_animation_scale 0"],
    ["shell", "settings put global transition_animation_scale 0"],
    ["shell", "settings put global animator_duration_scale 0"]
  ],
  "clear_notifications": [
    ["shell", "service call notification 1"]
  ]
}
```

### Port Forwarding

```python
# Forward local port 8080 to device port 8080
phone.action("setup_forwarding", "8080", "8080")
```

Config:
```json
{
  "setup_forwarding": [
    ["forward", "$ARG0", "$ARG1"]
  ]
}
```

## Logging

The wrapper uses Python's logging module. Configure it as needed:

```python
import logging

# Set to DEBUG for detailed output
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger('vault_adb_wrapper')
logger.setLevel(logging.DEBUG)
```

## Troubleshooting

### Device not found
- Ensure ADB server is running: `adb devices`
- Check USB debugging is enabled on device
- Verify device serial matches your config

### WiFi connection fails
- Enable WiFi debugging: `adb tcpip 5555`
- Ensure device and computer are on same network
- Check firewall settings

### Config not loading
- Verify JSON syntax is valid
- Check file path is correct
- Ensure device UUID matches exactly

## License

Apache License 2.0 - see LICENSE file for details

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- Type hints are included
- Docstrings are updated
- Tests pass (if applicable)

## Author

ecki

## Acknowledgments

- Built on top of [adbutils](https://github.com/openatx/adbutils)
- Inspired by the need for simplified Android automation
