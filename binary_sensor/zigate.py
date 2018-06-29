"""
ZiGate platform that has two fake binary sensors.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/ZiGate/
"""
from homeassistant.components.binary_sensor import BinarySensorDevice


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate binary sensor platform."""
    add_devices([
        ZiGateBinarySensor('Basement Floor Wet', False, 'moisture'),
        ZiGateBinarySensor('Movement Backyard', True, 'motion'),
    ])


class ZiGateBinarySensor(BinarySensorDevice):
    """representation of a ZiGate binary sensor."""

    def __init__(self, name, state, device_class):
        """Initialize the ZiGate sensor."""
        self._name = name
        self._state = state
        self._sensor_type = device_class

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._sensor_type

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
        return self._state
