"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/binary_sensor.zigate/
"""
import logging

from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.binary_sensor import (BinarySensorEntity,
                                                    ENTITY_ID_FORMAT)
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
            if any(actions.values()):
                continue
            for attribute in device.attributes:
                if attribute['cluster'] < 5:
                    continue
                if 'name' in attribute:
                    key = '{}-{}-{}-{}'.format(ieee,
                                               attribute['endpoint'],
                                               attribute['cluster'],
                                               attribute['attribute'],
                                               )
                    value = attribute.get('value')
                    if value is None:
                        continue
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    if type(value) in (bool, dict):
                        _LOGGER.debug(('Creating binary sensor '
                                       'for device '
                                       '{} {}').format(device,
                                                       attribute))
                        entity = ZiGateBinarySensor(hass, device, attribute)
                        devs.append(entity)
                        hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateBinarySensor(BinarySensorEntity):
    """representation of a ZiGate binary sensor."""

    def __init__(self, hass, device, attribute):
        """Initialize the sensor."""
        self._device = device
        self._attribute = attribute
        self._device_class = None
        if self._is_zone_status():
            self._is_on = attribute.get('value', {}).get('alarm1', False)
        else:
            self._is_on = attribute.get('value', False)
        name = attribute.get('name')
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          name)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)

        typ = self._device.get_value('type', '').lower()
        if name == 'presence':
            self._device_class = 'motion'
        elif 'magnet' in typ:
            self._device_class = 'door'
        elif 'smok' in typ:
            self._device_class = 'smoke'
        elif 'zone_status' in name:
            self._device_class = 'safety'
        hass.bus.listen('zigate.attribute_updated', self._handle_event)

    def _handle_event(self, call):
        if (
            self._device.ieee == call.data['ieee']
            and self._attribute['endpoint'] == call.data['endpoint']
            and self._attribute['cluster'] == call.data['cluster']
            and self._attribute['attribute'] == call.data['attribute']
        ):
            _LOGGER.debug("Event received: %s", call.data)
            if self._is_zone_status():
                self._is_on = call.data['value'].get('alarm1', False)
            else:
                self._is_on = call.data['value']
            if not self.hass:
                raise PlatformNotReady
            self.schedule_update_ha_state()

    @property
    def device_class(self):
        return self._device_class

    @property
    def unique_id(self) -> str:
        if self._device.ieee:
            return '{}-{}-{}-{}'.format(self._device.ieee,
                                        self._attribute['endpoint'],
                                        self._attribute['cluster'],
                                        self._attribute['attribute'],
                                        )

    @property
    def should_poll(self):
        """No polling needed for a ZiGate binary sensor."""
        return False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return '{} {}'.format(self._attribute.get('name'),
                              self._device)

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': '0x{:02x}'.format(self._attribute['endpoint']),
            'cluster': '0x{:04x}'.format(self._attribute['cluster']),
            'attribute': '0x{:04x}'.format(self._attribute['attribute'])
        }
        if self._is_zone_status():
            attrs.update(self._attribute.get('value'))
        return attrs

    def _is_zone_status(self):
        '''return True if attribute is a zone status'''
        return 'zone_status' in self._attribute.get('name')
