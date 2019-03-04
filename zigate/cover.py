"""
ZiGate cover platform that implements covers.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/cover.zigate/
"""
import logging

from homeassistant.components.cover import (
    CoverDevice, ENTITY_ID_FORMAT)
try:
    from homeassistant.components.zigate import DOMAIN as ZIGATE_DOMAIN
    from homeassistant.components.zigate import DATA_ZIGATE_ATTRS
except ImportError:  # temporary until official support
    from custom_components.zigate import DOMAIN as ZIGATE_DOMAIN
    from custom_components.zigate import DATA_ZIGATE_ATTRS

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zigate']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return

    myzigate = hass.data[ZIGATE_DOMAIN]
    import zigate

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
                    entity = ZiGateCover(device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateCover(CoverDevice):
    """Representation of a ZiGate cover."""

    def __init__(self, device, endpoint):
        """Initialize the cover."""
        self._device = device
        self._endpoint = endpoint
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)

    @property
    def should_poll(self) -> bool:
        return self._device.assumed_state

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
            'endpoint': self._endpoint,
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
