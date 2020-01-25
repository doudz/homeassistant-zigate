import logging
import voluptuous as vol
from zigate.flasher import flash
from zigate.firmware import download_latest

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_time_change
from homeassistant.helpers.discovery import load_platform
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP
)

from .dispatcher import device_added
from .. import ZiGateDeviceEntity
from ..const import (
    DOMAIN, 
    SUPPORTED_PLATFORMS,
    DATA_ZIGATE_DEVICES,
    DATA_ZIGATE_ATTRS,
    ADDR,
    IEEE
)

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


class ZigateServices:
    """Initialize Zigate services."""

    def __init__(self, hass, config, myzigate, component):
        self.hass = hass
        self.myzigate = myzigate
        self.component = component
        self.channel = config[DOMAIN].get('channel')
        self.enable_led = config[DOMAIN].get('enable_led', True)

        self.hass.bus.listen_once(EVENT_HOMEASSISTANT_START, self.start_zigate)
        self.hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, self.stop_zigate)

        self.hass.services.register(DOMAIN, 'refresh_devices_list', self.refresh_devices_list)
        self.hass.services.register(DOMAIN, 'generate_templates', self.generate_templates)
        self.hass.services.register(DOMAIN, 'reset', self.zigate_reset)
        self.hass.services.register(DOMAIN, 'permit_join', self.permit_join)
        self.hass.services.register(DOMAIN, 'start_zigate', self.start_zigate)
        self.hass.services.register(DOMAIN, 'stop_zigate', self.stop_zigate)
        self.hass.services.register(DOMAIN, 'cleanup_devices', self.zigate_cleanup)
        self.hass.services.register(DOMAIN, 'refresh_device', self.refresh_device,
            schema=REFRESH_DEVICE_SCHEMA)
        self.hass.services.register(DOMAIN, 'discover_device', self.discover_device,
            schema=DISCOVER_DEVICE_SCHEMA)
        self.hass.services.register(DOMAIN, 'network_scan', self.network_scan)
        self.hass.services.register(DOMAIN, 'raw_command', self.raw_command,
            schema=RAW_COMMAND_SCHEMA)
        self.hass.services.register(DOMAIN, 'identify_device',self.identify_device,
            schema=IDENTIFY_SCHEMA)
        self.hass.services.register(DOMAIN, 'remove_device', self.remove_device, 
            schema=REMOVE_SCHEMA)
        self.hass.services.register(DOMAIN, 'initiate_touchlink', self.initiate_touchlink)
        self.hass.services.register(DOMAIN, 'touchlink_factory_reset', self.touchlink_factory_reset)
        self.hass.services.register(DOMAIN, 'read_attribute', self.read_attribute,
            schema=READ_ATTRIBUTE_SCHEMA)
        self.hass.services.register(DOMAIN, 'write_attribute', self.write_attribute,
            schema=WRITE_ATTRIBUTE_SCHEMA)
        self.hass.services.register(DOMAIN, 'add_group', self.add_group,
            schema=ADD_GROUP_SCHEMA)
        self.hass.services.register(DOMAIN, 'get_group_membership', self.get_group_membership,
            schema=GET_GROUP_MEMBERSHIP_SCHEMA)
        self.hass.services.register(DOMAIN, 'remove_group', self.remove_group,
            schema=REMOVE_GROUP_SCHEMA)
        self.hass.services.register(DOMAIN, 'action_onoff', self.action_onoff,
            schema=ACTION_ONOFF_SCHEMA)
        self.hass.services.register(DOMAIN, 'build_network_table', self.build_network_table,
            schema=BUILD_NETWORK_TABLE_SCHEMA)
        self.hass.services.register(DOMAIN, 'ias_warning', self.ias_warning,
            schema=ACTION_IAS_WARNING_SCHEMA)
        self.hass.services.register(DOMAIN, 'ias_squawk', self.ias_squawk,
            schema=ACTION_IAS_SQUAWK_SCHEMA)
        self.hass.services.register(DOMAIN, 'ota_load_image', self.ota_load_image,
            schema=OTA_LOAD_IMAGE_SCHEMA)
        self.hass.services.register(DOMAIN, 'ota_image_notify', self.ota_image_notify,
            schema=OTA_IMAGE_NOTIFY_SCHEMA)
        self.hass.services.register(DOMAIN, 'ota_get_status', self.get_ota_status)
        self.hass.services.register(DOMAIN, 'view_scene', self.view_scene,
            schema=VIEW_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'add_scene', self.add_scene,
            schema=ADD_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'remove_scene', self.remove_scene,
            schema=REMOVE_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'store_scene', self.store_scene,
            schema=STORE_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'recall_scene', self.recall_scene,
            schema=RECALL_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'scene_membership_request', self.scene_membership_request,
            schema=SCENE_MEMBERSHIP_REQUEST_SCHEMA)
        self.hass.services.register(DOMAIN, 'copy_scene', self.copy_scene,
            schema=COPY_SCENE_SCHEMA)
        self.hass.services.register(DOMAIN, 'upgrade_firmware', self.upgrade_firmware)        

        track_time_change(
            self.hass, self.refresh_devices_list, hour=0, minute=0, second=0)

    def zigate_reset(self, service):
        self.myzigate.reset()

    def permit_join(self, service):
        self.myzigate.permit_join()

    def zigate_cleanup(self, service):
        """Remove missing device."""
        self.myzigate.cleanup_devices()

    def start_zigate(self, service_event=None):
        self.myzigate.autoStart(self.channel)
        self.myzigate.start_auto_save()
        self.myzigate.set_led(self.enable_led)
        version = self.myzigate.get_version_text()
        if version < '3.1a':
            self.hass.components.persistent_notification.create(
                ('Your zigate firmware is outdated, '
                 'Please upgrade to 3.1a or later !'),
                title='ZiGate')
        # first load
        for device in self.myzigate.devices:
            device_added(device=device)

        for platform in SUPPORTED_PLATFORMS:
            load_platform(self.hass, platform, DOMAIN, {}, config)

        self.hass.bus.fire('zigate.started')

    def stop_zigate(self, service=None):
        self.myzigate.save_state()
        self.myzigate.close()

        self.hass.bus.fire('zigate.stopped')

    def refresh_devices_list(self, service):
        self.myzigate.get_devices_list()

    def generate_templates(self, service):
        self.myzigate.generate_templates(self.hass.config.config_dir)

    def _get_addr_from_service_request(self, service):
        entity_id = service.data.get(ATTR_ENTITY_ID)
        ieee = service.data.get(IEEE)
        addr = service.data.get(ADDR)
        if entity_id:
            entity = self.component.get_entity(entity_id)
            if entity:
                addr = entity._device.addr
        elif ieee:
            device = self.myzigate.get_device_from_ieee(ieee)
            if device:
                addr = device.addr
        return addr

    def _to_int(self, value):
        '''
        convert str to int
        '''
        if 'x' in value:
            return int(value, 16)
        return int(value)

    def refresh_device(self, service):
        full = service.data.get('full', False)
        addr = self._get_addr_from_service_request(service)
        if addr:
            self.myzigate.refresh_device(addr, full=full)
        else:
            for device in self.myzigate.devices:
                device.refresh_device(full=full)

    def discover_device(self, service):
        addr = self._get_addr_from_service_request(service)
        if addr:
            self.myzigate.discover_device(addr, True)

    def network_scan(self, service):
        self.myzigate.start_network_scan()

    def raw_command(self, service):
        cmd = self._to_int(service.data.get('cmd'))
        data = service.data.get('data', '')
        self.myzigate.send_data(cmd, data)

    def identify_device(self, service):
        addr = self._get_addr_from_service_request(service)
        self.myzigate.identify_device(addr)

    def remove_device(self, service):
        addr = self._get_addr_from_service_request(service)
        self.myzigate.remove_device(addr)

    def initiate_touchlink(self, service):
        self.myzigate.initiate_touchlink()

    def touchlink_factory_reset(self, service):
        self.myzigate.touchlink_factory_reset()

    def read_attribute(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint'))
        cluster = self._to_int(service.data.get('cluster'))
        attribute_id = self._to_int(service.data.get('attribute_id'))
        manufacturer_code = self._to_int(service.data.get('manufacturer_code', '0'))
        self.myzigate.read_attribute_request(addr, endpoint, cluster, attribute_id,
            manufacturer_code=manufacturer_code)

    def write_attribute(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint'))
        cluster = self._to_int(service.data.get('cluster'))
        attribute_id = self._to_int(service.data.get('attribute_id'))
        attribute_type = self._to_int(service.data.get('attribute_type'))
        value = self._to_int(service.data.get('value'))
        attributes = [(attribute_id, attribute_type, value)]
        manufacturer_code = self._to_int(service.data.get('manufacturer_code', '0'))
        self.myzigate.write_attribute_request(addr, endpoint, cluster, attributes,
            manufacturer_code=manufacturer_code)

    def add_group(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint'))
        groupaddr = service.data.get('group_addr')
        self.myzigate.add_group(addr, endpoint, groupaddr)

    def remove_group(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint'))
        groupaddr = service.data.get('group_addr')
        self.myzigate.remove_group(addr, endpoint, groupaddr)

    def get_group_membership(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint'))
        self.myzigate.get_group_membership(addr, endpoint)

    def action_onoff(self, service):
        addr = self._get_addr_from_service_request(service)
        onoff = self._to_int(service.data.get('onoff'))
        endpoint = self._to_int(service.data.get('endpoint', '0'))
        ontime = self._to_int(service.data.get('on_time', '0'))
        offtime = self._to_int(service.data.get('off_time', '0'))
        effect = self._to_int(service.data.get('effect', '0'))
        gradient = self._to_int(service.data.get('gradient', '0'))
        self.myzigate.action_onoff(addr, endpoint, onoff, ontime, offtime, effect, gradient)

    def build_network_table(self, service):
        table = self.myzigate.build_neighbours_table(service.data.get('force', False))
        _LOGGER.debug('Neighbours table {}'.format(table))

    def ota_load_image(self, service):
        ota_image_path = service.data.get('imagepath')
        self.myzigate.ota_load_image(ota_image_path)

    def ota_image_notify(self, service):
        addr = self._get_addr_from_service_request(service)
        destination_endpoint = self._to_int(service.data.get('destination_endpoint', '1'))
        payload_type = self._to_int(service.data.get('payload_type', '0'))
        self.myzigate.ota_image_notify(addr, destination_endpoint, payload_type)

    def get_ota_status(self, service):
        self.myzigate.get_ota_status()

    def view_scene(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = self._to_int(service.data.get('scene'))
        self.myzigate.view_scene(addr, endpoint, groupaddr, scene)

    def add_scene(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = self._to_int(service.data.get('scene'))
        name = service.data.get('scene_name')
        transition = self._to_int(service.data.get('transition', '0'))
        self.myzigate.add_scene(addr, endpoint, groupaddr, scene, name, transition)

    def remove_scene(service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = self._to_int(service.data.get('scene', -1))
        if scene == -1:
            scene = None
        self.myzigate.remove_scene(addr, endpoint, groupaddr, scene)

    def store_scene(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = self._to_int(service.data.get('scene'))
        self.myzigate.store_scene(addr, endpoint, groupaddr, scene)

    def recall_scene(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        scene = self._to_int(service.data.get('scene'))
        self.myzigate.recall_scene(addr, endpoint, groupaddr, scene)

    def scene_membership_request(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        groupaddr = service.data.get('group_addr')
        self.myzigate.scene_membership_request(addr, endpoint, groupaddr)

    def copy_scene(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        fromgroupaddr = service.data.get('from_group_addr')
        fromscene = self._to_int(service.data.get('from_scene'))
        togroupaddr = service.data.get('to_group_addr')
        toscene = self._to_int(service.data.get('to_scene'))
        self.myzigate.copy_scene(addr, endpoint, fromgroupaddr, fromscene, togroupaddr, toscene)

    def ias_warning(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        mode = service.data.get('mode', 'burglar')
        strobe = service.data.get('strobe', True)
        level = service.data.get('level', 'low')
        duration = service.data.get('duration', 60)
        strobe_cycle = service.data.get('strobe_cycle', 10)
        strobe_level = service.data.get('strobe_level', 'low')
        self.myzigate.action_ias_warning(addr, endpoint, mode, strobe, level, duration, strobe_cycle, strobe_level)

    def ias_squawk(self, service):
        addr = self._get_addr_from_service_request(service)
        endpoint = self._to_int(service.data.get('endpoint', '1'))
        mode = service.data.get('mode', 'armed')
        strobe = service.data.get('strobe', True)
        level = service.data.get('level', 'low')
        self.myzigate.action_ias_squawk(addr, endpoint, mode, strobe, level)

    def upgrade_firmware(self, service):
        port = self.myzigate.connection._port
        pizigate = False
        if isinstance(self.myzigate, zigate.ZiGateGPIO):
            pizigate = True
        if self.myzigate._started and not pizigate:
            msg = 'You should stop zigate first using service zigate.stop_zigate and put zigate in download mode.'
            self.hass.components.persistent_notification.create(msg, title='ZiGate')
            return
        if pizigate:
            self.stop_zigate()
            self.myzigate.set_bootloader_mode()
        backup_filename = 'zigate_backup_{:%Y%m%d%H%M%S}.bin'.format(datetime.datetime.now())
        backup_filename = os.path.join(self.hass.config.config_dir, backup_filename)
        flash(port, save=backup_filename)
        msg = 'ZiGate backup created {}'.format(backup_filename)
        self.hass.components.persistent_notification.create(msg, title='ZiGate')
        firmware_path = service.data.get('path')
        if not firmware_path:
            firmware_path = download_latest()
        flash(port, write=firmware_path)
        msg = 'ZiGate flashed with {}'.format(firmware_path)
        self.hass.components.persistent_notification.create(msg, title='ZiGate')
        self.myzigate._version = None
        if pizigate:
            self.myzigate.set_running_mode()
            self.start_zigate()
        else:
            msg = 'Now you have to unplug/replug the ZiGate USB key and then call service zigate.start_zigate'
            self.hass.components.persistent_notification.create(msg, title='ZiGate')
