"""
ZiGate component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/zigate/
"""
import logging
import voluptuous as vol
import os
import datetime
import zigate

from homeassistant.exceptions import PlatformNotReady
# from homeassistant import config_entries
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.group import \
    ENTITY_ID_FORMAT as GROUP_ENTITY_ID_FORMAT
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.event import track_time_change
from homeassistant.const import (ATTR_BATTERY_LEVEL, CONF_PORT,
                                 CONF_HOST, CONF_SCAN_INTERVAL,
                                 ATTR_ENTITY_ID,
                                 EVENT_HOMEASSISTANT_START,
                                 EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, SCAN_INTERVAL
from .adminpanel import adminpanel_setup


_LOGGER = logging.getLogger(__name__)

DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'
ADDR = 'addr'
IEEE = 'ieee'

ENTITY_ID_ALL_ZIGATE = GROUP_ENTITY_ID_FORMAT.format('all_zigate')

SUPPORTED_PLATFORMS = ('sensor',
                       'binary_sensor',
                       'switch',
                       'light',
                       'cover',
                       'climate',
                       'lock')

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_PORT): cv.string,
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional('channel'): cv.positive_int,
        vol.Optional('gpio'): cv.boolean,
        vol.Optional('enable_led'): cv.boolean,
        vol.Optional('polling'): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL): cv.positive_int,
        vol.Optional('admin_panel'): cv.boolean,
    })
}, extra=vol.ALLOW_EXTRA)


REFRESH_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional('full'): cv.boolean,
})

DISCOVER_DEVICE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

RAW_COMMAND_SCHEMA = vol.Schema({
    vol.Required('cmd'): cv.string,
    vol.Optional('data'): cv.string,
})

IDENTIFY_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

REMOVE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
})

READ_ATTRIBUTE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('cluster'): cv.string,
    vol.Required('attribute_id'): cv.string,
    vol.Optional('manufacturer_code'): cv.string,
})

WRITE_ATTRIBUTE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('cluster'): cv.string,
    vol.Required('attribute_id'): cv.string,
    vol.Required('attribute_type'): cv.string,
    vol.Required('value'): cv.string,
    vol.Optional('manufacturer_code'): cv.string,
})

ADD_GROUP_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Optional('group_addr'): cv.string,
})

REMOVE_GROUP_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Optional('group_addr'): cv.string,
})

GET_GROUP_MEMBERSHIP_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
})

ACTION_ONOFF_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('onoff'): cv.string,
    vol.Optional('endpoint'): cv.string,
    vol.Optional('on_time'): cv.string,
    vol.Optional('off_time'): cv.string,
    vol.Optional('effect'): cv.string,
    vol.Optional('gradient'): cv.string,
})

OTA_LOAD_IMAGE_SCHEMA = vol.Schema({
    vol.Required('imagepath'): cv.string,
})

OTA_IMAGE_NOTIFY_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Optional('destination_enpoint'): cv.string,
    vol.Optional('payload_type'): cv.string,
})

VIEW_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
    vol.Required('scene'): cv.string,
})

ADD_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
    vol.Required('scene'): cv.string,
    vol.Required('name'): cv.string,
    vol.Optional('transition'): cv.string,
})

REMOVE_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
    vol.Optional('scene'): cv.string,
})

STORE_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
    vol.Required('scene'): cv.string,
})

RECALL_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
    vol.Required('scene'): cv.string,
})

SCENE_MEMBERSHIP_REQUEST_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('group_addr'): cv.string,
})

COPY_SCENE_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Required('from_group_addr'): cv.string,
    vol.Required('from_scene'): cv.string,
    vol.Required('to_group_addr'): cv.string,
    vol.Required('to_scene'): cv.string,
})

BUILD_NETWORK_TABLE_SCHEMA = vol.Schema({
    vol.Optional('force'): cv.boolean,
    })

ACTION_IAS_WARNING_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Optional('mode'): cv.string,
    vol.Optional('strobe'): cv.boolean,
    vol.Optional('level'): cv.string,
    vol.Optional('duration'): cv.positive_int,
    vol.Optional('strobe_cycle'): cv.positive_int,
    vol.Optional('strobe_level'): cv.string,
})

ACTION_IAS_SQUAWK_SCHEMA = vol.Schema({
    vol.Optional(ADDR): cv.string,
    vol.Optional(IEEE): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required('endpoint'): cv.string,
    vol.Optional('mode'): cv.string,
    vol.Optional('strobe'): cv.boolean,
    vol.Optional('level'): cv.string,
})


def setup(hass, config):
    """Setup zigate platform."""
    port = config[DOMAIN].get(CONF_PORT)
    host = config[DOMAIN].get(CONF_HOST)
    gpio = config[DOMAIN].get('gpio', False)
    enable_led = config[DOMAIN].get('enable_led', True)
    polling = config[DOMAIN].get('polling', True)
    channel = config[DOMAIN].get('channel')
    scan_interval = datetime.timedelta(seconds=config[DOMAIN].get(CONF_SCAN_INTERVAL, SCAN_INTERVAL))
    admin_panel = config[DOMAIN].get('admin_panel', True)

    persistent_file = os.path.join(hass.config.config_dir,
                                   'zigate.json')

    _LOGGER.debug('Port : %s', port)
    _LOGGER.debug('Host : %s', host)
    _LOGGER.debug('GPIO : %s', gpio)
    _LOGGER.debug('Led : %s', enable_led)
    _LOGGER.debug('Channel : %s', channel)
    _LOGGER.debug('Scan interval : %s', scan_interval)

    myzigate = zigate.connect(port=port, host=host,
                              path=persistent_file,
                              auto_start=False,
                              gpio=gpio
                              )
    _LOGGER.debug('ZiGate object created %s', myzigate)

    hass.data[DOMAIN] = myzigate
    hass.data[DATA_ZIGATE_DEVICES] = {}
    hass.data[DATA_ZIGATE_ATTRS] = {}

    component = EntityComponent(_LOGGER, DOMAIN, hass, scan_interval)
#     component.setup(config)
    entity = ZiGateComponentEntity(myzigate)
    hass.data[DATA_ZIGATE_DEVICES]['zigate'] = entity
    component.add_entities([entity])

    def device_added(**kwargs):
        device = kwargs['device']
        _LOGGER.debug('Add device {}'.format(device))
        ieee = device.ieee
        if ieee not in hass.data[DATA_ZIGATE_DEVICES]:
            hass.data[DATA_ZIGATE_DEVICES][ieee] = None  # reserve
            entity = ZiGateDeviceEntity(hass, device, polling)
            hass.data[DATA_ZIGATE_DEVICES][ieee] = entity
            component.add_entities([entity])
            if 'signal' in kwargs:
                hass.components.persistent_notification.create(
                    ('A new ZiGate device "{}"'
                     ' has been added !'
                     ).format(device),
                    title='ZiGate')

    def device_removed(**kwargs):
        # component.async_remove_entity
        device = kwargs['device']
        ieee = device.ieee
        hass.components.persistent_notification.create(
            'The ZiGate device {}({}) is gone.'.format(device.ieee,
                                                       device.addr),
            title='ZiGate')
        entity = hass.data[DATA_ZIGATE_DEVICES][ieee]
        component.async_remove_entity(entity.entity_id)
        del hass.data[DATA_ZIGATE_DEVICES][ieee]

    def device_need_discovery(**kwargs):
        device = kwargs['device']
        hass.components.persistent_notification.create(
            ('The ZiGate device {}({}) needs to be discovered'
             ' (missing important'
             ' information)').format(device.ieee, device.addr),
            title='ZiGate')

    zigate.dispatcher.connect(device_added,
                              zigate.ZIGATE_DEVICE_ADDED, weak=False)
    zigate.dispatcher.connect(device_removed,
                              zigate.ZIGATE_DEVICE_REMOVED, weak=False)
    zigate.dispatcher.connect(device_need_discovery,
                              zigate.ZIGATE_DEVICE_NEED_DISCOVERY, weak=False)

    def attribute_updated(**kwargs):
        device = kwargs['device']
        ieee = device.ieee
        attribute = kwargs['attribute']
        _LOGGER.debug('Update attribute for device {} {}'.format(device,
                                                                 attribute))
        entity = hass.data[DATA_ZIGATE_DEVICES].get(ieee)
        event_data = attribute.copy()
        if type(event_data.get('type')) == type:
            event_data['type'] = event_data['type'].__name__
        event_data['ieee'] = device.ieee
        event_data['addr'] = device.addr
        event_data['device_type'] = device.get_property_value('type')
        if entity:
            event_data['entity_id'] = entity.entity_id
        hass.bus.fire('zigate.attribute_updated', event_data)

    zigate.dispatcher.connect(attribute_updated,
                              zigate.ZIGATE_ATTRIBUTE_UPDATED, weak=False)

    def device_updated(**kwargs):
        device = kwargs['device']
        _LOGGER.debug('Update device {}'.format(device))
        ieee = device.ieee
        entity = hass.data[DATA_ZIGATE_DEVICES].get(ieee)
        if not entity:
            _LOGGER.debug('Device not found {}, adding it'.format(device))
            device_added(device=device)
        event_data = {}
        event_data['ieee'] = device.ieee
        event_data['addr'] = device.addr
        event_data['device_type'] = device.get_property_value('type')
        if entity:
            event_data['entity_id'] = entity.entity_id
        hass.bus.fire('zigate.device_updated', event_data)

    zigate.dispatcher.connect(device_updated,
                              zigate.ZIGATE_DEVICE_UPDATED, weak=False)
    zigate.dispatcher.connect(device_updated,
                              zigate.ZIGATE_ATTRIBUTE_ADDED, weak=False)
    zigate.dispatcher.connect(device_updated,
                              zigate.ZIGATE_DEVICE_ADDRESS_CHANGED, weak=False)

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
        myzigate.autoStart(channel)
        myzigate.start_auto_save()
        myzigate.set_led(enable_led)
        version = myzigate.get_version_text()
        if version < '3.1a':
            hass.components.persistent_notification.create(
                ('Your zigate firmware is outdated, '
                 'Please upgrade to 3.1a or later !'),
                title='ZiGate')
        # first load
        for device in myzigate.devices:
            device_added(device=device)

        for platform in SUPPORTED_PLATFORMS:
            load_platform(hass, platform, DOMAIN, {}, config)

        hass.bus.fire('zigate.started')

    def stop_zigate(service=None):
        myzigate.save_state()
        myzigate.close()

        hass.bus.fire('zigate.stopped')

    def refresh_devices_list(service):
        myzigate.get_devices_list()

    def generate_templates(service):
        myzigate.generate_templates(hass.config.config_dir)

    def _get_addr_from_service_request(service):
        entity_id = service.data.get(ATTR_ENTITY_ID)
        ieee = service.data.get(IEEE)
        addr = service.data.get(ADDR)
        if entity_id:
            entity = component.get_entity(entity_id)
            if entity:
                addr = entity._device.addr
        elif ieee:
            device = myzigate.get_device_from_ieee(ieee)
            if device:
                addr = device.addr
        return addr

    def _to_int(value):
        '''
        convert str to int
        '''
        if 'x' in value:
            return int(value, 16)
        return int(value)

    def refresh_device(service):
        full = service.data.get('full', False)
        addr = _get_addr_from_service_request(service)
        if addr:
            myzigate.refresh_device(addr, full=full)
        else:
            for device in myzigate.devices:
                device.refresh_device(full=full)

    def discover_device(service):
        addr = _get_addr_from_service_request(service)
        if addr:
            myzigate.discover_device(addr, True)

    def network_scan(service):
        myzigate.start_network_scan()

    def raw_command(service):
        cmd = _to_int(service.data.get('cmd'))
        data = service.data.get('data', '')
        myzigate.send_data(cmd, data)

    def identify_device(service):
        addr = _get_addr_from_service_request(service)
        myzigate.identify_device(addr)

    def remove_device(service):
        addr = _get_addr_from_service_request(service)
        myzigate.remove_device(addr)

    def initiate_touchlink(service):
        myzigate.initiate_touchlink()

    def touchlink_factory_reset(service):
        myzigate.touchlink_factory_reset()

    def read_attribute(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint'))
        cluster = _to_int(service.data.get('cluster'))
        attribute_id = _to_int(service.data.get('attribute_id'))
        manufacturer_code = _to_int(service.data.get('manufacturer_code', '0'))
        myzigate.read_attribute_request(addr, endpoint, cluster, attribute_id,
                                        manufacturer_code=manufacturer_code)

    def write_attribute(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint'))
        cluster = _to_int(service.data.get('cluster'))
        attribute_id = _to_int(service.data.get('attribute_id'))
        attribute_type = _to_int(service.data.get('attribute_type'))
        value = _to_int(service.data.get('value'))
        attributes = [(attribute_id, attribute_type, value)]
        manufacturer_code = _to_int(service.data.get('manufacturer_code', '0'))
        myzigate.write_attribute_request(addr, endpoint, cluster, attributes,
                                         manufacturer_code=manufacturer_code)

    def add_group(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint'))
        groupaddr = service.data.get('group_addr')
        myzigate.add_group(addr, endpoint, groupaddr)

    def remove_group(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint'))
        groupaddr = service.data.get('group_addr')
        myzigate.remove_group(addr, endpoint, groupaddr)

    def get_group_membership(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint'))
        myzigate.get_group_membership(addr, endpoint)

    def action_onoff(service):
        addr = _get_addr_from_service_request(service)
        onoff = _to_int(service.data.get('onoff'))
        endpoint = _to_int(service.data.get('endpoint', '0'))
        ontime = _to_int(service.data.get('on_time', '0'))
        offtime = _to_int(service.data.get('off_time', '0'))
        effect = _to_int(service.data.get('effect', '0'))
        gradient = _to_int(service.data.get('gradient', '0'))
        myzigate.action_onoff(addr, endpoint, onoff, ontime, offtime, effect, gradient)

    def build_network_table(service):
        table = myzigate.build_neighbours_table(service.data.get('force', False))
        _LOGGER.debug('Neighbours table {}'.format(table))

    def ota_load_image(service):
        ota_image_path = service.data.get('imagepath')
        myzigate.ota_load_image(ota_image_path)

    def ota_image_notify(service):
        addr = _get_addr_from_service_request(service)
        destination_endpoint = _to_int(service.data.get('destination_endpoint', '1'))
        payload_type = _to_int(service.data.get('payload_type', '0'))
        myzigate.ota_image_notify(addr, destination_endpoint, payload_type)

    def get_ota_status(service):
        myzigate.get_ota_status()

    def view_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = _to_int(service.data.get('scene'))
        myzigate.view_scene(addr, endpoint, groupaddr, scene)

    def add_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = _to_int(service.data.get('scene'))
        name = service.data.get('scene_name')
        transition = _to_int(service.data.get('transition', '0'))
        myzigate.add_scene(addr, endpoint, groupaddr, scene, name, transition)

    def remove_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = _to_int(service.data.get('scene', -1))
        if scene == -1:
            scene = None
        myzigate.remove_scene(addr, endpoint, groupaddr, scene)

    def store_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = _to_int(service.data.get('scene'))
        myzigate.store_scene(addr, endpoint, groupaddr, scene)

    def recall_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = _to_int(service.data.get('scene'))
        myzigate.recall_scene(addr, endpoint, groupaddr, scene)

    def scene_membership_request(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        myzigate.scene_membership_request(addr, endpoint, groupaddr)

    def copy_scene(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        fromgroupaddr = service.data.get('from_group_addr')
        fromscene = _to_int(service.data.get('from_scene'))
        togroupaddr = service.data.get('to_group_addr')
        toscene = _to_int(service.data.get('to_scene'))
        myzigate.copy_scene(addr, endpoint, fromgroupaddr, fromscene, togroupaddr, toscene)

    def ias_warning(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        mode = service.data.get('mode', 'burglar')
        strobe = service.data.get('strobe', True)
        level = service.data.get('level', 'low')
        duration = service.data.get('duration', 60)
        strobe_cycle = service.data.get('strobe_cycle', 10)
        strobe_level = service.data.get('strobe_level', 'low')
        myzigate.action_ias_warning(addr, endpoint, mode, strobe, level, duration, strobe_cycle, strobe_level)

    def ias_squawk(service):
        addr = _get_addr_from_service_request(service)
        endpoint = _to_int(service.data.get('endpoint', '1'))
        mode = service.data.get('mode', 'armed')
        strobe = service.data.get('strobe', True)
        level = service.data.get('level', 'low')
        myzigate.action_ias_squawk(addr, endpoint, mode, strobe, level)

    def upgrade_firmware(service):
        from zigate.flasher import flash
        from zigate.firmware import download_latest
        port = myzigate._port
        pizigate = False
        if isinstance(myzigate, zigate.ZiGateGPIO):
            pizigate = True
        if myzigate._started and not pizigate:
            msg = 'You should stop zigate first using service zigate.stop_zigate and put zigate in download mode.'
            hass.components.persistent_notification.create(msg, title='ZiGate')
            return
        if pizigate:
            stop_zigate()
            myzigate.set_bootloader_mode()
        backup_filename = 'zigate_backup_{:%Y%m%d%H%M%S}.bin'.format(datetime.datetime.now())
        backup_filename = os.path.join(hass.config.config_dir, backup_filename)
        flash(port, save=backup_filename)
        msg = 'ZiGate backup created {}'.format(backup_filename)
        hass.components.persistent_notification.create(msg, title='ZiGate')
        firmware_path = service.data.get('path')
        if not firmware_path:
            firmware_path = download_latest()
        flash(port, write=firmware_path)
        msg = 'ZiGate flashed with {}'.format(firmware_path)
        hass.components.persistent_notification.create(msg, title='ZiGate')
        myzigate._version = None
        if pizigate:
            myzigate.set_running_mode()
            start_zigate()
        else:
            msg = 'Now you have to unplug/replug the ZiGate USB key and then call service zigate.start_zigate'
            hass.components.persistent_notification.create(msg, title='ZiGate')

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_zigate)
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_zigate)

    hass.services.register(DOMAIN, 'refresh_devices_list',
                           refresh_devices_list)
    hass.services.register(DOMAIN, 'generate_templates',
                           generate_templates)
    hass.services.register(DOMAIN, 'reset', zigate_reset)
    hass.services.register(DOMAIN, 'permit_join', permit_join)
    hass.services.register(DOMAIN, 'start_zigate', start_zigate)
    hass.services.register(DOMAIN, 'stop_zigate', stop_zigate)
    hass.services.register(DOMAIN, 'cleanup_devices', zigate_cleanup)
    hass.services.register(DOMAIN, 'refresh_device',
                           refresh_device,
                           schema=REFRESH_DEVICE_SCHEMA)
    hass.services.register(DOMAIN, 'discover_device',
                           discover_device,
                           schema=DISCOVER_DEVICE_SCHEMA)
    hass.services.register(DOMAIN, 'network_scan', network_scan)
    hass.services.register(DOMAIN, 'raw_command', raw_command,
                           schema=RAW_COMMAND_SCHEMA)
    hass.services.register(DOMAIN, 'identify_device', identify_device,
                           schema=IDENTIFY_SCHEMA)
    hass.services.register(DOMAIN, 'remove_device', remove_device,
                           schema=REMOVE_SCHEMA)
    hass.services.register(DOMAIN, 'initiate_touchlink', initiate_touchlink)
    hass.services.register(DOMAIN, 'touchlink_factory_reset',
                           touchlink_factory_reset)
    hass.services.register(DOMAIN, 'read_attribute', read_attribute,
                           schema=READ_ATTRIBUTE_SCHEMA)
    hass.services.register(DOMAIN, 'write_attribute', write_attribute,
                           schema=WRITE_ATTRIBUTE_SCHEMA)
    hass.services.register(DOMAIN, 'add_group', add_group,
                           schema=ADD_GROUP_SCHEMA)
    hass.services.register(DOMAIN, 'get_group_membership', get_group_membership,
                           schema=GET_GROUP_MEMBERSHIP_SCHEMA)
    hass.services.register(DOMAIN, 'remove_group', remove_group,
                           schema=REMOVE_GROUP_SCHEMA)
    hass.services.register(DOMAIN, 'action_onoff', action_onoff,
                           schema=ACTION_ONOFF_SCHEMA)
    hass.services.register(DOMAIN, 'build_network_table', build_network_table,
                           schema=BUILD_NETWORK_TABLE_SCHEMA)
    hass.services.register(DOMAIN, 'ias_warning', ias_warning,
                           schema=ACTION_IAS_WARNING_SCHEMA)
    hass.services.register(DOMAIN, 'ias_squawk', ias_squawk,
                           schema=ACTION_IAS_SQUAWK_SCHEMA)

    hass.services.register(DOMAIN, 'ota_load_image', ota_load_image,
                           schema=OTA_LOAD_IMAGE_SCHEMA)
    hass.services.register(DOMAIN, 'ota_image_notify', ota_image_notify,
                           schema=OTA_IMAGE_NOTIFY_SCHEMA)
    hass.services.register(DOMAIN, 'ota_get_status', get_ota_status)
    hass.services.register(DOMAIN, 'view_scene', view_scene,
                           schema=VIEW_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'add_scene', add_scene,
                           schema=ADD_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'remove_scene', remove_scene,
                           schema=REMOVE_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'store_scene', store_scene,
                           schema=STORE_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'recall_scene', recall_scene,
                           schema=RECALL_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'scene_membership_request', scene_membership_request,
                           schema=SCENE_MEMBERSHIP_REQUEST_SCHEMA)
    hass.services.register(DOMAIN, 'copy_scene', copy_scene,
                           schema=COPY_SCENE_SCHEMA)
    hass.services.register(DOMAIN, 'upgrade_firmware', upgrade_firmware)
    track_time_change(hass, refresh_devices_list,
                      hour=0, minute=0, second=0)

    if admin_panel:
        _LOGGER.debug('Start ZiGate Admin Panel on port 9998')
        myzigate.start_adminpanel()
        # myzigate.start_adminpanel(mount='/zigateproxy')
        # adminpanel_setup(hass, 'zigateproxy')

#     hass.async_create_task(
#         hass.config_entries.flow.async_init(
#             DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
#         )
#     )

    return True


# async def async_setup_entry(hass, entry):
#     _LOGGER.warning('async_setup_entry not implemented yet for ZiGate')
#     return False


class ZiGateComponentEntity(Entity):
    '''Representation of ZiGate Key'''
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
    '''Representation of ZiGate device'''

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
            if not self.hass:
                raise PlatformNotReady
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

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self.unique_id)
            },
            "name": self.name,
            "manufacturer": self._device.get_value('manufacturer'),
            "model": self._device.get_value('type'),
            "sw_version": self._device.get_value('datecode')
        }
