"""Connect to a MySensors gateway via pymysensors API."""
import logging

import voluptuous as vol
from mysensors import BaseAsyncGateway

from homeassistant.components.mqtt import valid_publish_topic, valid_subscribe_topic
from homeassistant.const import CONF_OPTIMISTIC
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    ATTR_DEVICES,
    CONF_BAUD_RATE,
    CONF_DEVICE,
    CONF_GATEWAYS,
    CONF_NODES,
    CONF_PERSISTENCE,
    CONF_PERSISTENCE_FILE,
    CONF_RETAIN,
    CONF_TCP_PORT,
    CONF_TOPIC_IN_PREFIX,
    CONF_TOPIC_OUT_PREFIX,
    CONF_VERSION,
    DOMAIN,
    MYSENSORS_GATEWAYS,
)
from .device import get_mysensors_devices
from .gateway import finish_setup, get_mysensors_gateway, setup_gateway
from ...config_entries import ConfigEntry
from ...helpers.typing import HomeAssistantType, ConfigType

_LOGGER = logging.getLogger(__name__)

CONF_DEBUG = "debug"
CONF_NODE_NAME = "name"

DEFAULT_BAUD_RATE = 115200
DEFAULT_TCP_PORT = 5003
DEFAULT_VERSION = "2.3"


def has_all_unique_files(value):
    """Validate that all persistence files are unique and set if any is set."""
    persistence_files = [gateway.get(CONF_PERSISTENCE_FILE) for gateway in value]
    if None in persistence_files and any(
        name is not None for name in persistence_files
    ):
        raise vol.Invalid(
            "persistence file name of all devices must be set if any is set"
        )
    if not all(name is None for name in persistence_files):
        schema = vol.Schema(vol.Unique())
        schema(persistence_files)
    return value


def is_persistence_file(value):
    """Validate that persistence file path ends in either .pickle or .json."""
    if value.endswith((".json", ".pickle")):
        return value
    raise vol.Invalid(f"{value} does not end in either `.json` or `.pickle`")


def deprecated(key):
    """Mark key as deprecated in configuration."""

    def validator(config):
        """Check if key is in config, log warning and remove key."""
        if key not in config:
            return config
        _LOGGER.warning(
            "%s option for %s is deprecated. Please remove %s from your "
            "configuration file",
            key,
            DOMAIN,
            key,
        )
        config.pop(key)
        return config

    return validator


NODE_SCHEMA = vol.Schema({cv.positive_int: {vol.Required(CONF_NODE_NAME): cv.string}})

GATEWAY_SCHEMA = {
    vol.Required(CONF_DEVICE): cv.string,
    vol.Optional(CONF_PERSISTENCE_FILE): vol.All(cv.string, is_persistence_file),
    vol.Optional(CONF_BAUD_RATE, default=DEFAULT_BAUD_RATE): cv.positive_int,
    vol.Optional(CONF_TCP_PORT, default=DEFAULT_TCP_PORT): cv.port,
    vol.Optional(CONF_TOPIC_IN_PREFIX): valid_subscribe_topic,
    vol.Optional(CONF_TOPIC_OUT_PREFIX): valid_publish_topic,
    vol.Optional(CONF_NODES, default={}): NODE_SCHEMA,
}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            vol.All(
                deprecated(CONF_DEBUG),
                {
                    vol.Required(CONF_GATEWAYS): vol.All(
                        cv.ensure_list, has_all_unique_files, [GATEWAY_SCHEMA]
                    ),
                    vol.Optional(CONF_OPTIMISTIC, default=False): cv.boolean,
                    vol.Optional(CONF_PERSISTENCE, default=True): cv.boolean,
                    vol.Optional(CONF_RETAIN, default=True): cv.boolean,
                    vol.Optional(CONF_VERSION, default=DEFAULT_VERSION): cv.string,
                },
            )
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config: ConfigType) -> bool:
    """Set up the MySensors component."""
    if config is None:
        #when configured via ConfigEntry, hass calls async_setup(hass,None) and then calls async_setup_entry(...).
        #so in async_setup we have to check if there are any ConfigEntries and then return True. This lets async_setup_entry run.
        return bool(hass.config_entries.async_entries(DOMAIN))


    #there is an actual configuration in configuration.yaml, so we have to process it
    _LOGGER.info("async setup called")

    return True

async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:

    _LOGGER.debug("async_setup_entry: %s (id: %s)", entry.title, entry.unique_id)
    gateway = await setup_gateway(hass, entry)

    if not gateway:
        _LOGGER.error("gateway setup failed")
        return False

    if MYSENSORS_GATEWAYS not in hass.data:
        hass.data[MYSENSORS_GATEWAYS] = []
    hass.data[MYSENSORS_GATEWAYS].append(gateway)

    hass.async_create_task(finish_setup(hass, entry, gateway))

    return True

def _get_mysensors_name(gateway : BaseAsyncGateway, node_id, child_id) -> str:
    """Return a name for a node child."""
    node_name = f"{gateway.sensors[node_id].sketch_name} {node_id}"
    return f"{node_name} {child_id}"


@callback
def setup_mysensors_platform(
    hass,
    domain,
    discovery_info,
    device_class,
    device_args=None,
    async_add_entities=None,
):
    """Set up a MySensors platform."""
    # Only act if called via MySensors by discovery event.
    # Otherwise gateway is not set up.
    if not discovery_info:
        return None
    if device_args is None:
        device_args = ()
    new_devices = []
    new_dev_ids = discovery_info[ATTR_DEVICES]
    for dev_id in new_dev_ids:
        devices = get_mysensors_devices(hass, domain)
        if dev_id in devices:
            continue
        gateway_id, node_id, child_id, value_type = dev_id
        gateway = get_mysensors_gateway(hass, gateway_id)
        if not gateway:
            continue
        device_class_copy = device_class
        if isinstance(device_class, dict):
            child = gateway.sensors[node_id].children[child_id]
            s_type = gateway.const.Presentation(child.type).name
            device_class_copy = device_class[s_type]
        name = _get_mysensors_name(gateway, node_id, child_id)

        args_copy = (*device_args, gateway, node_id, child_id, name, value_type)
        devices[dev_id] = device_class_copy(*args_copy)
        new_devices.append(devices[dev_id])
    if new_devices:
        _LOGGER.info("Adding new devices: %s", new_devices)
        if async_add_entities is not None:
            async_add_entities(new_devices, True)
    return new_devices
