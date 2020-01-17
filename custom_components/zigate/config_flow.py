"""Adds config flow for ZiGate."""

from collections import OrderedDict
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from .const import DOMAIN


@config_entries.HANDLERS.register(DOMAIN)
class ZiGateConfigFlow(config_entries.ConfigFlow):
    """ZiGate config flow."""
    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        errors = {}

        fields = OrderedDict()
        fields[vol.Optional(CONF_PORT)] = str

        if user_input is not None:
            print(user_input)
            return self.async_create_entry(title=user_input.get(CONF_PORT, 'Auto'), data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_import(self, import_info):
        """Handle a ZiGate config import."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        print('import ', import_info)

        return self.async_create_entry(title="configuration.yaml", data={})
