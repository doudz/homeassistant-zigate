# ZiGate component for Home Assistant
A new component to use the ZiGate (http://zigate.fr)

To install, copy all the files in your hass folder, under 'custom\_components' and adapt your configuration.yaml

To pair a new device, go in developer/services and call the 'zigate.permit\_join' service.
You have 30 seconds to pair your device.


Configuration example :

```
# Enable ZiGate (port will be auto-discovered)
zigate:

```
or

```
# Enable ZiGate
zigate:
  port: /dev/ttyS0

```

Currently it supports sensor, binary_sensor and switch
Light will be supported soon
