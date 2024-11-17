"""Platform for AMT Intelbras Alarms."""

from typing import Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)

from . import AlarmHub
from .const import (
    CONF_AWAY_MODE_ENABLED,
    CONF_AWAY_PARTITION_LIST,
    CONF_HOME_MODE_ENABLED,
    CONF_HOME_PARTITION_LIST,
    CONF_NIGHT_PARTITION_LIST,
    DOMAIN,
    LOGGER,
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the alarm platform."""
    print("setup_platform")
    LOGGER.error("setup_platform")

    if discovery_info == {}:
        LOGGER.error("disocvery is empty")
    else:
        LOGGER.error("discovery is not empty")

    hub = hass.data[DOMAIN]
    panels: list[Union[AlarmPanel, PartitionAlarmPanel]] = [AlarmPanel(hub)]
    for i in range(hub.max_partitions):
        panels.append(PartitionAlarmPanel(hub, i))

    for panel in panels:
        panel.update_state()

    add_entities(panels)

    hass.helpers.discovery.load_platform('binary_sensor', DOMAIN, {}, config)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Intelbras AMT Alarms from a config entry."""
    print("async setup entry")
    LOGGER.error("async setup entry")
    hub = hass.data[DOMAIN][entry.entry_id]
    panels: list[Union[AlarmPanel, PartitionAlarmPanel]] = [AlarmPanel(hub)]
    for i in range(hub.max_partitions):
        panels.append(PartitionAlarmPanel(hub, i))

    for panel in panels:
        panel.update_state()

    async_add_entities(panels)

    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Intelbras AMT Alarms component."""
    print("async_setup")
    LOGGER.error("async_setup")


class AlarmPanel(AlarmControlPanelEntity):
    """Representation of a alarm."""

    def __init__(self, hub: AlarmHub) -> None:
        """Initialize the alarm."""
        LOGGER.error("AlarmPanel instantiation")
        print("AlarmPanel instantiation")
        self._state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self.hub.async_alarm_arm_night()

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        await self.hub.async_alarm_arm_home()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self.hub.async_alarm_arm_away()

    async def async_added_to_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.listen_event(self)

    async def async_will_remove_from_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.remove_listen_event(self)

    @property
    def should_poll(self):
        """Declare this Entity as Push."""
        return False

    @property
    def unique_id(self):
        """Return the unique id for the sync module."""
        return self.name + ".alarm_panel"

    @property
    def name(self):
        """Return the name of the panel."""
        return "Alarm panel"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""
        return AlarmControlPanelEntityFeature(
            (
                # AlarmControlPanelEntityFeature.ARM_HOME
                # if self.config_entry.data[CONF_HOME_MODE_ENABLED]
                # else 0
                0
            )
            | (
                # AlarmControlPanelEntityFeature.ARM_AWAY
                # if self.config_entry.data[CONF_AWAY_MODE_ENABLED]
                # else 0
                0
            )
            | AlarmControlPanelEntityFeature.ARM_NIGHT
            | AlarmControlPanelEntityFeature.TRIGGER
            | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
        )

    @property
    def changed_by(self):
        """Last change triggered by."""
        return self._by

    @property
    def device_info(self):
        """Return device information for this Entity."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Intelbras",
            "model": "AMTxxxx",
            "sw_version": "Unknown",
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"device_id": self.unique_id}

    async def async_update(self):
        """Update the state of the device."""
        await self.hub.async_update()

    def update_state(self):
        """Update synchronously to current state."""
        partitions = self.hub.get_partitions()
        triggered_partitions = self.hub.get_triggered_partitions()
        old_state = self._state
        if None in partitions:
            self._state = STATE_UNAVAILABLE
        elif not any(partitions):
            self._state = STATE_ALARM_DISARMED
        else:
            night_partition_check = [False] * self.hub.max_partitions
            away_partition_check = [False] * self.hub.max_partitions
            home_partition_check = [False] * self.hub.max_partitions

            for i in range(self.hub.max_partitions):
                # if CONF_NIGHT_PARTITION_LIST[i] not in self.hub.config_entry.data:
                    night_partition_check[i] = True
                # else:
                #     night_partition_check[i] = (
                #         self.hub.config_entry.data[CONF_NIGHT_PARTITION_LIST[i]]
                #         == partitions[i]
                #     )
                # if CONF_AWAY_PARTITION_LIST[i] not in self.hub.config_entry.data:
                    away_partition_check[i] = True
                # else:
                #     away_partition_check[i] = (
                #         self.hub.config_entry.data[CONF_AWAY_PARTITION_LIST[i]]
                #         == partitions[i]
                #     )
                # if CONF_HOME_PARTITION_LIST[i] not in self.hub.config_entry.data:
                    home_partition_check[i] = True
                # else:
                #     home_partition_check[i] = (
                #         self.hub.config_entry.data[CONF_HOME_PARTITION_LIST[i]]
                #         == partitions[i]
                #     )
            if all(night_partition_check):
                self._state = STATE_ALARM_ARMED_NIGHT
            # elif self.hub.config_entry.data[CONF_AWAY_MODE_ENABLED] and all(
            #     away_partition_check
            # ):
            #     self._state = STATE_ALARM_ARMED_AWAY
            # elif self.hub.config_entry.data[CONF_HOME_MODE_ENABLED] and all(
            #     home_partition_check
            # ):
            #     self._state = STATE_ALARM_ARMED_HOME
            else:
                self._state = STATE_ALARM_DISARMED
        if True in triggered_partitions:
            self._state = STATE_ALARM_TRIGGERED
        return self._state != old_state

    @callback
    def hub_update(self):
        """Receive callback to update state from Hub."""
        if self.update_state():
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self.hub.async_alarm_disarm(code)


class PartitionAlarmPanel(AlarmControlPanelEntity):
    """Representation of a alarm."""

    def __init__(self, hub: AlarmHub, index: int) -> None:
        """Initialize the alarm."""
        self.index = index
        self._state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self.hub.send_arm_partition(self.index)

    async def async_alarm_arm_away(self, code=None):
        """Send arm night command."""
        await self.hub.send_arm_partition(self.index)

    async def async_alarm_arm_home(self, code=None):
        """Send arm night command."""
        await self.hub.send_arm_partition(self.index)

    async def async_added_to_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.listen_event(self)

    async def async_will_remove_from_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.remove_listen_event(self)

    @property
    def should_poll(self):
        """Declare this Entity as Push."""
        return False

    @property
    def panel_unique_id(self):
        """Return the unique id for the original panel."""
        return "Alarm Panel.alarm_panel"

    @property
    def unique_id(self):
        """Return the unique id for the sync module."""
        return self.panel_unique_id + ".partition" + str(self.index)

    @property
    def name(self):
        """Return the name of the panel."""
        return "Alarm panel for partition " + str(self.index + 1)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        """Return the list of supported features."""
        return AlarmControlPanelEntityFeature(
            AlarmControlPanelEntityFeature.ARM_NIGHT
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.TRIGGER
            | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
        )

    @property
    def changed_by(self):
        """Last change triggered by."""
        return self._by

    @property
    def device_info(self):
        """Return device information for this Entity."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Intelbras",
            "model": "AMTxxxx",
            "sw_version": "Unknown",
            "via_device": (DOMAIN, self.panel_unique_id),
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"device_id": self.unique_id}

    async def async_update(self):
        """Update the state of the device."""
        await self.hub.async_update()

    def update_state(self):
        """Update synchronously to current state."""
        partitions = self.hub.get_partitions()
        triggered_partitions = self.hub.get_triggered_partitions()
        old_state = self._state
        if None in partitions:
            self._state = STATE_UNAVAILABLE
        elif partitions[self.index]:
            self._state = STATE_ALARM_ARMED_NIGHT
        else:
            self._state = STATE_ALARM_DISARMED
        if (
            triggered_partitions[self.index] is not None
            and triggered_partitions[self.index]
        ):
            self._state = STATE_ALARM_TRIGGERED
        return self._state != old_state

    @callback
    def hub_update(self):
        """Receive callback to update state from Hub."""
        if self.update_state():
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self.hub.send_disarm_partition(self.index)
