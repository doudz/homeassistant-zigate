# ZiGate component for Home Assistant
A new component to use the ZiGate (http://zigate.fr)

To install:
- if not exists, create folder 'custom\_components' under your home assitant directory (beside configuration.yaml)
- copy all the files in your hass folder, under 'custom\_components' like that :

```
custom_components/
├── binary_sensor
│   └── zigate.py
├── light
│   └── zigate.py
├── sensor
│   └── zigate.py
├── switch
│   └── zigate.py
└── zigate
    ├── __init__.py
    └── services.yaml
```
    
- adapt your configuration.yaml

To pair a new device, go in developer/services and call the 'zigate.permit\_join' service.
You have 30 seconds to pair your device.

WARNING : Since commit https://github.com/doudz/homeassistant-zigate/commit/ddf141ebb103eaa4f6d585b645262446fd77d202, you have to rename the file .zigate.json to zigate.json to avoid loosing you configuration !


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

or
if you want to use Wifi ZiGate (or usb zigate forwarded with ser2net for example)
Port is optionnal, default is 9999 

```
# Enable ZiGate Wifi
zigate:
  host: 192.168.0.10:9999

```

Currently it supports sensor, binary_sensor and switch and light (brightness and color)
