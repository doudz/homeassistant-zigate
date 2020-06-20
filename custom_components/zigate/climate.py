"""
ZiGate climate platform that implements climates.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.zigate/
"""
import logging

from homeassistant.exceptions import PlatformNotReady
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.components.climate import ClimateEntity, ENTITY_ID_FORMAT
from homeassistant.components.climate.const import SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE, HVAC_MODE_HEAT
import zigate
from . import DOMAIN as ZIGATE_DOMAIN
from . import DATA_ZIGATE_ATTRS
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the zigate climate devices."""
    if discovery_info is None:
        return

    myzigate = hass.data[ZIGATE_DOMAIN]

    def sync_attributes():
        devs = []
        for device in myzigate.devices:
            ieee = device.ieee or device.addr  # compatibility
            actions = device.available_actions()
            if not any(actions.values()):
                continue
            for endpoint, action_type in actions.items():
                if [zigate.ACTIONS_THERMOSTAT] == action_type:
                    key = '{}-{}-{}'.format(ieee,
                                            'climate',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating climate '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZigateClimate(hass, device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_entities(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZigateClimate(ClimateEntity):
    """Representation of a Zigate climate device."""

    def __init__(self, hass, device, endpoint):
        """Initialize the ZiGate climate."""
        self._device = device
        self._endpoint = endpoint
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)
        hass.bus.listen('zigate.attribute_updated', self._handle_event)

        self._support_flags = SUPPORT_FLAGS
        self._hvac_mode = HVAC_MODE_HEAT

    def _handle_event(self, call):
        if (
            self._device.ieee == call.data['ieee']
            and self._endpoint == call.data['endpoint']
        ):
            _LOGGER.debug("Event received: %s", call.data)
            if not self.hass:
                raise PlatformNotReady
            self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        if self._device.ieee:
            return '{}-{}-{}'.format(self._device.ieee,
                                     'climate',
                                     self._endpoint)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    @property
    def should_poll(self) -> bool:
        return False

    def update(self):
        self._device.refresh_device()

    @property
    def name(self):
        """Return the name of the device if any."""
        return '{} {}'.format(self._device,
                              self._endpoint)

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        t = 0
        a = self._device.get_attribute(self._endpoint, 0x0201, 0x0000)
        if a:
            t = a.get('value', 0)
        return t

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        if self.preset_mode == 'away':
            attr = 0x0014
        else:
            attr = 0x0012
        t = 0
        a = self._device.get_attribute(self._endpoint, 0x0201, attr)
        if a:
            t = a.get('value', 0)
        return t

    @property
    def hvac_mode(self):
        return self._hvac_mode

    @property
    def hvac_modes(self):
        return [HVAC_MODE_HEAT]

    def set_hvac_mode(self, hvac_mode):
        self._hvac_mode = hvac_mode

    @property
    def preset_modes(self):
        return ['home', 'away']

    @property
    def preset_mode(self):
        t = 1
        a = self._device.get_attribute(self._endpoint, 0x0201, 0x0002)
        if a:
            t = a.get('value', t)
        if t == 0:
            return 'away'
        return 'home'

    def set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        if preset_mode == 'away':
            self.hass.data[ZIGATE_DOMAIN].write_attribute_request(self._device.addr,
                                                                  self._endpoint,
                                                                  0x0201,
                                                                  [(0x0002, 0x18, 0)])
        else:
            self.hass.data[ZIGATE_DOMAIN].write_attribute_request(self._device.addr,
                                                                  self._endpoint,
                                                                  0x0201,
                                                                  [(0x0002, 0x18, 1)])

    def set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            temp = int(kwargs.get(ATTR_TEMPERATURE) * 100)
            if self.preset_mode == 'away':
                attr = 0x0014
            else:
                attr = 0x0012
            self.hass.data[ZIGATE_DOMAIN].write_attribute_request(self._device.addr,
                                                                  self._endpoint,
                                                                  0x0201,
                                                                  [(attr, 0x29, temp)])
        self.schedule_update_ha_state()

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            'addr': self._device.addr,
            'ieee': self._device.ieee,
            'endpoint': '0x{:02x}'.format(self._endpoint),
        }
