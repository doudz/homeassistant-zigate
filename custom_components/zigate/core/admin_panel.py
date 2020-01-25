import requests
from aiohttp import web

from homeassistant.components.http import HomeAssistantView

BASE_PANEL = '''
<dom-module id='ha-panel-zigateadmin'>
  <template>
    <iframe src="/zigateproxy?q=%2F" style="width:99%; height:99%; border:0"></iframe>
  </template>
</dom-module>

<script>
class HaPanelZiGateadmin extends Polymer.Element {
  static get is() { return 'ha-panel-zigateadmin'; }

  static get properties() {
    return {
      // Home Assistant object
      hass: Object,
      // If should render in narrow mode
      narrow: {
        type: Boolean,
        value: false,
      },
      // If sidebar is currently shown
      showMenu: {
        type: Boolean,
        value: false,
      },
      // Home Assistant panel info
      // panel.config contains config passed to register_panel serverside
      panel: Object
    };
  }
}
customElements.define(HaPanelZiGateadmin.is, HaPanelZiGateadmin);
</script>
'''


class ZiGateAdminPanel(HomeAssistantView):
    requires_auth = False
    name = "zigateadmin"
    url = "/zigateadmin.html"

    async def get(self, request):
        """Handle ZiGate admin panel requests."""
        response = web.Response(text=base_panel)
        response.headers["Cache-Control"] = "no-cache"
        return response


class ZiGateProxy(HomeAssistantView):
    requires_auth = False
    cors_allowed = True
    name = "zigateproxy"
    url = "/zigateproxy"

    async def get(self, request):
        """Handle ZiGate proxy requests."""
        headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        r = requests.get('http://localhost:9998'+request.query.get('q', '/'), headers=headers)
        headers = r.headers.copy()
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, PUT'
        headers['Cache-Control'] = 'no-cache'
        headers['Pragma'] = 'no-cache'
        return web.Response(body=r.content, status=r.status_code, headers=headers)


