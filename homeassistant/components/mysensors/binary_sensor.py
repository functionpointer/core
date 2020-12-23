"""Support for MySensors binary sensors."""
from typing import Callable

from homeassistant.components import mysensors
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SOUND,
    DEVICE_CLASS_VIBRATION,
    DEVICE_CLASSES,
    DOMAIN,
    BinarySensorEntity,
)
from homeassistant.components.mysensors.const import MYSENSORS_DISCOVERY
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import HomeAssistantType

SENSORS = {
    "S_DOOR": "door",
    "S_MOTION": DEVICE_CLASS_MOTION,
    "S_SMOKE": "smoke",
    "S_SPRINKLER": DEVICE_CLASS_SAFETY,
    "S_WATER_LEAK": DEVICE_CLASS_SAFETY,
    "S_SOUND": DEVICE_CLASS_SOUND,
    "S_VIBRATION": DEVICE_CLASS_VIBRATION,
    "S_MOISTURE": DEVICE_CLASS_MOISTURE,
}


async def async_setup_platform(hass: HomeAssistantType, config, async_add_entities, discovery_info=None):
    """Set up the mysensors platform for binary sensors."""
    pass


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, async_add_entities: Callable):
    async def async_discover(discovery_info):
        """Discover and add an MQTT cover."""
        mysensors.setup_mysensors_platform(
            hass,
            DOMAIN,
            discovery_info,
            MySensorsBinarySensor,
            async_add_entities=async_add_entities,
        )

    async_dispatcher_connect(
        hass, MYSENSORS_DISCOVERY.format(config_entry.unique_id, DOMAIN), async_discover
    )

async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    return True

class MySensorsBinarySensor(mysensors.device.MySensorsEntity, BinarySensorEntity):
    """Representation of a MySensors Binary Sensor child node."""

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return self._values.get(self.value_type) == STATE_ON

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        pres = self.gateway.const.Presentation
        device_class = SENSORS.get(pres(self.child_type).name)
        if device_class in DEVICE_CLASSES:
            return device_class
        return None
