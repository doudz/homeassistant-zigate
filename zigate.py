'''
Created on 3 févr. 2018

@author: doudz
'''
import logging
import voluptuous as vol

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import (ATTR_BATTERY_LEVEL, CONF_PORT,
                                 EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP) 
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['zigate==0.16.4']

DOMAIN = 'zigate'
DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_PORT): cv.string,
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Setup zigate platform."""
    import zigate

    port = config.get(CONF_PORT)
    z = zigate.ZiGate(port, auto_start=False)
    hass.data[DOMAIN] = z
    hass.data[DATA_ZIGATE_DEVICES] = {}
    hass.data[DATA_ZIGATE_ATTRS] = {}
    
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    def device_added(**kwargs):
        device = kwargs['device']
        if device.addr not in hass.data[DATA_ZIGATE_DEVICES]:
            entity = ZiGateDeviceEntity(device)
            hass.data[DATA_ZIGATE_DEVICES][device.addr] = entity
            component.add_entities([entity])
            
    def device_removed(**kwargs):
        # component.async_remove_entity
        pass

    zigate.dispatcher.connect(device_added, zigate.ZIGATE_DEVICE_ADDED, weak=False)
    zigate.dispatcher.connect(device_removed, zigate.ZIGATE_DEVICE_REMOVED, weak=False)
    
    def attribute_updated(**kwargs):
        device = kwargs['device']
        attribute = kwargs['attribute']
        key = '{}-{}-{}-{}'.format(device.addr,
                                   attribute['endpoint'],
                                   attribute['cluster'],
                                   attribute['attribute'],
                                   )
        entity = hass.data[DATA_ZIGATE_ATTRS].get(key)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
        entity = hass.data[DATA_ZIGATE_DEVICES].get(device.addr)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
    
    zigate.dispatcher.connect(attribute_updated, zigate.ZIGATE_ATTRIBUTE_UPDATED, weak=False)
    
    def device_updated(**kwargs):
        device = kwargs['device']
        entity = hass.data[DATA_ZIGATE_DEVICES].get(device.addr)
        if entity:
            if entity.hass:
                entity.schedule_update_ha_state()
                
        zigate.dispatcher.connect(device_updated, zigate.ZIGATE_DEVICE_UPDATED, weak=False)
        zigate.dispatcher.connect(device_updated, zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)
    
    def zigate_reset(service):
        z.reset()

    def permit_join(service):
        z.permit_join()

    def start_zigate(service_event):
        z.autoStart()
        z.start_auto_save()
        # firt load
        for device in z.devices:
            device_added(device=device)
            
        load_platform(hass, 'sensor', DOMAIN, {}, config)
        load_platform(hass, 'binary_sensor', DOMAIN, {}, config)

    def stop_zigate(service_event):
        z.save_state()
        z.close()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_zigate)
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_zigate)
    
    hass.services.register(DOMAIN, 'reset', zigate_reset)
    hass.services.register(DOMAIN, 'permit_join', permit_join)
    hass.services.register(DOMAIN, 'start_zigate', start_zigate)
    hass.services.register(DOMAIN, 'stop_zigate', stop_zigate)

    return True


class ZiGateDeviceEntity(Entity):
    '''Representation of ZiGate device'''

    def __init__(self, device):
        """Initialize the sensor."""
        self._device = device
        self.registry_name = str(device)
        self._name = self._device.addr
        
    @property
    def should_poll(self):
        """No polling."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._device.info.get('last_seen')

    @property
    def unique_id(self)->str:
        return self._device.ieee

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        attrs = {'battery': self._device.get_property_value('battery'),
                 ATTR_BATTERY_LEVEL: int(self._device.battery_percent),
                 'rssi_percent': int(self._device.rssi_percent),
                 'type': self._device.get_property_value('type'),
                 'manufacturer': self._device.get_property_value('manufacturer'),
                 'receiver_on_when_idle': self._device.receiver_on_when_idle()
                 }
        attrs.update(self._device.info)
        return attrs
    
    @property
    def icon(self):
        return 'mdi:access-point'
