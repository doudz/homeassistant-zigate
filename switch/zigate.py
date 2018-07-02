"""
ZiGate platform.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/ZiGate/
"""
from homeassistant.components.switch import SwitchDevice
from homeassistant.const import DEVICE_DEFAULT_NAME

DOMAIN = 'zigate'
DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return
    
    z = hass.data[DOMAIN]
    import zigate
    
    def sync_attributes():
        devs = []
        for device in z.devices:
            actions = device.available_actions()
            if not actions:
                continue
            for endpoint, action_type in actions.items():
                if zigate.ACTIONS_ONOFF in action_type:
                    key = '{}-{}-{}'.format(device.addr,
                                               zigate.ACTIONS_ONOFF,
                                               endpoint
                                               )
                    if key not in hass.data[DATA_ZIGATE_ATTRS]:
                        entity = ZiGateSwitch(device, endpoint)
                        devs.append(entity)
                        hass.data[DATA_ZIGATE_ATTRS][key] = entity
    
        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes, zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateSwitch(SwitchDevice):
    """Representation of a ZiGate switch."""

    def __init__(self, device, endpoint):
        """Initialize the ZiGate switch."""
        self._device = device
        self._endpoint = endpoint
        self._name = 'zigate_{}_onoff_{}'.format(device.addr,
                                                 endpoint)
        self._unique_id = '{}-{}-{}'.format(device.addr, 'onoff', endpoint)

    @property
    def unique_id(self)->str:
        return self._unique_id

    @property
    def should_poll(self):
        """No polling needed for a ZiGate switch."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

#     @property
#     def current_power_w(self):
#         """Return the current power usage in W."""
#         if self._state:
#             return 100
# 
#     @property
#     def today_energy_kwh(self):
#         """Return the today total energy usage in kWh."""
#         return 15

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._device.get_property_value('onoff')

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.hass.data[DOMAIN].action_onoff(self._device.addr,
                                            self._endpoint,
                                            1)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.hass.data[DOMAIN].action_onoff(self._device.addr,
                                            self._endpoint,
                                            0)
    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'endpoint': self._endpoint,
        }
