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

from .schema import (
    user_schema, night_partition_schema,
    away_mode_partition_schema,
    home_mode_partition_schema,
    partition_on, partition_off, partition_none,
)
# import traceback


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(user_schema),
            vol.Schema(night_partition_schema),
            vol.Schema(away_mode_partition_schema),
            vol.Schema(home_mode_partition_schema)
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("async_unload_entry")
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if DOMAIN in hass.data:
            hass.data[DOMAIN].close()
            hass.data[DOMAIN]  = None
        else:
            entry.runtime_data.close()
            entry.runtime_data = None

    return unload_ok


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
        for i in range(self.max_partitions):
            await self.alarm.send_disarm_partition(i)


    async def async_alarm_arm_mode(self, mode_list, code=None):
        """Send arm command with specific mode list"""
        LOGGER.debug(f"config_entry {self.config_entry.data}")
        partitions = [*range(self.max_partitions)]
        for i in range(self.max_partitions):
            LOGGER.debug(f"mode_list[i] not in self.config_entry.data: {mode_list[i] not in self.config_entry.data}")
            if mode_list[i] in self.config_entry.data:
                LOGGER.debug(f"self.config_entry.data[mode_list[i]] != partition_on: {self.config_entry.data[mode_list[i]] != partition_on}")
            else:
                LOGGER.debug(f"mode_list[i] not in self.config_entry.data[]")
            LOGGER.debug(f"i {i} mode_list[i] {mode_list[i]}")
            if (mode_list[i] not in self.config_entry.data or
                self.config_entry.data[mode_list[i]] != partition_on):
                partitions.remove(i)
        LOGGER.debug(f"len(partitions) {len(partitions)} self.max_partitions {self.max_partitions}")
        if len(partitions) == self.max_partitions:
            await self.alarm.send_arm(code)
        else:
            for i in partitions:
                await self.alarm.send_arm_partition(i, code)
        

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self.async_alarm_arm_mode(CONF_NIGHT_PARTITION_LIST, code)

    async def async_alarm_arm_away(self, code=None):
        """Send arm await command."""
        if self.config_entry.data[CONF_AWAY_MODE_ENABLED]:
            await self.async_alarm_arm_mode(CONF_AWAY_PARTITION_LIST, code)

    async def async_alarm_arm_home(self, code=None):
        """Send arm await command."""
        if self.config_entry.data[CONF_HOME_MODE_ENABLED]:
            await self.async_alarm_arm_mode(CONF_HOME_PARTITION_LIST, code)

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

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intelbras AMT Alarms from a config entry."""
    password=None
    if "password" in entry.data:
       password=entry.data["password"]
    LOGGER.debug("instantiating AlarmHub entry")
    alarm = AlarmHub(hass, entry, entry.data["port"], default_password=password)
    entry.runtime_data = alarm

    await alarm.wait_connection_and_update()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the alarm platform."""
    LOGGER.debug("setup_platform")
