"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/sensor.zigate/
"""
import logging
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import (DEVICE_CLASS_HUMIDITY,
                                 DEVICE_CLASS_TEMPERATURE,
                                 DEVICE_CLASS_ILLUMINANCE,
                                 STATE_UNAVAILABLE)
from homeassistant.helpers.entity import Entity
try:
    from homeassistant.components.zigate import DOMAIN as ZIGATE_DOMAIN
    from homeassistant.components.zigate import DATA_ZIGATE_DEVICES
    from homeassistant.components.zigate import DATA_ZIGATE_ATTRS
except:  # temporary until official support
    from custom_components.zigate import DOMAIN as ZIGATE_DOMAIN
    from custom_components.zigate import DATA_ZIGATE_DEVICES
    from custom_components.zigate import DATA_ZIGATE_ATTRS

DEPENDENCIES = ['zigate']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return

    myzigate = hass.data[ZIGATE_DOMAIN]

    def sync_attributes(**kwargs):
        devs = []
        for device in myzigate.devices:
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
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    if type(value) not in (bool, dict):
                        _LOGGER.debug(('Creating sensor '
                                       'for device '
                                       '{} {}').format(device,
                                                       attribute))
                        entity = ZiGateSensor(device, attribute)
                        devs.append(entity)
                        hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)

    sync_attributes()
    import zigate
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateSensor(Entity):
    """Representation of a ZiGate sensor."""

    def __init__(self, device, attribute):
        """Initialize the sensor."""
        self._device = device
        self._attribute = attribute
        self._device_class = None
        name = attribute.get('name')
        entity_id = 'zigate_{}_{}'.format(device.addr,
                                          name)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)

        if 'temperature' in name:
            self._device_class = DEVICE_CLASS_TEMPERATURE
        elif 'humidity' in name:
            self._device_class = DEVICE_CLASS_HUMIDITY
        elif 'luminosity' in name:
            self._device_class = DEVICE_CLASS_ILLUMINANCE

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
        """No polling needed for a ZiGate sensor."""
        return False

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self._attribute.get('name'),
                              self._device)

    @property
    def state(self):
        """Return the state of the sensor."""
        a = self._device.get_attribute(self._attribute['endpoint'],
                                       self._attribute['cluster'],
                                       self._attribute['attribute'])
        if a:
            return a.get('value', STATE_UNAVAILABLE)
        return STATE_UNAVAILABLE

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._attribute.get('unit')

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
