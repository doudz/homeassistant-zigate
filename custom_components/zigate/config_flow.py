"""Adds config flow for ZiGate."""
import logging
import zigate
import os
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL

from .core.const import DOMAIN, AVAILABLE_MODES, PERSISTENT_FILE

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(mode, default=False): bool for mode in AVAILABLE_MODES
    }
)

USB_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT): str,
    }
)

WIFI_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): str,
    }
)

_LOGGER = logging.getLogger(__name__)


class ZiGateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ZiGate config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Livebox flow."""
        self.id = None

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):

        errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None and bool(user_input):
            if user_input.get("usb") or (user_input.get("host") is None and user_input.get("port")):
                return await self.async_step_usb(user_input)
            elif user_input.get("wifi") or (user_input.get("host") and user_input.get("port")):
                return await self.async_step_wifi(user_input)
            elif user_input.get("gpio", False):
                return await self.async_step_register(user_input)

        errors["base"] = "single_instance_allowed"
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_usb(self, user_input=None):
        """Step for register component."""
        if user_input.get("port") is not None:
            self.port = user_input["port"]
            return await self.async_step_register(user_input)

        return self.async_show_form(
            step_id="usb", data_schema=USB_SCHEMA
        )

    async def async_step_wifi(self, user_input=None):
        """Step for register component."""
        if user_input.get("host") is not None:
            self.host = user_input["host"]
            self.port = user_input["port"]
            return await self.async_step_register(user_input)

        return self.async_show_form(
            step_id="wifi", data_schema=WIFI_SCHEMA
        )

    async def async_step_register(self, user_input=None):
        """Step for register component."""

        errors = {}
        if user_input is None:
            return await self.async_step_user()

        myzigate = zigate.connect(
            host=user_input.get("host", None),
            port=user_input.get("port", None),
            path=os.path.join(self.hass.config.config_dir, PERSISTENT_FILE),
            auto_start=False,
            gpio=user_input.get("gpio", None)
        )
        try:
            myzigate.autoStart()
            self.id = myzigate.ieee
            myzigate.save_state()
            myzigate.close()
        except:
            _LOGGER.debug("Zigate not found")
            errors["base"] = "cannot_connect"

        if self.id is not None:
            return self.async_create_entry(
                title=DOMAIN,
                data={
                    "id": self.id,
                    "host": user_input.get("host", None),
                    "port": user_input.get("port", None),
                    "gpio": user_input.get("gpio", None)
                },
            )

        errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="user", errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get option flow."""
        return ZiGateOptionsFlowHandler(config_entry)


class ZiGateOptionsFlowHandler(config_entries.OptionsFlow):
    """ZiGate config flow options."""

    def __init__(self, config_entry):
        """Load the options."""
        self.config_entry = config_entry

        self.channel = self.config_entry.options.get("channel", "")
        self.enable_led = self.config_entry.options.get("enable_led", True)
        self.polling = self.config_entry.options.get("polling", True)
        self.scan_interval = self.config_entry.options.get("scan_interval", 120)
        self.admin_panel = self.config_entry.options.get("admin_panel", True)

    async def async_step_init(self, user_input=None):
        """Manage the options."""

        OPTIONS_SCHEMA = vol.Schema({
            vol.Optional('channel', default=self.channel): int,
            vol.Optional('enable_led', default=self.enable_led): bool,
            vol.Optional('polling', default=self.polling): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=self.scan_interval): int,
            vol.Optional('admin_panel', default=self.admin_panel): bool,
        })

        if user_input is not None:
            return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)
