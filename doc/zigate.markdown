---
layout: page
title: "ZiGate component"
description: "Instructions on how to use the Component ZiGate with Home Assistant."
date: 2018-07-03 12:00
sidebar: true
comments: false
sharing: true
footer: true
logo: home-assistant.png
ha_category: Other
---


The `zigate` component allows you to use the ZiGate module (http://www.zigate.fr)


Available ZiGate platforms:

- [Binary sensor](/components/binary_sensor/) (`binary_sensor`)
- [Light](/components/light/) (`light`)
- [Sensor](/components/sensor/) (`sensor`)
- [Switch](/components/switch/) (`switch`)
- [Cover](/components/cover/) (`cover`)

To integrate the ZiGate component in Home Assistant, add the following section to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry (port auto-discovery)
[zigate]:

# or

# Example configuration.yaml entry setting the USB port
[zigate]:
  port: /dev/ttyUSB0
  channel: 15
  enable_led: false
```

or
if you want to use Wifi ZiGate (or usb zigate forwarded with ser2net for example)
Port is optionnal, default is 9999 

```yaml
# Enable ZiGate Wifi
zigate:
  host: 192.168.0.10:9999

```

To pair a new device, go in developer/services and call the 'zigate.permit\_join' service.
You have 30 seconds to pair your device.
Entities (sensor, switch, light, etc) will be auto-generated.

