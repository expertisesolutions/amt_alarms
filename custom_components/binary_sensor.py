"""Platform for AMT Intelbras Alarms Sensors."""

import sys

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    LOGGER,
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the alarm platform."""
    hub = hass.data[DOMAIN]

    sensors = []
    for i in range(hub.max_sensors):
        if hub.is_sensor_configured(i):
            sensors += [AlarmSensor(i, hub)]

    for sensor in sensors:
        sensor.update_state()

    add_entities(sensors)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up Intelbras AMT Alarm sensors from a config entry."""
    hub = hass.data[DOMAIN][entry.entry_id]

    sensors = []
    for i in range(hub.max_sensors):
        if hub.is_sensor_configured(i):
            sensors += [AlarmSensor(i, hub)]

    print("adding ", len(sensors), " sensors", file=sys.stderr)
    for sensor in sensors:
        sensor.update_state()

    async_add_entities(sensors)

    # try:
    # except
    return True


class AlarmSensor(BinarySensorEntity):
    """Representation of a infra-red motion sensor."""

    def __init__(self, index, hub):
        """Initialize motion sensor entity representation."""
        LOGGER.error("AlarmSensor instantiation")
        print("AlarmSensor instantiation")
        self.__index = index
        self.__hub = hub
        self._name = hub.name + " motion sensor " + str(index + 1)
        self._unique_id = hub.name + "_motion_" + str(index)
        self._state = STATE_UNAVAILABLE

    @property
    def device_info(self):
        """Return device information for this Entity."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "sw_version": "Unknown",
            "via_device": (DOMAIN, self.panel_unique_id),
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {"device_id": self.unique_id}

    @property
    def should_poll(self):
        """Declare this Entity as Push."""
        return False

    async def async_added_to_hass(self):
        """Entity was added to Home Assistant."""
        # print ("Binary Sensor is calling listen event (not async)", file=sys.stderr)
        self.__hub.listen_event(self)

    async def async_will_remove_from_hass(self):
        """Entity was added to Home Assistant."""
        # print ("Binary Sensor is calling REMOVE listen event", file=sys.stderr)
        self.__hub.remove_listen_event(self)

    @property
    def name(self):
        """Return the name of the binary sensor, if any."""
        return self._name

    @property
    def panel_unique_id(self):
        """Return the unique id for the original panel."""
        return "Alarm Panel.alarm_panel"

    @property
    def unique_id(self):
        """Return the unique id for the sync module."""
        return self._unique_id

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.state == STATE_ON

    @property
    def state(self):
        """Return state."""
        return self._state

    async def async_update(self):
        """Retrieve latest state."""
        self.__hub.listen_event(self)
        # print ("Binary Sensor is calling listen event (from async)", file=sys.stderr)
        await self.__hub.async_update()

    def update_state(self):
        """Update synchronously to current state."""
        old_state = self._state
        open_sensors = self.__hub.get_open_sensors()
        st = open_sensors[self.__index]
        # print ("Binary sensor data is ", open_sensors, " and st is ", st, file=sys.stderr)
        if st is None:
            self._state = STATE_UNAVAILABLE
        elif st is True:
            self._state = STATE_ON
        else:
            self._state = STATE_OFF
        # print ("Binary Sensor state is ", self._state, file=sys.stderr)
        return self._state != old_state

    @callback
    def hub_update(self):
        """Receive callback to update state from Hub."""
        # print ("Binary sensor is updating from hub", file=sys.stderr)
        if self.update_state():
            self.async_write_ha_state()

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return BinarySensorDeviceClass.MOTION
