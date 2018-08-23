"""
ZiGate light platform that implements lights.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/light.zigate/
"""
import logging
from functools import reduce
from operator import ior

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_TRANSITION, ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS, SUPPORT_COLOR_TEMP,
    SUPPORT_TRANSITION,
    SUPPORT_COLOR, Light, ENTITY_ID_FORMAT)
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
    import zigate
    LIGHT_ACTIONS = [zigate.ACTIONS_LEVEL,
                     zigate.ACTIONS_COLOR,
                     zigate.ACTIONS_TEMPERATURE,
                     zigate.ACTIONS_HUE,
                     ]

    def sync_attributes():
        devs = []
        for device in myzigate.devices:
            actions = device.available_actions()
            if not any(actions.values()):
                continue
            for endpoint, action_type in actions.items():
                if any(i in action_type for i in LIGHT_ACTIONS):
                    key = '{}-{}-{}'.format(device.addr,
                                            'light',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating light '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZiGateLight(device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateLight(Light):
    """Representation of a ZiGate light."""

    def __init__(self, device, endpoint):
        """Initialize the light."""
        self._device = device
        self._endpoint = endpoint
        entity_id = 'zigate_{}_{}'.format(device.addr,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)

        import zigate
        supported_features = set()
        supported_features.add(SUPPORT_TRANSITION)
        for action_type in device.available_actions(endpoint)[endpoint]:
            if action_type == zigate.ACTIONS_LEVEL:
                supported_features.add(SUPPORT_BRIGHTNESS)
            elif action_type == zigate.ACTIONS_COLOR:
                supported_features.add(SUPPORT_COLOR)
            elif action_type == zigate.ACTIONS_TEMPERATURE:
                supported_features.add(SUPPORT_COLOR_TEMP)
            elif action_type == zigate.ACTIONS_HUE:
                supported_features.add(SUPPORT_COLOR)
        self._supported_features = reduce(ior, supported_features)

    @property
    def should_poll(self) -> bool:
        """No polling needed for a ZiGate light."""
        return False

    @property
    def name(self) -> str:
        """Return the name of the light if any."""
        return '{} {}'.format(self._device,
                              self._endpoint)

    @property
    def unique_id(self):
        """Return unique ID for light."""
        if self._device.ieee:
            return '{}-{}-{}'.format(self._device.ieee,
                                     'light',
                                     self._endpoint)

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        a = self._device.get_attribute(self._endpoint, 8, 0)
        if a:
            return int(a.get('value', 0)*255/100)
        return 0

    @property
    def hs_color(self) -> tuple:
        """Return the hs color value."""
        h = 0
        a = self._device.get_attribute(self._endpoint, 0x0300, 0x0000)
        if a:
            h = a.get('value', 0)
        s = 0
        a = self._device.get_attribute(self._endpoint, 0x0300, 0x0001)
        if a:
            s = a.get('value', 0)
        return (h, s)

    @property
    def color_temp(self) -> int:
        """Return the CT color temperature."""
        a = self._device.get_attribute(self._endpoint, 0x0300, 0x0007)
        if a:
            return a.get('value')

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        a = self._device.get_attribute(self._endpoint, 6, 0)
        if a:
            return a.get('value', False)
        return False

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        transition = 0
        if ATTR_TRANSITION in kwargs:
            transition = int(kwargs[ATTR_TRANSITION])
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            brightness = int((brightness / 255) * 100)
            self.hass.data[ZIGATE_DOMAIN].action_move_level_onoff(self._device.addr,
                                                           self._endpoint,
                                                           1,
                                                           brightness,
                                                           transition
                                                           )
        else:
            self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                self._endpoint,
                                                1,
                                                transition)
        if ATTR_HS_COLOR in kwargs:
            h, s = kwargs[ATTR_HS_COLOR]
            self.hass.data[ZIGATE_DOMAIN].actions_move_hue_saturation(self._device.addr,
                                                               self._endpoint,
                                                               int(h),
                                                               int(s),
                                                               transition)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        transition = 0
        if ATTR_TRANSITION in kwargs:
            transition = int(kwargs[ATTR_TRANSITION])
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                            self._endpoint,
                                            0,
                                            off_time=transition)

    def toggle(self, **kwargs):
        """Toggle the device"""
        transition = 0
        if ATTR_TRANSITION in kwargs:
            transition = int(kwargs[ATTR_TRANSITION])
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                            self._endpoint,
                                            2,
                                            transition,
                                            transition)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'endpoint': self._endpoint,
        }
