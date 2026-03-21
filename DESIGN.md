# Design — amt_alarms

Custom Home Assistant integration for Intelbras AMT alarm panels (AMT 4010 Smart, XEG 4000 Smart, etc.).

## Architecture

```
Home Assistant
  │
  ├─ ConfigFlow (UI setup, 4 steps)
  │   └─ Validates TCP connection to alarm panel
  │
  ├─ AlarmHub (entry.runtime_data)
  │   └─ AMTAlarm (amtalarm library)
  │       └─ TCP socket → alarm panel (port 9009)
  │
  ├─ AlarmPanel (main alarm_control_panel entity)
  │   ├─ States: armed_night / armed_away / armed_home / disarmed / triggered / unavailable
  │   ├─ Mode detection: compares active partitions against configured partition maps
  │   └─ Services: bypass_zone, silent/audible/medical/fire trigger
  │
  ├─ PartitionAlarmPanel (one per partition, up to 4)
  │   ├─ States: armed_night / disarmed / triggered / unavailable
  │   └─ Individual arm/disarm (protocol limitation: no per-partition modes)
  │
  └─ AlarmSensor (binary_sensor, one per configured zone)
      └─ Motion detection state from alarm panel
```

## IsecNet V1 Protocol

Proprietary binary protocol over TCP (default port 9009). The alarm panel initiates the connection to HA (which acts as a TCP server). Push-based — no polling.

### Frame Format

```
[NumBytes] [Command] [Data...] [CheckSum]
```

- **NumBytes** (1 byte): total frame length including this byte (min 3: NumBytes + Command + CheckSum)
- **Command** (1 byte): command identifier
- **Data** (variable): command-specific payload
- **CheckSum** (1 byte): XOR all preceding bytes, then XOR with `0xFF`

Example — heartbeat (0xF7): `03 F7 0B` → `03 XOR F7 = F4`, `F4 XOR 0xFF = 0B` ✓

### Checksum Algorithm

```python
def checksum(frame_bytes):
    xor = 0
    for b in frame_bytes:
        xor ^= b
    return xor ^ 0xFF
```

### Connection Flow

1. Alarm panel connects to HA on configured TCP port (default 9009)
2. Panel sends `0x94` (CONECTAR) — basic connection announcement
3. HA responds with `0x94` ACK
4. Panel sends `0x95` (extended connect) with MAC address, model code, firmware version
5. HA responds with `0x95` ACK
6. Connection established — panel starts sending events, HA can send commands

After connection, HA polls status every ~1s via `send_request_zones()` (ISEC Mobile 0x5B command).

### Reconnection

If the TCP connection drops, the alarm panel will re-initiate connection. The `amtalarm` library handles this via `__accept_new_connection()` which creates a new asyncio task for the new socket.

## Command Reference

### Receiving Events (Panel → HA)

| Command | Name | Description |
|---------|------|-------------|
| `0x94` | CONECTAR | Basic connection handshake |
| `0x95` | Extended connect | MAC (6 bytes), model code (1 byte), firmware (variable) |
| `0xF7` | Heartbeat | Keep-alive, sent periodically by panel |
| `0x80` | DateTime request | Panel requests current date/time from HA |
| `0xB0` | Contact ID event | Standard alarm event (no timestamp) |
| `0xB4` | Contact ID + timestamp | Alarm event with date/time |
| `0xB5` | Contact ID + photo | Alarm event with attached photo (AMT 8000) |

### Device Info Queries (HA → Panel)

| Command | Name | Response contains |
|---------|------|-------------------|
| `0xC0` | Firmware version | Firmware string |
| `0xC2` | Model | Model name string |
| `0xC4` | MAC address | 6-byte MAC |
| `0xC6` | Central phone | Phone number |
| `0xC8` | Account | Account ID |
| `0xCA` | Num zones | Number of configured zones |
| `0xCC` | Num partitions | Number of partitions |
| `0xD1` | Zone names | Names of alarm zones |
| `0xD3` | Partition names | Names of partitions |

### ISEC Mobile Wrapper (0xE9)

Used for arm/disarm/bypass/status commands. Frame structure:

```
[NumBytes] 0xE9 0x21 [password_ascii...] [command] [data...] 0x21 [CheckSum]
```

- `0x21` is used as a delimiter before and after the payload
- Password is sent as ASCII digits (e.g., "1234" → `0x31 0x32 0x33 0x34`)
- If no password: just `0xE9 0x21 [command] [data...] 0x21`

#### ISEC Mobile Commands

| Command | Name | Data | Description |
|---------|------|------|-------------|
| `0x41` | Arm partition | `0x40 + partition + 1` | Arm a specific partition (1-indexed) |
| `0x44` | Disarm partition | `0x40 + partition + 1` | Disarm a specific partition |
| `0x42` | Bypass zones | 8-byte zone bitmap | Bypass specified zones before arming |
| `0x45` | Trigger/panic | panic_type byte | Trigger panic (silent/audible/medical/fire) |
| `0x5B` | Request zones/status | (none) | Request current sensor and partition status |
| `0x50` | PGM control | PGM number + state | Control PGM outputs |

#### Arm/Disarm Data Encoding

Partition number is encoded as `0x40 + partition_index + 1`:
- Partition 1: `0x42` (0x40 + 0 + 1 = 0x41... actually `0x40 + 1 = 0x41`)
- Partition 2: `0x42`
- Partition 3: `0x43`
- Partition 4: `0x44`

(The amtalarm library uses `0x40 + partition + 1` where partition is 0-indexed)

#### Bypass Zone Bitmap

8 bytes, each bit represents a zone (LSB = zone 1 of that byte):
- Byte 0, bit 0 = zone 1
- Byte 0, bit 7 = zone 8
- Byte 1, bit 0 = zone 9
- ...up to zone 64 (only 48 used)

#### Panic Types (0x45 command)

| Value | Type |
|-------|------|
| `0x00` | Silent panic |
| `0x01` | Audible panic |
| `0x02` | Medical emergency |
| `0x03` | Fire alarm |

### ISEC Mobile Status Response

Response to `0x5B` request. 54+ byte packet inside 0xE9 wrapper:

| Offset | Size | Description |
|--------|------|-------------|
| 1-6 | 6 bytes | Open sensors bitmap (48 zones, 1 bit each) |
| 9-14 | 6 bytes | Triggered sensors bitmap |
| 17-22 | 6 bytes | Bypassed sensors bitmap |
| 28-29 | 2 bytes | Partition states (bit per partition, byte 28 = armed, byte 29 = triggered) |
| 30 | 1 byte | Siren/status flags |
| 36 | 1 byte | Battery/power status |
| 43 | 1 byte | Communication error flags |

Sensor bitmaps: 6 bytes × 8 bits = 48 zones max. Bit set = sensor open/triggered/bypassed.

Partition bytes: bit 0 = partition 1, bit 1 = partition 2, etc. Up to 4 partitions.

### IsecProgram Wrapper (0xE7)

Used for programming/authentication commands. Uses **CRC-16** (polynomial 0x8005) instead of XOR checksum.

```
[NumBytes] 0xE7 [data...] [CRC-16 high] [CRC-16 low]
```

#### IsecProgram Commands

| Command | Name | Description |
|---------|------|-------------|
| `0x11` | Authenticate | Send password for programming access |
| Zone name read/write | Various | Read/write zone names |
| Password read/write | Various | Read/write user passwords |
| EEPROM read/write | Various | Direct EEPROM access (advanced) |

### CRC-16 Algorithm

Polynomial: `0x8005`, used for IsecProgram (0xE7) frames only.

```python
import crcengine
crc16 = crcengine.new('crc16')
crc_value = crc16(frame_bytes)
```

The `crcengine` library (v0.2) is a dependency in `manifest.json`.

## Contact ID Events

Standard alarm industry format for event reporting. Used in 0xB0, 0xB4, 0xB5 commands.

### Event Format

```
ACCT MT QXYZ GG CCC
```

- **ACCT**: 4-digit account number
- **MT**: message type (18 = Contact ID)
- **Q**: event qualifier — `0x01` = new event/opening, `0x03` = restore/closing
- **XYZ**: 3-digit event code (see table below)
- **GG**: partition/group number (2 digits)
- **CCC**: zone/user number (3 digits)

**BCD encoding**: digit 0 is encoded as `0xA` in the protocol.

### Common Event Codes

| Code | Q=01 (Event) | Q=03 (Restore) |
|------|-------------|-----------------|
| 100 | Medical alarm | Medical restore |
| 110 | Fire alarm | Fire restore |
| 120 | Panic alarm | Panic restore |
| 130 | Burglar alarm | Burglar restore |
| 131 | Perimeter alarm | Perimeter restore |
| 132 | Interior alarm | Interior restore |
| 137 | Tamper | Tamper restore |
| 300 | System trouble | System restore |
| 301 | AC power loss | AC power restore |
| 302 | Low battery | Battery restore |
| 305 | System reset | — |
| 350 | Communication trouble | Comm restore |
| 400 | Arm/disarm (away) | — |
| 401 | Arm/disarm (user) | — |
| 403 | Auto arm | — |
| 407 | Arm (remote) | Disarm (remote) |
| 408 | Quick arm | — |
| 409 | Arm (keyswitch) | Disarm (keyswitch) |
| 461 | Wrong password | — |
| 570 | Zone bypass | Zone unbypass |
| 602 | Periodic test | — |
| 616 | Service request | — |
| 621 | Event log reset | — |
| 625 | Date/time set | — |

### Event with Timestamp (0xB4)

Same as 0xB0 but prepended with 6 bytes: `YY MM DD HH MM SS` (BCD encoded).

### Event with Photo (0xB5)

AMT 8000 only. Contact ID event followed by photo data fragments.

## Model Codes

Sent in the 0x95 extended connect frame:

| Code | Model |
|------|-------|
| `0x1E` | AMT 2018 E / AMT 2018 EG |
| `0x34` | AMT 2018 E Smart |
| `0x36` | AMT 1000 Smart |
| `0x41` | AMT 4010 / AMT 4010 Smart |
| `0x61` | AMT 1016 NET |
| `0x29` | XEG 4000 Smart |

## IsecNet V2 Protocol

Used by AMT 8000 series. Extended frame format with 2-byte addressing:

```
[NumBytes_H] [NumBytes_L] [DST_H] [DST_L] [SRC_H] [SRC_L] [Command_H] [Command_L] [Data...] [CRC-16]
```

- 2-byte frame length, 2-byte destination/source IDs, 2-byte command
- Uses CRC-16 (same polynomial 0x8005)
- Not used by this integration (only V1 models supported)

### AMT 8000 APP Mobile Commands (V2)

| Command | Name | Description |
|---------|------|-------------|
| `0xF0F0` | Auth | Authenticate with password |
| `0x0B4A` | Status request | Request panel status |
| `0x401F` | Bypass | Bypass zones |
| `0x401E` | Arm/Disarm | Arm or disarm partitions |
| `0x401A` | Panic | Trigger panic alarm |
| `0x0BB0` | Photo fragment | Receive photo data |

## Receptor IP Connection (Optional)

For connecting through an Intelbras Receptor IP (gateway device):

1. Send `0xE0` init frame to receptor
2. Send `0xE3` with account number to check link
3. Send `0xE4` to establish link to specific alarm panel
4. Once linked, `0xE7` and `0xE9` frames are relayed to the panel

This mode is NOT used by this integration (direct TCP connection instead).

## Arm Mode Logic

The main panel maps HA arm modes to partition combinations:

- **Night mode** (always enabled): which partitions must be armed for `armed_night`
- **Away mode** (optional): which partitions must be armed for `armed_away`
- **Home mode** (optional): which partitions must be armed for `armed_home`

Each partition can be:
- **Active** (`partition_on`): must be armed for the mode to match
- **Not active** (`partition_off`): not used (reserved)
- **Don't care** (`partition_none`): ignored in mode detection

### Mode detection (`_is_armed_mode`)

Returns `True` only if:
1. At least one partition is configured as Active for this mode
2. All Active partitions are currently armed

Priority when multiple modes match: **night > away > home** (enforced by `if/elif` chain in `update_state`).

### Partition entities

Individual partitions have no concept of "mode" — the AMT protocol only supports arm/disarm per partition. All three arm actions (`arm_night`, `arm_away`, `arm_home`) send the same `send_arm_partition` command. State is always `armed_night` when armed.

## Config Flow

4-step wizard, same structure for both initial setup (ConfigFlow) and reconfiguration (OptionsFlowHandler):

1. **User step**: TCP port (default 9009) + optional password (4-6 digits)
2. **Night mode**: partition 1-4 requirements (Active/Not active/Don't care)
3. **Away mode**: enable toggle + partition requirements
4. **Home mode**: enable toggle + partition requirements → saves entry

Config is stored in `entry.data`. The Options flow updates `entry.data` directly (not `entry.options`).

## Entity IDs

Entity IDs are derived from the alarm model name + MAC address:

- Panel: `alarm_control_panel.{model}_{mac}_alarm_panel`
- Partitions: `alarm_control_panel.{model}_{mac}_partition_{N}_alarm_panel`
- Sensors: `binary_sensor.{model}_{mac}_motion_{N}`

Where `{model}` = e.g. `xeg_4000_smart`, `{mac}` = hex MAC, `{N}` = 1-based index.

## Event System

Push-based updates: `AlarmHub` wraps `AMTAlarm.listen_event()` / `remove_listen_event()`. When the alarm panel sends an event, `AMTAlarm` calls `alarm_update()` on all registered listeners. Each entity's `alarm_update` callback calls `update_state()` and writes HA state if changed.

No polling (`should_poll = False`, no `async_update` methods).

## Custom Services

Registered on the `alarm_control_panel` entity platform:

| Service | Parameters | Description |
|---------|-----------|-------------|
| `bypass_zone` | `zones` (list), `code` (optional) | Bypass zones before arming |
| `alarm_silent_trigger` | `code` (optional) | Silent panic trigger |
| `alarm_audible_trigger` | `code` (optional) | Audible panic trigger |
| `alarm_medical_trigger` | `code` (optional) | Medical emergency |
| `alarm_fire_trigger` | `code` (optional) | Fire alarm |

## Files

```
custom_components/amt_alarms/
├── __init__.py              # AlarmHub class, entry setup/unload
├── alarm_control_panel.py   # AlarmPanel + PartitionAlarmPanel entities
├── binary_sensor.py         # AlarmSensor entities (motion zones)
├── config_flow.py           # ConfigFlow + OptionsFlowHandler
├── const.py                 # Constants, config keys, AMT event codes
├── schema.py                # Voluptuous schemas for config flow
├── manifest.json            # HA integration metadata (v0.0.5.12)
├── services.yaml            # Service definitions for HA UI
├── strings.json             # Config flow UI text
└── translations/en.json     # English translations
```

## Dependencies

- **amtalarm** (`git+https://github.com/expertisesolutions/amtalarm.git`): Low-level AMT protocol library (TCP server, CRC, Contact ID event parsing, ISEC Mobile command framing)
- **crcengine** (`==0.2`): CRC-16 calculation for IsecProgram frame validation

Both auto-installed by HA from `manifest.json`.

## Deployment

The integration is a git submodule of the homeassistant-config repo. To deploy:

```bash
# From homeassistant-config root
rsync -av amt_alarms/custom_components/amt_alarms/ homeassistant:/config/custom_components/amt_alarms/
ssh homeassistant 'ha core restart'
```

Or install via HACS as a custom repository pointing to the amt_alarms repo.

## SDK Reference

The protocol is documented in Intelbras "SDK Centrais de Alarme" (v1.0.1), an Excel workbook with 10 sheets:

1. IsecNet V1 protocol (frame format, checksum)
2. Event receiving (commands 0x94, 0x95, 0xB0, 0xB4, 0xB5, 0x80, 0xC0-0xD3)
3. Receptor IP connection (0xE0, 0xE3, 0xE4, 0xE7/0xE9 relay)
4. ISEC Mobile commands (arm/disarm/bypass/status/panic/PGM)
5. ISEC Program commands (auth, zone names, passwords, EEPROM)
6. IsecNet V2 (AMT 8000, 2-byte addressing)
7. Photo retrieval (AMT 8000)
8. Checksum calculator
9. Contact ID event code list
10. Frame decoder tool

Local copy: `~/dev/homeassistant/SDKCentraisDeAlarmeIntelbras-v1.0.1.xlsx`

EEPROM map for AMT 8000: `~/dev/homeassistant/Mapa EEPROM AMT 8000 V22.xlsx`

amtalarm library source: `~/dev/homeassistant/dev/amtalarm/`

## Known Limitations

- Partition arm modes are identical at the protocol level — the AMT protocol only supports arm/disarm per partition, with no concept of "mode". The three arm methods all send `send_arm_partition`.
- Max 4 partitions (hardware limit, 48 zones max).
- Password must be exactly 4 or 6 digits (AMT protocol requirement).
- No YAML configuration — config flow only.
- IsecNet V2 (AMT 8000) not supported — only V1 models.
- Photo events (0xB5) received but not processed beyond Contact ID extraction.
- No Receptor IP support — direct TCP only.
