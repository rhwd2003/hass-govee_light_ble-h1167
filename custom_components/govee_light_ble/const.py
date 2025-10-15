DOMAIN = "govee_light_ble"
DISCOVERY_NAMES = ('Govee_', 'ihoment_', 'GBK_', 'H1167', 'H1167_')
READ_CHARACTERISTIC_UUID = '00010203-0405-0607-0809-0a0b0c0d2b10'
WRITE_CHARACTERISTIC_UUID = '00010203-0405-0607-0809-0a0b0c0d2b11'

# Connection settings
MAX_CONNECTION_ATTEMPTS = 3
CONNECTION_TIMEOUT = 10  # Reduced from 30 to 10 seconds
RETRY_DELAY = 1  # Reduced from 2 to 1 second
INITIAL_CONNECTION_TIMEOUT = 15  # Longer timeout for initial connection
RECONNECTION_TIMEOUT = 8  # Shorter timeout for reconnections
