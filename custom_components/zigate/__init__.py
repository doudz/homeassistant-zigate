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

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.components.group import \
    ENTITY_ID_FORMAT as GROUP_ENTITY_ID_FORMAT
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL
)


from .core.const import (
    DOMAIN,
    SCAN_INTERVAL,
    PERSISTENT_FILE,
    DATA_ZIGATE_DEVICES,
    DATA_ZIGATE_ATTRS,
    DATA_ZIGATE_CONFIG,
    ZIGATE_ID,
    SUPPORTED_PLATFORMS
)
from .core.admin_panel import ZiGateAdminPanel, ZiGateProxy
from .core.dispatcher import ZigateDispatcher
from .core.services import ZigateServices
from .core.entities import ZiGateComponentEntity

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['zigate']

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


async def async_setup(hass, config):
    """Load configuration for Zigate component."""

    hass.data[DATA_ZIGATE_DEVICES] = {}
    hass.data[DATA_ZIGATE_ATTRS] = {}

    if DOMAIN not in config:
        return True

    config = config[DOMAIN]
    hass.data[DATA_ZIGATE_CONFIG] = config

    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Setup zigate platform."""

    # Merge config entry and yaml config
    config = config_entry.data
    options = config_entry.options
    config = {**config, **options}

    # Update hass.data with merged config so we can access it elsewhere
    hass.data[DATA_ZIGATE_CONFIG] = config

    port = config.get("port")
    host = config.get("host")
    gpio = config.get("gpio")
    channel = config.get("channel")
    enable_led = config.get("enable_led", True)
    admin_panel = config.get("admin_panel", True)
    scan_interval = datetime.timedelta(
        seconds=config.get("scan_interval", SCAN_INTERVAL)
    )

    persistent_file = os.path.join(hass.config.config_dir, PERSISTENT_FILE)

    _LOGGER.debug('Port : %s', port)
    _LOGGER.debug('Host : %s', host)
    _LOGGER.debug('GPIO : %s', gpio)
    _LOGGER.debug('Led : %s', enable_led)
    _LOGGER.debug('Channel : %s', channel)
    _LOGGER.debug('Scan interval : %s', scan_interval)
    _LOGGER.debug('Admin panel : %s', admin_panel)

    myzigate = zigate.connect(
        port=port,
        host=host,
        path=persistent_file,
        auto_start=False,
        gpio=gpio
    )
    hass.data[DOMAIN] = myzigate
    try:
        myzigate.autoStart(channel)
        myzigate.start_auto_save()
        myzigate.set_led(enable_led)
        version = myzigate.get_version_text()
        if version < '3.1a':
            hass.components.persistent_notification.create(
                ('Your zigate firmware is outdated, '
                 'Please upgrade to 3.1a or later !'), title='ZiGate')
        hass.data[ZIGATE_ID] = myzigate.ieee
        myzigate.save_state()
        myzigate.close()
    except:
        return False

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, hass.data[ZIGATE_ID])},
        name='Zigate Coordinator',
        manufacturer='Zigate',
        sw_version=version,
    )

    platform = EntityPlatform(
        hass=hass,
        logger=_LOGGER,
        domain=DOMAIN,
        platform_name=DOMAIN,
        platform=None,
        scan_interval=scan_interval,
        entity_namespace=None,
    )
    platform.config_entry = config_entry

    ZigateDispatcher(hass, config, platform)
    services = ZigateServices(hass, config_entry, config, platform)
    await services.async_register()
    entity = ZiGateComponentEntity(myzigate)
    hass.data[DATA_ZIGATE_DEVICES][DOMAIN] = entity
    await platform.async_add_entities([entity])

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

    await hass.services.async_call(DOMAIN, "start_zigate")

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""

    for component in SUPPORTED_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(config_entry, component)
        )

    await hass.services.async_call(DOMAIN, "stop_zigate")

    return True
