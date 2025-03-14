"""Platform for AMT Intelbras Alarms."""

from typing import Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelState,
    AlarmControlPanelEntityFeature,
    CodeFormat
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
    LOGGER.debug("setup_platform alarm_control_panel")

    if discovery_info == {}:
        LOGGER.debug("disocvery is empty")
    else:
        LOGGER.debug("discovery is not empty")

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
    LOGGER.debug("async setup entry alarm_control_panel")
    hub = entry.runtime_data
    panels: list[Union[AlarmPanel, PartitionAlarmPanel]] = [AlarmPanel(hub)]
    for i in range(hub.max_partitions):
        panels.append(PartitionAlarmPanel(hub, i))

    for panel in panels:
        panel.update_state()

    async_add_entities(panels)

    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Intelbras AMT Alarms component."""
    LOGGER.debug("async_setup alarm_control_panel")


class AlarmPanel(AlarmControlPanelEntity):
    """Representation of a alarm."""

    def __init__(self, hub: AlarmHub) -> None:
        """Initialize the alarm."""
        LOGGER.debug("AlarmPanel instantiation")
        self._internal_state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub

    @property
    def code_arm_required(self) -> bool:
        return self.hub.alarm.default_password == None

    @property
    def code_format(self) -> CodeFormat | None:
        if self.code_arm_required:
            return CodeFormat.NUMBER
        else:
            return None

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self.hub.async_alarm_arm_night(code)

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        await self.hub.async_alarm_arm_home(code)

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        await self.hub.async_alarm_arm_away(code)

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
        return self.hub.alarm.model + "_" + self.hub.alarm._mac_address.hex() + "_alarm_panel"

    @property
    def name(self):
        """Return the name of the panel."""
        return self.hub.alarm.model

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
            "model": self.hub.alarm.model + " control panel",
            "sw_version": "Unknown",
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"device_id": self.unique_id}

    async def async_update(self):
        """Update the state of the device."""
        await self.hub.async_update()

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        return self._internal_state

    def update_state(self):
        """Update synchronously to current state."""
        partitions = self.hub.get_partitions()
        triggered_partitions = self.hub.get_triggered_partitions()
        old_state = self._internal_state
        if None in partitions:
            self._internal_state = STATE_UNAVAILABLE
        elif True in triggered_partitions:
            self._internal_state = AlarmControlPanelState.TRIGGERED
        elif not any(partitions):
            self._internal_state = AlarmControlPanelState.DISARMED
        else:
            self._internal_state = AlarmControlPanelState.ARMED_NIGHT
        return self._internal_state != old_state

    @callback
    def alarm_update(self):
        """Receive callback to update state from Hub."""
        if self.update_state():
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self.hub.async_alarm_disarm(code)


class PartitionAlarmPanel(AlarmControlPanelEntity):
    """Representation of a alarm."""

    _attr_should_poll = False
    _attr_supported_features = (
        | AlarmControlPanelEntityFeature.ARM_NIGHT
        | AlarmControlPanelEntityFeature.TRIGGER
    )
    _attr_code_arm_required = False

    def __init__(self, hub: AlarmHub, index: int) -> None:
        """Initialize the alarm."""
        self.index = index
        self._internal_state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub
        self._attr_supported_features = (
            (
                AlarmControlPanelEntityFeature.ARM_HOME
                if self.hub.config_entry.data[CONF_HOME_MODE_ENABLED]
                else 0
            )
            | (
                AlarmControlPanelEntityFeature.ARM_AWAY
                if self.hub.config_entry.data[CONF_AWAY_MODE_ENABLED]
                else 0
            )
            | AlarmControlPanelEntityFeature.ARM_NIGHT
            | AlarmControlPanelEntityFeature.TRIGGER
        )
        self._attr_code_arm_required = (self.hub.alarm.default_password == None)

    @property
    def code_format(self) -> CodeFormat | None:
        if self._attr_code_arm_required:
            return CodeFormat.NUMBER
        else:
            return None

    async def async_alarm_arm_night(self, code=None):
        """Send arm night command."""
        await self.hub.alarm.send_arm_partition(self.index, code)

    async def async_alarm_arm_away(self, code=None):
        """Send arm night command."""
        await self.hub.alarm.send_arm_partition(self.index, code)

    async def async_alarm_arm_home(self, code=None):
        """Send arm night command."""
        await self.hub.alarm.send_arm_partition(self.index, code)

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
        """Return the unique id for the sync module."""
        return self.hub.alarm.model + "_" + self.hub.alarm._mac_address.hex() + "_alarm_panel"

    @property
    def unique_id(self):
        """Return the unique id for the sync module."""
        return self.hub.alarm.model + "_" + self.hub.alarm._mac_address.hex() + "_partition_" + str(self.index+1) + "_alarm_panel"

    @property
    def name(self):
        """Return the name of the panel."""
        return self.hub.alarm.model + " Partition " + str(self.index+1)

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
            "model": self.hub.alarm.model + " partition control panel",
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

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        return self._internal_state

    def update_state(self):
        """Update synchronously to current state."""
        partitions = self.hub.get_partitions()
        triggered_partitions = self.hub.get_triggered_partitions()
        old_state = self._internal_state
        if None in partitions:
            self._internal_state = STATE_UNAVAILABLE
        elif partitions[self.index]:
            self._internal_state = AlarmControlPanelState.ARMED_NIGHT
        else:
            self._internal_state = AlarmControlPanelState.DISARMED
        if (
            triggered_partitions[self.index] is not None
            and triggered_partitions[self.index]
        ):
            self._internal_state = AlarmControlPanelState.TRIGGERED
        return self._internal_state != old_state

    @callback
    def alarm_update(self):
        """Receive callback to update state from Hub."""
        if self.update_state():
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        await self.hub.alarm.send_disarm_partition(self.index, code)
