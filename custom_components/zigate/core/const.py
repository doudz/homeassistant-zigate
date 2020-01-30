DOMAIN = 'zigate'
SCAN_INTERVAL = 120
DATA_ZIGATE_DEVICES = 'zigate_devices'
DATA_ZIGATE_ATTRS = 'zigate_attributes'
DATA_ZIGATE_CONFIG = 'zigate_config'
ZIGATE_ID = 'zigate_id'
ADDR = 'addr'
IEEE = 'ieee'
SUPPORTED_PLATFORMS = (
    'sensor',
    'binary_sensor',
    'switch',
    'light',
    'cover',
    'climate'
)
PERSISTENT_FILE = 'zigate.json'
AVAILABLE_MODES = ['usb', 'wifi', 'gpio']
