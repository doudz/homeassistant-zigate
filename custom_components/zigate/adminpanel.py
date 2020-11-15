"""ZiGate Admin panel proxy."""
import aiohttp
from homeassistant.components.http import HomeAssistantView


class PanelProxy(HomeAssistantView):
    """Reverse Proxy View."""

    requires_auth = True
    cors_allowed = True
    name = "panelproxy"

    def __init__(self, url, proxy_url):
        """Initialize view url."""
        self.url = url + r"{requested_url:.*}"
        self.proxy_url = proxy_url

    async def get(self, request, requested_url):
        """Handle GET proxy requests."""
        return await self._handle_request("GET", request, requested_url)

    async def post(self, request, requested_url):
        """Handle POST proxy requests."""
        return await self._handle_request("POST", request, requested_url)

    async def _handle_request(self, method, request, requested_url):
        """Handle proxy requests."""
        requested_url = requested_url or "/"
        headers = request.headers.copy()
        headers["Host"] = request.host
        headers["X-Real-Ip"] = request.remote
        headers["X-Forwarded-For"] = request.remote
        headers["X-Forwarded-Proto"] = request.scheme
        post_data = await request.read()
        async with aiohttp.request(
            method,
            self.proxy_url + requested_url,
            params=request.query,
            data=post_data,
            headers=headers,
        ) as resp:
            content = await resp.read()
            headers = resp.headers.copy()
            return aiohttp.web.Response(
                body=content, status=resp.status, headers=headers
            )


def adminpanel_setup(hass, url_path):
    """Set up the proxy frontend panels."""
    hass.http.register_view(PanelProxy("/" + url_path, 'http://localhost:9998/' + url_path))
    hass.components.frontend.async_register_built_in_panel(
        "iframe",
        "Zigate Admin",
        "mdi:zigbee",
        "proxy_" + url_path,
        {"url": "/" + url_path},
        require_admin=True,
    )
