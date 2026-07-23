"""Voltage sensors for AMT Intelbras Alarms (mains and battery)."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricPotential
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, LOGGER


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up AMT voltage sensors from a config entry."""
    hub = entry.runtime_data
    if hub.alarm.system_password is None:
        return True

    sensors = [
        AlarmVoltageSensor(hub, "source"),
        AlarmVoltageSensor(hub, "battery"),
    ]
    for sensor in sensors:
        sensor.update_state()
    async_add_entities(sensors)
    return True


class AlarmVoltageSensor(SensorEntity):
    """Source (mains) or battery voltage reported by the panel."""

    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hub, kind):
        self.hub = hub
        self._kind = kind
        label = "Tensão da fonte" if kind == "source" else "Tensão da bateria"
        self._name = self.hub.alarm.model + " " + label
        self._unique_id = (self.hub.alarm.model + "_"
                           + self.hub.alarm._mac_address.hex() + "_voltage_" + kind)
        self._value = None

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def panel_unique_id(self):
        return self.hub.alarm.model + "_" + self.hub.alarm._mac_address.hex() + "_alarm_panel"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, self.panel_unique_id),
        }

    async def async_added_to_hass(self):
        self.hub.listen_event(self)

    async def async_will_remove_from_hass(self):
        self.hub.remove_listen_event(self)

    @property
    def native_value(self):
        return self._value

    def update_state(self):
        old = self._value
        gs = self.hub.alarm.general_status
        if gs is None:
            self._value = None
        elif self._kind == "source":
            self._value = round(gs.source_voltage, 2)
        else:
            self._value = round(gs.battery_voltage, 2)
        return self._value != old

    @callback
    def alarm_update(self):
        if self.update_state():
            self.async_write_ha_state()
