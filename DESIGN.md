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

## Protocol

The AMT protocol is a proprietary binary protocol over TCP. The `amtalarm` library handles:

- Connection handshake (`0x94` CONECTAR, `0x95` complementary with MAC/model/firmware)
- Contact ID event reporting (`0xB0`, `0xB4` with timestamps, `0xB5` with photo)
- Time sync requests (`0x80`)
- Device info queries (firmware `0xC0`, model `0xC2`, MAC `0xC4`)
- Optional ISEC Mobile frame wrapper (`0xE9`)
- CRC validation via `crcengine`

The alarm panel pushes events to HA (local_push IoT class). No polling.

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

- **amtalarm** (`git+https://github.com/expertisesolutions/amtalarm.git`): Low-level AMT protocol library (TCP, CRC, Contact ID events)
- **crcengine** (`==0.2`): CRC calculation for protocol frame validation

Both auto-installed by HA from `manifest.json`.

## Known Limitations

- Partition arm modes are identical at the protocol level — the AMT protocol only supports arm/disarm per partition, with no concept of "mode". The three arm methods all send `send_arm_partition`.
- Max 4 partitions (hardware limit).
- Password must be exactly 4 or 6 digits (AMT protocol requirement).
- No YAML configuration — config flow only.
