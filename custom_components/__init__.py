"""The Intelbras AMT Alarms integration."""
import asyncio
import socket
import time
from typing import Union

from amtalarm import AMTAlarm
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    discovery_flow
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)

from .const import (
    CONF_AWAY_MODE_ENABLED,
    CONF_AWAY_PARTITION_1,
    CONF_AWAY_PARTITION_2,
    CONF_AWAY_PARTITION_3,
    CONF_AWAY_PARTITION_4,
    CONF_AWAY_PARTITION_LIST,
    CONF_HOME_MODE_ENABLED,
    CONF_HOME_PARTITION_1,
    CONF_HOME_PARTITION_2,
    CONF_HOME_PARTITION_3,
    CONF_HOME_PARTITION_4,
    CONF_HOME_PARTITION_LIST,
    CONF_NIGHT_PARTITION_1,
    CONF_NIGHT_PARTITION_2,
    CONF_NIGHT_PARTITION_3,
    CONF_NIGHT_PARTITION_4,
    CONF_NIGHT_PARTITION_LIST,
    CONF_PASSWORD,
    CONF_PORT,
    DOMAIN,
    LOGGER,
)

# import traceback


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.port,
                vol.Optional(CONF_PASSWORD): int,
                vol.Optional(CONF_NIGHT_PARTITION_1): bool,
                vol.Optional(CONF_NIGHT_PARTITION_2): bool,
                vol.Optional(CONF_NIGHT_PARTITION_3): bool,
                vol.Optional(CONF_NIGHT_PARTITION_4): bool,
                vol.Optional(CONF_AWAY_MODE_ENABLED): bool,
                vol.Optional(CONF_AWAY_PARTITION_1): bool,
                vol.Optional(CONF_AWAY_PARTITION_2): bool,
                vol.Optional(CONF_AWAY_PARTITION_3): bool,
                vol.Optional(CONF_AWAY_PARTITION_4): bool,
                vol.Optional(CONF_HOME_MODE_ENABLED): bool,
                vol.Optional(CONF_HOME_PARTITION_1): bool,
                vol.Optional(CONF_HOME_PARTITION_2): bool,
                vol.Optional(CONF_HOME_PARTITION_3): bool,
                vol.Optional(CONF_HOME_PARTITION_4): bool,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("async_unload_entry")
    # unload_ok = all(
    #     await asyncio.gather(
    #         *[
    #             hass.config_entries.async_forward_entry_unload(entry, component)
    #             for component in PLATFORMS
    #         ]
    #     )
    # )
    # if unload_ok:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _bcd_to_decimal(mbytes: bytes, unescape_zeros=True):
    """Convert a sequence of bcd encoded decimal to integer."""

    def unescape_zero(i: int):
        return i if i != 0xA else 0

    if unescape_zeros:
        mbytes = bytes(unescape_zero(b) for b in mbytes)

    len_mbytes = len(mbytes)
    return sum(10 ** (len_mbytes - i - 1) * b for i, b in enumerate(mbytes))


def _decimal_to_bcd_nibble(decimal: int):
    """Convert a decimal between 0 to 99 into two bcd encoded nibbles."""
    if decimal < 0 or decimal > 99:
        raise ValueError("argument must be non negative")

    ones = decimal % 10
    tens = decimal // 10

    return tens << 4 | ones


class AlarmHub:
    """Placeholder class to make tests pass."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, port, default_password=None
    ) -> None:
        """Initialize."""

        LOGGER.debug("AlarmHub instantiation")
        self.default_password = None;
        if default_password is not None:
            self.default_password = str(default_password)
            if len(self.default_password) != 4 and len(self.default_password) != 6:
                raise ValueError

        self.hass = hass
        self.config_entry = config_entry

        self.alarm = AMTAlarm(port, default_password=default_password, logger=LOGGER)

    @property
    def name(self):
        """Return unique name from device."""
        return "AMTAlarm"

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""

    async def async_alarm_arm_night(self, code=None):
        """Send disarm command."""
        for i in range(self.max_partitions):
            if CONF_NIGHT_PARTITION_LIST[i] in self.config_entry.data:
                if self.config_entry.data[CONF_NIGHT_PARTITION_LIST[i]]:
                    await self.send_arm_partition(i)
            else:
                await self.send_arm_partition(i)

    async def async_alarm_arm_away(self, code=None):
        """Send disarm command."""
        if self.config_entry.data[CONF_AWAY_MODE_ENABLED]:
            for i in range(self.max_partitions):
                if CONF_AWAY_PARTITION_LIST[i] in self.config_entry.data:
                    if self.config_entry.data[CONF_AWAY_PARTITION_LIST[i]]:
                        self.send_arm_partition(i)
                else:
                    self.send_arm_partition(i)

    async def async_alarm_arm_home(self, code=None):
        """Send disarm command."""
        if self.config_entry.data[CONF_HOME_MODE_ENABLED]:
            for i in range(self.max_partitions):
                if CONF_HOME_PARTITION_LIST[i] in self.config_entry.data:
                    if self.config_entry.data[CONF_HOME_PARTITION_LIST[i]]:
                        await self.send_arm_partition(i)
                else:
                    await self.send_arm_partition(i)

    def close(self):
        """Close and free resources."""
        self.alarm.close()

    async def wait_connection_and_update(self):
        """Call asynchronously wait_connection and then after a update."""
        return await self.alarm.wait_connection_and_update()

    async def wait_connection(self):
        """Call asynchronously wait_connection and then after a update."""
        return await self.alarm.wait_connection()

    def get_partitions(self):
        """Return partitions array."""
        return self.alarm.partitions

    def get_triggered_partitions(self):
        """Return partitions array."""
        return self.alarm.triggered_partitions

    def get_open_sensors(self):
        """Return motion sensors states."""
        return self.alarm.open_sensors

    def listen_event(self, listener):
        """Add object as listener."""
        self.alarm.listen_event(listener)

    def remove_listen_event(self, listener):
        """Add object as listener."""
        self.alarm.remove_listen_event(listener)

    @property
    def max_sensors(self):
        """Return the maximum number of sensors the platform may have."""
        return self.alarm.max_sensors

    def is_sensor_configured(self, index):
        """Check if the numbered sensor is configured."""
        return self.alarm.is_sensor_configured(index)

    @property
    def max_partitions(self):
        """Return the maximum number of partitions the platform may have."""
        return self.alarm.max_partitions

    def is_partition_configured(self, index):
        """Check if the numbered partition is configured."""
        return self.alarm.is_partition_configured(index)


# async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
#     """Set up the Intelbras AMT Alarms component."""
#     LOGGER.error("__init__ async_setup")

#     if DOMAIN not in config:
#         return True

#     config = config[DOMAIN]

#     print("instantiating AlarmHub no entry")
#     alarm = AlarmHub(hass, {}, config.get(CONF_PORT), config.get(CONF_PASSWORD))
#     hass.data[DOMAIN] = alarm

#     print("will wait connection and update")
#     await alarm.wait_connection_and_update()

#     print("wait connection and updated")
    
#     hass.helpers.discovery.load_platform(PLATFORMS, DOMAIN, {}, config)

#     #alarm_control_panel.async_setup(
#     #hass.async_create_task(async_initialize_alarm(hass, alarm, config))

#     # panels: list[Union[AlarmPanel, PartitionAlarmPanel]] = [AlarmPanel(alarm, entry)]
#     # for i in range(alarm.max_partitions):
#     #     panels.append(PartitionAlarmPanel(alarm, i))

#     # for panel in panels:
#     #     panel.update_state()

#     # add_entities(panels)
    
#     return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intelbras AMT Alarms from a config entry."""
    password=None
    if "password" in entry.data:
       password=entry.data["password"]
    LOGGER.debug("instantiating AlarmHub entry")
    alarm = AlarmHub(hass, entry, entry.data["port"], default_password=password)
    entry.runtime_data = alarm

    await alarm.wait_connection_and_update()

    # device_registry = dr.async_get(hass)

    # device_registry.async_get_or_create(
    #     config_entry_id=entry.entry_id,
    #     identifiers={(DOMAIN, str(entry.data["port"]))},
    #     manufacturer="Intelbras",
    #     name=f"Intelbras",
    #     model=alarm.alarm.model,
    #     sw_version="0.0.1",
    # )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the alarm platform."""
    LOGGER.debug("setup_platform")
