"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/ZiGate/
"""
import logging
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.const import STATE_UNAVAILABLE, STATE_ON, STATE_OFF

DOMAIN = 'zigate'
DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return

    z = hass.data[DOMAIN]

    def sync_attributes():
        devs = []
        for device in z.devices:
            actions = device.available_actions()
            if any(actions.values()):
                continue
            for attribute in device.attributes:
                if attribute['cluster'] == 0:
                    continue
                if 'name' in attribute:
                    key = '{}-{}-{}-{}'.format(device.addr,
                                               attribute['endpoint'],
                                               attribute['cluster'],
                                               attribute['attribute'],
                                               )
                    value = attribute.get('value')
                    if value is None:
                        continue
                    if key not in hass.data[DATA_ZIGATE_ATTRS]:
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
        self._name = 'zigate_{}_{}'.format(device.addr,
                                           name)
        self.registry_name = '{} {}'.format(name, device)

        typ = self._device.get_value('type', '').lower()
        if name == 'presence':
            self._device_class = 'motion'
        elif 'magnet' in typ:
            self._device_class = 'door'
        elif 'smok' in typ:
            self._device_class = 'smoke'
        elif 'leak' in typ:
            self._device_class = 'safety'

    @property
    def device_class(self):
        return self._device_class

    @property
    def unique_id(self)->str:
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
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        a = self._device.get_attribute(self._attribute['endpoint'],
                                       self._attribute['cluster'],
                                       self._attribute['attribute'])
        if a:
            value = a.get('value')
            if isinstance(value, dict):
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
            'endpoint': self._attribute['endpoint'],
            'cluster': self._attribute['cluster'],
            'attribute': self._attribute['attribute'],
            'battery_voltage': self._device.get_value('battery'),
            'battery_level': int(self._device.battery_percent),
        }
        state = self.state
        if isinstance(self.state, dict):
            attrs.update(state)
        return attrs
