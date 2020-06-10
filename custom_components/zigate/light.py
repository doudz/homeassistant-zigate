"""
ZiGate light platform that implements lights.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/light.zigate/
"""
import logging
from functools import reduce
from operator import ior

from homeassistant.exceptions import PlatformNotReady
import homeassistant.util.color as color_util
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_TRANSITION, ATTR_HS_COLOR,
    SUPPORT_BRIGHTNESS, SUPPORT_COLOR_TEMP,
    SUPPORT_TRANSITION, ATTR_COLOR_TEMP,
    SUPPORT_COLOR, LightEntity, ENTITY_ID_FORMAT)
import zigate
from . import DOMAIN as ZIGATE_DOMAIN
from . import DATA_ZIGATE_ATTRS


_LOGGER = logging.getLogger(__name__)

SUPPORT_HUE_COLOR = 64


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate sensors."""
    if discovery_info is None:
        return

    myzigate = hass.data[ZIGATE_DOMAIN]
    LIGHT_ACTIONS = [zigate.ACTIONS_LEVEL,
                     zigate.ACTIONS_COLOR,
                     zigate.ACTIONS_TEMPERATURE,
                     zigate.ACTIONS_HUE,
                     ]

    def sync_attributes():
        devs = []
        for device in myzigate.devices:
            ieee = device.ieee or device.addr  # compatibility
            actions = device.available_actions()
            if not any(actions.values()):
                continue
            for endpoint, action_type in actions.items():
                if any(i in action_type for i in LIGHT_ACTIONS):
                    key = '{}-{}-{}'.format(ieee,
                                            'light',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating light '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZiGateLight(hass, device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateLight(LightEntity):
    """Representation of a ZiGate light."""

    def __init__(self, hass, device, endpoint):
        """Initialize the light."""
        self._device = device
        self._endpoint = endpoint
        self._is_on = False
        self._brightness = 0
        a = self._device.get_attribute(endpoint, 6, 0)
        if a:
            self._is_on = a.get('value', False)
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
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
                supported_features.add(SUPPORT_HUE_COLOR)
        self._supported_features = reduce(ior, supported_features)
        hass.bus.listen('zigate.attribute_updated', self._handle_event)

    def _handle_event(self, call):
        if (
            self._device.ieee == call.data['ieee']
            and self._endpoint == call.data['endpoint']
        ):
            _LOGGER.debug("Event received: %s", call.data)
            if call.data['cluster'] == 6 and call.data['attribute'] == 0:
                self._is_on = call.data['value']
            if call.data['cluster'] == 8 and call.data['attribute'] in (0, 17):
                self._brightness = int(call.data['value'] * 255 / 100)
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
        return self._brightness

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
        return self._is_on

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self._is_on = True
        self.schedule_update_ha_state()
        transition = 1
        if ATTR_TRANSITION in kwargs:
            transition = int(kwargs[ATTR_TRANSITION])
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            self._brightness = brightness
            brightness = round((brightness / 255) * 100) or 1
            self.hass.data[ZIGATE_DOMAIN].action_move_level_onoff(self._device.addr,
                                                                  self._endpoint,
                                                                  1,
                                                                  brightness,
                                                                  transition
                                                                  )
        else:
            self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                       self._endpoint,
                                                       1)
        if ATTR_HS_COLOR in kwargs:
            h, s = kwargs[ATTR_HS_COLOR]
            if self.supported_features & SUPPORT_COLOR:
                x, y = color_util.color_hs_to_xy(h, s)
                self.hass.data[ZIGATE_DOMAIN].action_move_colour(self._device.addr,
                                                                 self._endpoint,
                                                                 x,
                                                                 y,
                                                                 transition)
            elif self.supported_features & SUPPORT_HUE_COLOR:
                self.hass.data[ZIGATE_DOMAIN].action_move_hue_saturation(self._device.addr,
                                                                         self._endpoint,
                                                                         int(h),
                                                                         int(s),
                                                                         transition)
        elif ATTR_COLOR_TEMP in kwargs:
            temp = kwargs[ATTR_COLOR_TEMP]
            self.hass.data[ZIGATE_DOMAIN].action_move_temperature(self._device.addr,
                                                                  self._endpoint,
                                                                  int(temp),
                                                                  transition)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._is_on = False
        self.schedule_update_ha_state()
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                   self._endpoint,
                                                   0)

    def toggle(self, **kwargs):
        """Toggle the device"""
        self._is_on = not self._is_on
        self.schedule_update_ha_state()
        self.hass.data[ZIGATE_DOMAIN].action_onoff(self._device.addr,
                                                   self._endpoint,
                                                   2)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': '0x{:02x}'.format(self._endpoint),
        }
