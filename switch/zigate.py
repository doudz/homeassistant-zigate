"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/switch.zigate/
"""
import logging
from homeassistant.components.switch import SwitchDevice, ENTITY_ID_FORMAT
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
                if [zigate.ACTIONS_ONOFF] == action_type:
                    key = '{}-{}-{}'.format(ieee,
                                            'switch',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating switch '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZiGateSwitch(device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateSwitch(SwitchDevice):
    """Representation of a ZiGate switch."""

    def __init__(self, device, endpoint):
        """Initialize the ZiGate switch."""
        self._device = device
        self._endpoint = endpoint
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)

    @property
    def unique_id(self) -> str:
        if self._device.ieee:
            return '{}-{}-{}'.format(self._device.ieee,
                                     'switch',
                                     self._endpoint)

    @property
    def should_poll(self):
        """No polling needed for a ZiGate switch."""
        return self._device.assumed_state

    def update(self):
        self._device.refresh_device()

    @property
    def name(self):
        """Return the name of the device if any."""
        return '{} {}'.format(self._device,
                              self._endpoint)

    @property
    def is_on(self):
        """Return true if switch is on."""
        a = self._device.get_attribute(self._endpoint, 6, 0)
        if a:
            return a.get('value', False)
        return False

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                   self._endpoint,
                                                   1)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                   self._endpoint,
                                                   0)

    def toggle(self, **kwargs):
        """Toggle the device"""
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                   self._endpoint,
                                                   2)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': self._endpoint,
            'battery_voltage': self._device.get_value('battery_voltage'),
            'battery_level': int(self._device.battery_percent),
        }

#     @property
#     def assumed_state(self)->bool:
#         return self._device.assumed_state
