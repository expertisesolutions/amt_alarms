"""Platform for AMT Intelbras Alarms."""

from typing import Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_platform
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

from .schema import partition_none, partition_on

SERVICE_BYPASS_ZONE = "bypass_zone"
ATTR_ZONES = "zones"
ATTR_CODE = "code"
SERVICE_SILENT_TRIGGER = "alarm_silent_trigger"
SERVICE_AUDIBLE_TRIGGER = "alarm_audible_trigger"
SERVICE_MEDICAL_TRIGGER = "alarm_medical_trigger"
SERVICE_FIRE_TRIGGER = "alarm_fire_trigger"

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

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_BYPASS_ZONE,
        {vol.Required(ATTR_ZONES): cv.ensure_list,
         vol.Optional(ATTR_CODE): cv.string},
        "alarm_bypass",
    )
    platform.async_register_entity_service(
        SERVICE_SILENT_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_SILENT_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_AUDIBLE_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_AUDIBLE_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_MEDICAL_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_MEDICAL_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_FIRE_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_FIRE_TRIGGER,
    )

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

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_BYPASS_ZONE,
        {vol.Required(ATTR_ZONES): cv.ensure_list,
         vol.Optional(ATTR_CODE): cv.string},
        "alarm_bypass",
    )
    platform.async_register_entity_service(
        SERVICE_SILENT_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_SILENT_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_AUDIBLE_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_AUDIBLE_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_MEDICAL_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_MEDICAL_TRIGGER,
    )
    platform.async_register_entity_service(
        SERVICE_FIRE_TRIGGER,
        {vol.Optional(ATTR_CODE): cv.string},
        SERVICE_FIRE_TRIGGER,
    )

    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Intelbras AMT Alarms component."""
    LOGGER.debug("async_setup alarm_control_panel")


class AlarmPanel(AlarmControlPanelEntity):
    """Representation of a alarm panel."""

    _attr_should_poll = False

    def __init__(self, hub: AlarmHub) -> None:
        """Initialize the alarm."""
        LOGGER.debug("AlarmPanel instantiation")
        self._internal_state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub
        supported_features = AlarmControlPanelEntityFeature(0)
        if self.hub.config_entry.data[CONF_HOME_MODE_ENABLED]:
            supported_features = (supported_features | AlarmControlPanelEntityFeature.ARM_HOME)
        if self.hub.config_entry.data[CONF_AWAY_MODE_ENABLED]:
            supported_features = (supported_features | AlarmControlPanelEntityFeature.ARM_AWAY)
        supported_features = (supported_features
                              | AlarmControlPanelEntityFeature.ARM_NIGHT
                              | AlarmControlPanelEntityFeature.TRIGGER)
        self._attr_supported_features = supported_features
        self._attr_code_arm_required = (self.hub.alarm.default_password == None)

    @property
    def code_format(self) -> CodeFormat | None:
        if self._attr_code_arm_required:
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

    async def async_alarm_trigger(self, code=None):
        """Send arm away command."""
        await self.hub.alarm.send_audible_trigger(code)

    async def async_added_to_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.listen_event(self)

    async def async_will_remove_from_hass(self):
        """Entity was added to Home Assistant."""
        self.hub.remove_listen_event(self)

    async def alarm_silent_trigger(self, code: None | str = None):
        """Silent trigger alarm in the alarm system."""
        await self.hub.alarm.send_silent_trigger(code)
        return True

    async def alarm_audible_trigger(self, code: None | str = None):
        """Audible trigger alarm in the alarm system."""
        await self.hub.alarm.send_audible_trigger(code)
        return True

    async def alarm_medical_trigger(self, code: None | str = None):
        """Audible trigger alarm in the alarm system."""
        await self.hub.alarm.send_medical_trigger(code)
        return True

    async def alarm_fire_trigger(self, code: None | str = None):
        """Audible trigger alarm in the alarm system."""
        await self.hub.alarm.send_fire_trigger(code)
        return True

    async def alarm_bypass(self, code: None | str = None, zones = None):
        """Bypass zones in the alarm system."""
        if zones is None:
            _LOGGER.warning("No zones specified for bypass")
            return False
        
        await self.hub.alarm.send_bypass(zones, code)
        return True

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attributes = super().extra_state_attributes
        if attributes is None:
            attributes = {}
        
        bypassed_zones = []
        for i in range(self.hub.alarm.max_sensors):
            if self.hub.alarm.bypassed_sensors[i]:
                bypassed_zones += [i]

        attributes.update({
            "bypassed_zones": bypassed_zones,
        })
        return attributes

    @property
    def available_zones(self):
        """Return a list of available zones."""
        return list(range(self.hub.alarm.max_sensors))

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

    def _is_armed_mode(self, partitions, mode_list):
        for i in range(self.hub.max_partitions):
            value = partition_none
            if mode_list[i] in self.hub.config_entry.data:
                value = self.hub.config_entry.data[mode_list[i]]
                if value == partition_on and not partitions[i]:
                    return False
        return True

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
            is_armed_night = self._is_armed_mode(partitions, CONF_NIGHT_PARTITION_LIST)
            is_armed_home = self._is_armed_mode(partitions, CONF_HOME_PARTITION_LIST)
            is_armed_away = self._is_armed_mode(partitions, CONF_AWAY_PARTITION_LIST)

            if is_armed_home:
                self._internal_state = AlarmControlPanelState.ARMED_HOME
            if is_armed_away:
                self._internal_state = AlarmControlPanelState.ARMED_AWAY
            if is_armed_night:
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
    """Representation of a alarm partition."""

    _attr_should_poll = False

    def __init__(self, hub: AlarmHub, index: int) -> None:
        """Initialize the alarm."""
        self.index = index
        self._internal_state = STATE_UNAVAILABLE
        self._by = "Felipe"
        self.hub = hub
        supported_features = AlarmControlPanelEntityFeature(0)
        if self.hub.config_entry.data[CONF_HOME_MODE_ENABLED]:
            supported_features = (supported_features | AlarmControlPanelEntityFeature.ARM_HOME)
        if self.hub.config_entry.data[CONF_AWAY_MODE_ENABLED]:
            supported_features = (supported_features | AlarmControlPanelEntityFeature.ARM_AWAY)
        supported_features = (supported_features
                              | AlarmControlPanelEntityFeature.ARM_NIGHT)
        self._attr_supported_features = supported_features
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
