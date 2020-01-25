"""
ZiGate component.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/zigate/
"""
import logging
import voluptuous as vol
import os
import datetime
import requests
from aiohttp import web
import zigate

from homeassistant import config_entries
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.group import \
    ENTITY_ID_FORMAT as GROUP_ENTITY_ID_FORMAT
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.event import track_time_change
from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL
)
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    DATA_ZIGATE_DEVICES,
    DATA_ZIGATE_ATTRS
)
from .core.admin_panel import ZiGateAdminPanel, ZiGateProxy
from .core.dispatcher import ZigateDispatcher
from .core.services import ZigateServices

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_ALL_ZIGATE = GROUP_ENTITY_ID_FORMAT.format('all_zigate')

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

    persistent_file = os.path.join(hass.config.config_dir, 'zigate.json')

    _LOGGER.debug('Port : %s', port)
    _LOGGER.debug('Host : %s', host)
    _LOGGER.debug('GPIO : %s', gpio)
    _LOGGER.debug('Led : %s', enable_led)
    _LOGGER.debug('Channel : %s', channel)
    _LOGGER.debug('Scan interval : %s', scan_interval)

    myzigate = zigate.connect(
        port=port, host=host, path=persistent_file, auto_start=False, gpio=gpio)

    _LOGGER.debug('ZiGate object created %s', myzigate)

    hass.data[DOMAIN] = myzigate
    hass.data[DATA_ZIGATE_DEVICES] = {}
    hass.data[DATA_ZIGATE_ATTRS] = {}

    component = EntityComponent(_LOGGER, DOMAIN, hass, scan_interval)
    component.setup(config)
    entity = ZiGateComponentEntity(myzigate)
    hass.data[DATA_ZIGATE_DEVICES]['zigate'] = entity
    component.add_entities([entity])
    ZigateDispatcher(hass, component)
    ZigateServices(hass, myzigate)

    track_time_change(
        hass, refresh_devices_list, hour=0, minute=0, second=0)

    if admin_panel:
        _LOGGER.debug('Start ZiGate Admin Panel on port 9998')
        myzigate.start_adminpanel(prefix='/zigateproxy')

        hass.http.register_view(ZiGateAdminPanel())
        hass.http.register_view(ZiGateProxy())
        custom_panel_config = {
            "name": "zigateadmin",
            "embed_iframe": False,
            "trust_external": False,
            "html_url": "/zigateadmin.html",
        }

        config = {}
        config["_panel_custom"] = custom_panel_config

        hass.components.frontend.async_register_built_in_panel(
            component_name="custom",
            sidebar_title='Zigate Admin',
            sidebar_icon='mdi:zigbee',
            frontend_url_path="zigateadmin",
            config=config,
            require_admin=True,
        )

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
        )
    )

    return True


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
        import zigate
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
