"""
ZiGate cover platform that implements covers.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/cover.zigate/
"""
import logging

from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.cover import (
    CoverEntity, ENTITY_ID_FORMAT, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP)
import zigate
from . import DOMAIN as ZIGATE_DOMAIN
from . import DATA_ZIGATE_ATTRS

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return

    myzigate = hass.data[ZIGATE_DOMAIN]

    def sync_attributes():
        devs = []
        for device in myzigate.devices:
            ieee = device.ieee or device.addr  # compatibility
            actions = device.available_actions()
            if not any(actions.values()):
                continue
            for endpoint, action_type in actions.items():
                if [zigate.ACTIONS_COVER] == action_type:
                    key = '{}-{}-{}'.format(ieee,
                                            'cover',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating cover '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZiGateCover(hass, device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateCover(CoverEntity):
    """Representation of a ZiGate cover."""

    def __init__(self, hass, device, endpoint):
        """Initialize the cover."""
        self._device = device
        self._endpoint = endpoint
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)
        self._pos = 100
        self._available = True
        hass.bus.listen('zigate.attribute_updated', self._handle_event)

    def _handle_event(self, call):
        if self._device.ieee == call.data['ieee'] and self._endpoint == call.data['endpoint']:
            _LOGGER.debug("Attribute update received: %s", call.data)
            if call.data['cluster'] == 0x0102 and call.data['attribute'] == 8:
                self._pos = call.data['value']
            if not self.hass:
                raise PlatformNotReady
            self.schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        return False

    def update(self):
        self._device.refresh_device()

    @property
    def name(self) -> str:
        """Return the name of the cover if any."""
        return '{} {}'.format(self._device,
                              self._endpoint)

    @property
    def unique_id(self):
        """Return unique ID for cover."""
        if self._device.ieee:
            return '{}-{}-{}'.format(self._device.ieee,
                                     'cover',
                                     self._endpoint)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': '0x{:02x}'.format(self._endpoint),
        }

    def open_cover(self, **kwargs):
        self.hass.data[ZIGATE_DOMAIN].action_cover(self._device.addr,
                                                   self._endpoint,
                                                   0x00)

    def close_cover(self, **kwargs):
        self.hass.data[ZIGATE_DOMAIN].action_cover(self._device.addr,
                                                   self._endpoint,
                                                   0x01)

    def stop_cover(self, **kwargs):
        self.hass.data[ZIGATE_DOMAIN].action_cover(self._device.addr,
                                                   self._endpoint,
                                                   0x02)

    @property
    def current_cover_position(self):
        """Return the current position of the cover."""
        _LOGGER.debug("current_cover_position")
        attribute = self._device.get_attribute(self._endpoint, 0x0102, 0x0008)
        _LOGGER.debug("attribute: %s", attribute)
        if attribute:
            self._pos = attribute.get('value', 100)
        return self._pos

    @property
    def supported_features(self):
        """Flag supported features."""
        _LOGGER.debug("supported_features")
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP

    @property
    def available(self):
        """Return True if entity is available."""
        _LOGGER.debug("available")
        return self._available

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        _LOGGER.debug("is_closed: %s", self._pos)
        return self._pos == 0
