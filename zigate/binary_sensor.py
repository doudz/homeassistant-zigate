"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/binary_sensor.zigate/
"""
import logging
from homeassistant.components.binary_sensor import (BinarySensorDevice,
                                                    ENTITY_ID_FORMAT)
from homeassistant.const import STATE_UNAVAILABLE, STATE_ON, STATE_OFF
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
                        entity = ZiGateBinarySensor(device, attribute)
                        devs.append(entity)
                        hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    import zigate
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateBinarySensor(BinarySensorDevice):
    """representation of a ZiGate binary sensor."""

    def __init__(self, device, attribute):
        """Initialize the sensor."""
        self._device = device
        self._attribute = attribute
        self._device_class = None
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
        a = self._device.get_attribute(self._attribute['endpoint'],
                                       self._attribute['cluster'],
                                       self._attribute['attribute'])
        if a:
            value = a.get('value')
            if self._is_zone_status():
                return value.get('alarm1')
            return value

    @property
    def state(self):
        if self.is_on is None:
            return STATE_UNAVAILABLE
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': self._attribute['endpoint'],
            'cluster': self._attribute['cluster'],
            'attribute': self._attribute['attribute'],
            'battery_voltage': self._device.get_value('battery_voltage'),
            'battery_level': int(self._device.battery_percent),
        }
        if self._is_zone_status():
            attrs.update(self._attribute.get('value'))
        return attrs

    def _is_zone_status(self):
        '''return True if attribute is a zone status'''
        return 'zone_status' in self._attribute.get('name')
