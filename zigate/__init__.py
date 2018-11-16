"""
ZiGate component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/zigate/
"""
import logging
import voluptuous as vol
import os
import datetime

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.event import track_time_change
from homeassistant.const import (ATTR_BATTERY_LEVEL, CONF_PORT,
                                 CONF_HOST,
                                 ATTR_ENTITY_ID,
                                 EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['zigate==0.21.2']
DEPENDENCIES = ['persistent_notification']

DOMAIN = 'zigate'
DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'
ADDR = 'addr'
IEEE = 'ieee'

SUPPORTED_PLATFORMS = ('sensor',
                       'binary_sensor',
                       'switch',
                       'light')

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_PORT): cv.string,
        vol.Optional(CONF_HOST): cv.string
    })
}, extra=vol.ALLOW_EXTRA)


REFRESH_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

IDENTIFY_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

RAW_COMMAND_SCHEMA = vol.Schema({
    vol.Required('cmd'): cv.string,
    vol.Optional('data'): cv.string,
})

REMOVE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

def setup(hass, config):
    """Setup zigate platform."""
    import zigate

    port = config[DOMAIN].get(CONF_PORT)
    host = config[DOMAIN].get(CONF_HOST)
    persistent_file = os.path.join(hass.config.config_dir,
                                   '.zigate.json')

    myzigate = zigate.connect(port=port, host=host,
                              path=persistent_file,
                              auto_start=False
                              )
    
    hass.data[DOMAIN] = myzigate
    hass.data[DATA_ZIGATE_DEVICES] = {}
    hass.data[DATA_ZIGATE_ATTRS] = {}

    component = EntityComponent(_LOGGER, DOMAIN, hass)

    def get_entity_from_addr(addr):
        if addr:
            for d in hass.data[DATA_ZIGATE_DEVICES].values():
                if d.addr == addr:
                    return d

    def device_added(**kwargs):
        device = kwargs['device']
        _LOGGER.debug('Add device {}'.format(device))
        if device.ieee not in hass.data[DATA_ZIGATE_DEVICES]:
            entity = ZiGateDeviceEntity(device)
            hass.data[DATA_ZIGATE_DEVICES][device.ieee] = entity
            component.add_entities([entity])
            if 'signal' in kwargs:
                hass.components.persistent_notification.create(
                    ('A new ZiGate device "{} ({})"'
                     ' has been added !'
                     ).format(device.ieee, device.addr),
                    title='ZiGate')

    def device_removed(**kwargs):
        # component.async_remove_entity
        addr = kwargs[ADDR]
        entity = get_entity_from_addr(addr=addr)
        hass.components.persistent_notification.create(
            'The ZiGate device with address {} has leaved.'.format(addr),
            title='ZiGate')
        del hass.data[DATA_ZIGATE_DEVICES][entity.unique_id]

    def device_need_refresh(**kwargs):
        device = kwargs['device']
        hass.components.persistent_notification.create(
            ('The ZiGate device {} ({}) needs some'
             ' refresh (missing important'
             ' information)').format(device.ieee, device.addr),
            title='ZiGate')

    zigate.dispatcher.connect(device_added,
                              zigate.ZIGATE_DEVICE_ADDED, weak=False)
    zigate.dispatcher.connect(device_removed,
                              zigate.ZIGATE_DEVICE_REMOVED, weak=False)
    zigate.dispatcher.connect(device_need_refresh,
                              zigate.ZIGATE_DEVICE_NEED_REFRESH, weak=False)

    def attribute_updated(**kwargs):
        device = kwargs['device']
        attribute = kwargs['attribute']
        _LOGGER.debug('Update attribute {} for device {}'.format(attribute, device))
        key = '{}-{}-{}-{}'.format(device.ieee,
                                   attribute['endpoint'],
                                   attribute['cluster'],
                                   attribute['attribute'],
                                   )
        entity = hass.data[DATA_ZIGATE_ATTRS].get(key)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
        key = '{}-{}-{}'.format(device.ieee,
                                'switch',
                                attribute['endpoint'],
                                )
        entity = hass.data[DATA_ZIGATE_ATTRS].get(key)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
        key = '{}-{}-{}'.format(device.ieee,
                                'light',
                                attribute['endpoint'],
                                )
        entity = hass.data[DATA_ZIGATE_ATTRS].get(key)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
        entity = hass.data[DATA_ZIGATE_DEVICES].get(device.ieee)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()

        event_data = attribute.copy()
        event_data['ieee'] = device.ieee
        event_data['device_type'] = device.get_property_value('type')
        event_data['entity_id'] = entity.entity_id
        hass.bus.fire('zigate.update_attribute', event_data)

    zigate.dispatcher.connect(attribute_updated,
                              zigate.ZIGATE_ATTRIBUTE_UPDATED, weak=False)

    def device_updated(**kwargs):
        device = kwargs['device']
        _LOGGER.debug('Update device {}'.format(device))
        entity = hass.data[DATA_ZIGATE_DEVICES].get(device.ieee)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
        else:
            _LOGGER.debug('Device not found {}, adding it'.format(device))
            device_added(device=device)

        zigate.dispatcher.connect(device_updated,
                                  zigate.ZIGATE_DEVICE_UPDATED, weak=False)
        zigate.dispatcher.connect(device_updated,
                                  zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)

    def zigate_reset(service):
        myzigate.reset()

    def permit_join(service):
        myzigate.permit_join()

    def zigate_cleanup(service):
        '''
        Remove missing device
        '''
        myzigate.cleanup_devices()

    def start_zigate(service_event=None):
        myzigate.autoStart()
        myzigate.start_auto_save()
        version = myzigate.get_version_text()
        if version < '3.0d':
            hass.components.persistent_notification.create(
                ('Your zigate firmware is outdated, '
                 'Please upgrade to 3.0d or later !'),
                title='ZiGate')
        # first load
        for device in myzigate.devices:
            device_added(device=device)

        for platform in SUPPORTED_PLATFORMS:
            load_platform(hass, platform, DOMAIN, {}, config)

    def stop_zigate(service_event):
        myzigate.save_state()
        myzigate.close()

    def refresh_devices_list(service):
        myzigate.get_devices_list()

    def _get_addr_from_service_request(service):
        entity_id = service.data.get(ATTR_ENTITY_ID)
        if entity_id:
            entity = component.get_entity(entity_id)
            if entity:
                return entity._device.addr
        return service.data.get(ADDR)

    def identify_device(service):
        addr = _get_addr_from_service_request(service)
        myzigate.identify_device(addr)

    def refresh_device(service):
        addr = _get_addr_from_service_request(service)
        if addr:
            myzigate.refresh_device(addr)
        else:
            for device in myzigate.devices:
                device.refresh_device()

    def network_scan(service):
        myzigate.start_network_scan()

    def raw_command(service):
        cmd = int(service.data.get('cmd'), 16)
        data = service.data.get('data', '')
        myzigate.send_data(cmd, data)

    def initiate_touchlink(service):
        myzigate.initiate_touchlink()

    def touchlink_factory_reset(service):
        myzigate.touchlink_factory_reset()

    def remove_device(service):
        addr = _get_addr_from_service_request(service)
        myzigate.remove_device(addr)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_zigate)
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_zigate)

    hass.services.register(DOMAIN, 'refresh_devices_list', refresh_devices_list)
    hass.services.register(DOMAIN, 'reset', zigate_reset)
    hass.services.register(DOMAIN, 'permit_join', permit_join)
    hass.services.register(DOMAIN, 'start_zigate', start_zigate)
    hass.services.register(DOMAIN, 'stop_zigate', stop_zigate)
    hass.services.register(DOMAIN, 'cleanup_devices', zigate_cleanup)
    hass.services.register(DOMAIN, 'identify_device', identify_device,
                           schema=IDENTIFY_SCHEMA)
    hass.services.register(DOMAIN, 'refresh_device',
                           refresh_device,
                           schema=REFRESH_DEVICE_SCHEMA)
    hass.services.register(DOMAIN, 'network_scan', network_scan)
    hass.services.register(DOMAIN, 'raw_command', raw_command,
                           schema=RAW_COMMAND_SCHEMA)
    hass.services.register(DOMAIN, 'initiate_touchlink', initiate_touchlink)
    hass.services.register(DOMAIN, 'touchlink_factory_reset',
                           touchlink_factory_reset)
    hass.services.register(DOMAIN, 'remove_device',
                           remove_device, schema=REMOVE_SCHEMA)

    track_time_change(hass, refresh_devices_list,
                      hour=0, minute=0, second=0)

    return True


class ZiGateDeviceEntity(Entity):
    '''Representation of ZiGate device'''

    def __init__(self, device):
        """Initialize the sensor."""
        self._device = device
        self.entity_id = '{}.{}'.format(DOMAIN, self._device.ieee)

    @property
    def should_poll(self):
        """No polling."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Device {} ({})'.format(self._device.ieee, self._device.addr)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._device.info.get('last_seen')

    @property
    def unique_id(self)->str:
        return self._device.ieee

    @property
    def addr(self):
        return self._device.addr

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        attrs = {'battery_voltage': self._device.get_value('battery'),
                 ATTR_BATTERY_LEVEL: int(self._device.battery_percent),
                 'rssi_percent': int(self._device.rssi_percent),
                 'type': self._device.get_value('type'),
                 'manufacturer': self._device.get_value('manufacturer'),
                 'receiver_on_when_idle': self._device.receiver_on_when_idle(),
                 'missing': self._device.missing
                 }
        attrs.update(self._device.info)
        return attrs

    @property
    def icon(self):
        if self._device.missing:
            return 'mdi:emoticon-dead'
        if self.state:
            last_24h = datetime.datetime.now()-datetime.timedelta(hours=24)
            last_24h = last_24h.strftime('%Y-%m-%d %H:%M:%S')
            if self.state < last_24h:
                return 'mdi:help'
        return 'mdi:access-point'
