import zigate

from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_BATTERY_LEVEL

from ..const import DOMAIN


class ZiGateComponentEntity(Entity):
    '''Representation of ZiGate Key.'''
    
    def __init__(self, myzigate):
        """Initialize the sensor."""
        self._device = myzigate
        self.entity_id = '{}.{}'.format(DOMAIN, 'zigate')

    @property
    def network_table(self):
        return self._device._neighbours_table_cache

    @property
    def should_poll(self):
        """No polling."""
        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'ZiGate'

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._device.connection:
            if self._device.connection.is_connected():
                return 'connected'
        return 'disconnected'

    @property
    def unique_id(self) -> str:
        return self._device.ieee

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        if not self._device.connection:
            return {}
        attrs = {'addr': self._device.addr,
                 'ieee': self._device.ieee,
                 'groups': self._device.groups,
                 'network_table': self.network_table,
                 'firmware_version': self._device.get_version_text(),
                 'lib version': zigate.__version__
                 }
        return attrs

    @property
    def icon(self):
        return 'mdi:zigbee'


class ZiGateDeviceEntity(Entity):
    '''Representation of ZiGate device.'''

    def __init__(self, hass, device, polling=True):
        """Initialize the sensor."""
        self._polling = polling
        self._device = device
        ieee = device.ieee or device.addr
        self.entity_id = '{}.{}'.format(DOMAIN, ieee)
        hass.bus.listen('zigate.attribute_updated', self._handle_event)
        hass.bus.listen('zigate.device_updated', self._handle_event)

    def _handle_event(self, call):
        if self._device.ieee == call.data['ieee']:
            self.schedule_update_ha_state()

    @property
    def should_poll(self):
        """No polling."""
        return self._polling and self._device.receiver_on_when_idle()

    def update(self):
        self._device.refresh_device()

    @property
    def name(self):
        """Return the name of the sensor."""
        return str(self._device)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._device.info.get('last_seen')

    @property
    def unique_id(self) -> str:
        return self._device.ieee

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        attrs = {'lqi_percent': int(self._device.lqi_percent),
                 'type': self._device.get_value('type'),
                 'manufacturer': self._device.get_value('manufacturer'),
                 'receiver_on_when_idle': self._device.receiver_on_when_idle(),
                 'missing': self._device.missing,
                 'generic_type': self._device.genericType,
                 'discovery': self._device.discovery,
                 'groups': self._device.groups,
                 'datecode': self._device.get_value('datecode')
                 }
        if not self._device.receiver_on_when_idle():
            attrs.update({'battery_voltage': self._device.get_value('battery_voltage'),
                          ATTR_BATTERY_LEVEL: int(self._device.battery_percent),
                          })
        attrs.update(self._device.info)
        return attrs

    @property
    def icon(self):
        if self._device.missing:
            return 'mdi:emoticon-dead'
        if self.state:
            last_24h = datetime.datetime.now() - datetime.timedelta(hours=24)
            last_24h = last_24h.strftime('%Y-%m-%d %H:%M:%S')
            if not self.state or self.state < last_24h:
                return 'mdi:help'
        return 'mdi:access-point'

    @property
    def available(self):
        return not self._device.missing
