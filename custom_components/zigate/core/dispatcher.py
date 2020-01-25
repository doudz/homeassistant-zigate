import logging
import zigate

from homeassistant.helpers.entity import Entity

from ..const import (
    DOMAIN, 
    SUPPORTED_PLATFORMS,
    DATA_ZIGATE_DEVICES,
    DATA_ZIGATE_ATTRS,
    ADDR,
    IEEE
)
from .entities import ZiGateDeviceEntity

_LOGGER = logging.getLogger(__name__)


class ZigateDispatcher:
    """Zigate dispatcher."""

    def __init__(self, hass, config, component):
        """Initialize dispatcher."""

        self.hass = hass
        self.polling = config[DOMAIN].get('polling')
        self.component = component
        
        zigate.dispatcher.connect(self.device_added,
            zigate.ZIGATE_DEVICE_ADDED, weak=False)
        zigate.dispatcher.connect(self.device_removed,
            zigate.ZIGATE_DEVICE_REMOVED, weak=False)
        zigate.dispatcher.connect(self.device_need_discovery,
            zigate.ZIGATE_DEVICE_NEED_DISCOVERY, weak=False)
        zigate.dispatcher.connect(self.attribute_updated,
            zigate.ZIGATE_ATTRIBUTE_UPDATED, weak=False)
        zigate.dispatcher.connect(self.device_updated,
            zigate.ZIGATE_DEVICE_UPDATED, weak=False)
        zigate.dispatcher.connect(self.device_updated,
            zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)
        zigate.dispatcher.connect(self.device_updated,
            zigate.ZIGATE_DEVICE_ADDRESS_CHANGED, weak=False)

    def device_added(self, **kwargs):
        device = kwargs['device']
        _LOGGER.debug('Add device {}'.format(device))
        ieee = device.ieee
        if ieee not in self.hass.data[DATA_ZIGATE_DEVICES]:
            self.hass.data[DATA_ZIGATE_DEVICES][ieee] = None  # reserve
            entity = ZiGateDeviceEntity(self.hass, device, self.polling)
            self.hass.data[DATA_ZIGATE_DEVICES][ieee] = entity
            self.component.add_entities([entity])
            if 'signal' in kwargs:
                self.hass.components.persistent_notification.create(
                    ('A new ZiGate device "{}"'
                     ' has been added !'
                     ).format(device),
                    title='ZiGate')

    def device_removed(self, **kwargs):
        # component.async_remove_entity
        device = kwargs['device']
        ieee = device.ieee
        self.hass.components.persistent_notification.create(
            'The ZiGate device {}({}) is gone.'.format(device.ieee,
                                                       device.addr),
            title='ZiGate')
        entity = self.hass.data[DATA_ZIGATE_DEVICES][ieee]
        self.component.async_remove_entity(entity.entity_id)
        del self.hass.data[DATA_ZIGATE_DEVICES][ieee]

    def device_need_discovery(self, **kwargs):
        device = kwargs['device']
        self.hass.components.persistent_notification.create(
            ('The ZiGate device {}({}) needs to be discovered'
             ' (missing important'
             ' information)').format(device.ieee, device.addr),
            title='ZiGate')

    def attribute_updated(self, **kwargs):
        device = kwargs['device']
        ieee = device.ieee
        attribute = kwargs['attribute']
        _LOGGER.debug('Update attribute for device {} {}'.format(device,
                                                                 attribute))
        entity = self.hass.data[DATA_ZIGATE_DEVICES].get(ieee)
        event_data = attribute.copy()
        if type(event_data.get('type')) == type:
            event_data['type'] = event_data['type'].__name__
        event_data['ieee'] = device.ieee
        event_data['addr'] = device.addr
        event_data['device_type'] = device.get_property_value('type')
        if entity:
            event_data['entity_id'] = entity.entity_id
        self.hass.bus.fire('zigate.attribute_updated', event_data)

    def device_updated(self, **kwargs):
        device = kwargs['device']
        _LOGGER.debug('Update device {}'.format(device))
        ieee = device.ieee
        entity = self.hass.data[DATA_ZIGATE_DEVICES].get(ieee)
        if not entity:
            _LOGGER.debug('Device not found {}, adding it'.format(device))
            self.device_added(device=device)
        event_data = {}
        event_data['ieee'] = device.ieee
        event_data['addr'] = device.addr
        event_data['device_type'] = device.get_property_value('type')
        if entity:
            event_data['entity_id'] = entity.entity_id
        self.hass.bus.fire('zigate.device_updated', event_data)
