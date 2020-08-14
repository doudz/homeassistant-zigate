"""
ZiGate lock platform that implements locks.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/lock.zigate/
"""
import logging
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.lock import LockEntity, ENTITY_ID_FORMAT
import zigate
from . import DOMAIN as ZIGATE_DOMAIN
from . import DATA_ZIGATE_ATTRS

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the ZiGate locks."""
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
                if [zigate.ACTIONS_LOCK] == action_type:
                    key = '{}-{}-{}'.format(ieee,
                                            'lock',
                                            endpoint
                                            )
                    if key in hass.data[DATA_ZIGATE_ATTRS]:
                        continue
                    _LOGGER.debug(('Creating lock '
                                   'for device '
                                   '{} {}').format(device,
                                                   endpoint))
                    entity = ZiGateLock(hass, device, endpoint)
                    devs.append(entity)
                    hass.data[DATA_ZIGATE_ATTRS][key] = entity

        add_devices(devs)
    sync_attributes()
    zigate.dispatcher.connect(sync_attributes,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)


class ZiGateLock(LockEntity):
    """Representation of a ZiGate lock."""

    def __init__(self, hass, device, endpoint):
        """Initialize the ZiGate lock."""
        self._device = device
        self._endpoint = endpoint
        self._is_locked = 2
        a = self._device.get_attribute(endpoint, 0x0101, 0)
        if a:
            self._lock_state = a.get('value', 2)
        ieee = device.ieee or device.addr  # compatibility
        entity_id = 'zigate_{}_{}'.format(ieee,
                                          endpoint)
        self.entity_id = ENTITY_ID_FORMAT.format(entity_id)
        hass.bus.listen('zigate.attribute_updated', self._handle_event)

    def _handle_event(self, call):
        if (
            self._device.ieee == call.data['ieee']
            and self._endpoint == call.data['endpoint']
        ):
            _LOGGER.debug("Event received: %s", call.data)
            if call.data['cluster'] == 0x0101 and call.data['attribute'] == 0:
                self._lock_state = call.data['value']
            if not self.hass:
                raise PlatformNotReady
            self.schedule_update_ha_state()

    @property
    def unique_id(self) -> str:
        if self._device.ieee:
            return '{}-{}-{}'.format(self._device.ieee,
                                     'lock',
                                     self._endpoint)

    @property
    def should_poll(self):
        """No polling needed for a ZiGate lock."""
        return False

    def update(self):
        self._device.refresh_device()

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._lock_state == 1

    def lock(self, **kwargs):
        """Lock the device."""
        self._lock_state = 1
        self.schedule_update_ha_state()
        self.hass.data[ZIGATE_DOMAIN].action_lock(self._device.addr,
                                                  self._endpoint,
                                                  0)

    def unlock(self, **kwargs):
        """Unlock the device."""
        self._lock_state = 2
        self.schedule_update_ha_state()
        self.hass.data[ZIGATE_DOMAIN].action_lock(self._device.addr,
                                                  self._endpoint,
                                                  1)
