# py-vault-adb-wrapper

Python-Wrapper um [adbutils](https://github.com/openatx/adbutils), der ADB-Aktionen
für ein Gerät als benannte Schritte in einer JSON-Datei definiert.

## Installation

```bash
pip install .

# für Entwicklung (installiert zusätzlich pytest und ruff):
pip install -e ".[dev]"
```

## Voraussetzungen

- Python 3.9+
- adbutils >= 2.8.0
- laufender ADB-Server (Teil der Android SDK Platform Tools)

## Konfiguration

Eine JSON-Datei enthält pro Geräte-Seriennummer (oder `IP:Port`) eine Liste
benannter Aktionen. Jede Aktion ist eine Liste von Schritten
`[typ, ...daten]`.

```json
{
  "TA986027DH": {
    "call_start": [
      ["shell", "am start -a android.intent.action.CALL -d tel:$ARG0"]
    ],
    "call_end": [
      ["shell", "input keyevent KEYCODE_ENDCALL"]
    ],
    "screenshot": [
      ["shell", "screencap -p /sdcard/screenshot.png"],
      ["pull", "/sdcard/screenshot.png", "./screenshot.png"]
    ]
  }
}
```

### Schritt-Typen

| Typ | Bedeutung | Beispiel |
|-----|-----------|----------|
| `shell` | Shell-Befehl ausführen | `["shell", "am start ..."]` |
| `tap` | Tap-Koordinaten senden | `["tap", "500 300"]` |
| `action` | Andere Aktion aus der Config aufrufen | `["action", "unlock_screen"]` |
| `sleep` | Sekunden warten | `["sleep", "2"]` |
| `push` | Datei auf das Gerät kopieren | `["push", "quelle", "ziel"]` |
| `pull` | Datei vom Gerät holen | `["pull", "quelle", "ziel"]` |
| `forward` | Port-Forwarding einrichten | `["forward", "8080", "8080"]` |

`push`, `pull` und `forward` benötigen zwei Datenfelder; fehlt eines, wird
`InsufficientArgumentsException` geworfen.

### Argument-Platzhalter

`$ARG0`, `$ARG1`, ... in den Aktionsdaten werden beim Aufruf durch die
übergebenen Argumente ersetzt (einfache Ersetzung, keine echte
Shell-Quotierung):

```python
phone.action("call_start", "+491234567890")
```

## Verwendung

```python
from vault_adb_wrapper import VaultPhone, VaultPhoneException

try:
    phone = VaultPhone(uuid="TA986027DH", config="phone.json")

    if phone.status():
        phone.action("call_start", "+491234567890")
        phone.action("call_end")
except VaultPhoneException as e:
    print(f"Fehler: {e}")
```

Für eine Verbindung über WLAN (Gerät muss im TCP/IP-Debug-Modus sein):

```python
phone = VaultPhone(uuid=["192.168.1.100", "5555"], config="phone.json")
```

## API

### `VaultPhone(uuid, config, host_ip="127.0.0.1", host_port=5037, connect_timeout=1.0)`

- `uuid`: Geräte-Seriennummer, oder `[ip, port]` für eine WLAN-Verbindung
- `config`: Pfad zur JSON-Konfigurationsdatei
- `host_ip`, `host_port`: Adresse des ADB-Servers
- `connect_timeout`: Timeout in Sekunden für den WLAN-Verbindungsaufbau

Wirft `DeviceNotFoundException`, wenn das Gerät nicht in `adb devices`
auftaucht, und `ConfigNotFoundException`, wenn für die UUID keine
Konfiguration existiert.

### Methoden

- `status() -> bool` — ob das Gerät bei der Initialisierung gefunden wurde
- `action(name, *args) -> list` — führt die Schritte der benannten Aktion
  aus und gibt deren Rückgabewerte als Liste zurück; wirft
  `ActionNotFoundException`, wenn `name` nicht existiert
- `get_available_actions() -> list[str]` — Namen der konfigurierten Aktionen
- `uuid` (Property) — die Geräte-UUID

Ein einzelner fehlschlagender Schritt innerhalb einer Aktion bricht die
Aktion nicht ab: der Fehler wird geloggt, `None` an der entsprechenden
Stelle in die Ergebnisliste eingetragen, und mit dem nächsten Schritt
weitergemacht.

## Exceptions

```
VaultPhoneException
├── DeviceNotFoundException
├── ConfigNotFoundException
├── ActionNotFoundException
└── InsufficientArgumentsException
```

## Logging

Nutzt das Standard-`logging`-Modul unter dem Logger-Namen
`vault_adb_wrapper`.

```python
import logging
logging.getLogger("vault_adb_wrapper").setLevel(logging.DEBUG)
```

## Bekannte Einschränkungen

- Die Argument-Ersetzung escaped nur Anführungszeichen, keine vollständige
  Shell-Quotierung. Bei Verwendung von Nutzereingaben in `shell`-Aktionen
  entsprechend vorsichtig sein.
- Keine Rekursionsprüfung bei `action`-Schritten, die andere Aktionen
  aufrufen (Endlosschleifen bei zyklischer Konfiguration möglich).

## Lizenz

Apache License 2.0, siehe LICENSE.
