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

import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.group import \
    ENTITY_ID_FORMAT as GROUP_ENTITY_ID_FORMAT
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL
)


from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    DATA_ZIGATE_DEVICES,
    DATA_ZIGATE_ATTRS
)
from .core.admin_panel import ZiGateAdminPanel, ZiGateProxy
from .core.dispatcher import ZigateDispatcher
from .core.services import ZigateServices
from .core.entities import ZiGateComponentEntity

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
    ZigateDispatcher(hass, config, component)
    ZigateServices(hass, config, myzigate, component)

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

    #~ hass.async_create_task(
        #~ hass.config_entries.flow.async_init(
            #~ DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
        #~ )
    #~ )

    return True
