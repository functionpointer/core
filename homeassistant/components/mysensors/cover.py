"""Support for MySensors covers."""
import logging
from typing import Callable

from homeassistant.components import mysensors
from homeassistant.components.cover import ATTR_POSITION, DOMAIN, CoverEntity
from homeassistant.components.mysensors.const import MYSENSORS_DISCOVERY
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.dispatcher import async_dispatcher_connect
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the mysensors platform for covers."""
    pass


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities: Callable):

    async def async_discover(discovery_info):
        """Discover and add an MQTT cover."""
        mysensors.setup_mysensors_platform(
            hass,
            DOMAIN,
            discovery_info,
            MySensorsCover,
            async_add_entities=async_add_entities,
        )

    async_dispatcher_connect(
        hass, MYSENSORS_DISCOVERY.format(config_entry.unique_id, DOMAIN), async_discover
    )


class MySensorsCover(mysensors.device.MySensorsEntity, CoverEntity):
    """Representation of the value of a MySensors Cover child node."""

    @property
    def assumed_state(self):
        """Return True if unable to access real state of entity."""
        return self.gateway.optimistic

    @property
    def is_closed(self):
        """Return True if cover is closed."""
        set_req = self.gateway.const.SetReq
        if set_req.V_DIMMER in self._values:
            return self._values.get(set_req.V_DIMMER) == 0
        return self._values.get(set_req.V_LIGHT) == STATE_OFF

    @property
    def current_cover_position(self):
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        set_req = self.gateway.const.SetReq
        return self._values.get(set_req.V_DIMMER)

    async def async_open_cover(self, **kwargs):
        """Move the cover up."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_UP, 1, ack=1
        )
        if self.gateway.optimistic:
            # Optimistically assume that cover has changed state.
            if set_req.V_DIMMER in self._values:
                self._values[set_req.V_DIMMER] = 100
            else:
                self._values[set_req.V_LIGHT] = STATE_ON
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        """Move the cover down."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_DOWN, 1, ack=1
        )
        if self.gateway.optimistic:
            # Optimistically assume that cover has changed state.
            if set_req.V_DIMMER in self._values:
                self._values[set_req.V_DIMMER] = 0
            else:
                self._values[set_req.V_LIGHT] = STATE_OFF
            self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION)
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_DIMMER, position, ack=1
        )
        if self.gateway.optimistic:
            # Optimistically assume that cover has changed state.
            self._values[set_req.V_DIMMER] = position
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        """Stop the device."""
        set_req = self.gateway.const.SetReq
        self.gateway.set_child_value(
            self.node_id, self.child_id, set_req.V_STOP, 1, ack=1
        )
