# Bluetooth Connection Timeout Fixes

## Summary of Changes

This document describes the improvements made to fix Bluetooth connection timeout issues in the Govee Light BLE integration.

## Problems Identified

1. **Long connection timeouts (30 seconds)** - Caused the system to hang for too long
2. **Inefficient retry logic** - Used `bleak_retry_connector` which added unnecessary complexity
3. **No connection state management** - Devices could get stuck in bad states
4. **Missing connection locking** - Race conditions could occur with concurrent connection attempts
5. **Poor error handling** - Connection failures would make devices unavailable
6. **Wrong connectable flag** - Devices were marked as non-connectable

## Changes Made

### 1. Connection Constants (`const.py`)
- Reduced `MAX_CONNECTION_ATTEMPTS` from 5 to 3
- Reduced `CONNECTION_TIMEOUT` from 30 to 10 seconds
- Reduced `RETRY_DELAY` from 2 to 1 second
- Added `INITIAL_CONNECTION_TIMEOUT` (15 seconds) for first connection
- Added `RECONNECTION_TIMEOUT` (8 seconds) for subsequent connections

### 2. API Connection Handling (`api.py`)

#### New Features:
- **Connection locking** - Prevents concurrent connection attempts using `asyncio.Lock`
- **Exponential backoff** - Implements intelligent backoff after repeated failures
- **Connection state tracking** - Tracks failure count and last attempt time
- **Improved cleanup** - New `_cleanup_connection()` method ensures clean disconnects
- **Direct BleakClient usage** - Removed dependency on `bleak_retry_connector` for more control
- **Better error logging** - More detailed error messages with connection status

#### Key Methods Added/Modified:
- `_ensureConnected()` - Now uses locking to prevent race conditions
- `_connect()` - Completely rewritten with:
  - Exponential backoff for repeated failures
  - Proper cleanup between attempts
  - Better timeout handling (different for initial vs reconnection)
  - More detailed error logging
- `_cleanup_connection()` - New method for proper connection cleanup
- `sendPacketBuffer()` - Enhanced with better error handling and packet delays
- `reset_connection_state()` - New method to reset connection state
- `is_connected` - Property to check connection status
- `connection_failures` - Property to track failure count

### 3. Coordinator Improvements (`coordinator.py`)

#### Changes:
- Fixed `connectable` flag from `False` to `True` (critical fix!)
- Added error handling in `_async_update_data()` to prevent device unavailability
- Added `reset_connection()` method for manual connection reset
- Added `connection_status` property for diagnostics
- Better logging on connection success after failures

### 4. Integration Setup (`__init__.py`)

#### Improvements:
- Fixed missing imports (`Callable`, `DataUpdateCoordinator`)
- Better error handling during setup
- Proper device disconnection on unload
- More informative logging throughout
- Fixed `connectable` flag in device lookup

## How These Changes Fix Your Issues

### Connection Timeout Errors
- **Shorter timeouts** prevent long waits
- **Better retry logic** with exponential backoff prevents hammering the device
- **Connection cleanup** ensures fresh connection attempts
- **Proper locking** prevents multiple simultaneous connection attempts

### TimeoutError Issues
- **Adaptive timeouts** - First connection gets 15s, reconnections get 8s
- **Proper cleanup** between attempts prevents stale connections
- **Connection state tracking** prevents repeated attempts to problematic devices

### Device Availability
- **Graceful error handling** - Devices stay available even with connection issues
- **Connection state reset** - Automatic recovery after successful connections
- **Better diagnostics** - Detailed logging helps identify issues

## Testing Instructions

### 1. Restart Home Assistant
After updating the files, restart Home Assistant completely:
```bash
# In Home Assistant
Developer Tools > YAML > Restart
```

### 2. Monitor Logs
Watch the logs for connection attempts:
```bash
# In Home Assistant
Settings > System > Logs

# Or via command line if you have access:
tail -f /config/home-assistant.log | grep govee_light_ble
```

### 3. Expected Log Messages

**Successful Connection:**
```
INFO: Initializing Govee device: [device_name] ([address])
INFO: Connection attempt 1/3 for [address]
INFO: Successfully connected to [address] on attempt 1
```

**Connection with Retries:**
```
WARNING: Connection timeout for [address], attempt 1 (timeout: 15s)
INFO: Connection attempt 2/3 for [address]
INFO: Successfully connected to [address] on attempt 2
```

**Failed Connection (with backoff):**
```
ERROR: Failed to connect to [address] after 3 attempts (failure count: 1)
WARNING: Failed to update [device_name] ([address]): Exception: [error]. Connection failures: 1
```

### 4. Test Scenarios

1. **Normal Operation**: Devices should connect within 1-2 attempts
2. **Device Out of Range**: Should fail gracefully and retry later
3. **Device Turned Off**: Should handle gracefully without making integration unavailable
4. **Multiple Devices**: All devices should connect independently without interfering

### 5. Manual Connection Reset (if needed)

If a device gets stuck, you can reload the integration:
```
Settings > Devices & Services > Govee Bluetooth Lights > [device] > Reload
```

## Troubleshooting

### If devices still won't connect:

1. **Check Bluetooth adapter range** - Ensure devices are within range
2. **Check for interference** - Other Bluetooth devices may cause issues
3. **Restart Bluetooth** - Sometimes the adapter needs a reset
4. **Check device power** - Ensure devices are powered on
5. **Check logs** - Look for specific error messages

### Common Issues:

**"Connection backoff active"**
- Device has failed multiple times, waiting before retry
- Solution: Wait or reload the integration

**"BLE device not found"**
- Device is not in range or not advertising
- Solution: Move device closer or check if it's powered on

**"Connection slot error"**
- Bluetooth adapter has too many connections
- Solution: Reduce number of connected devices or upgrade adapter

## Performance Improvements

- **Faster connections**: Reduced timeouts mean quicker setup
- **Less resource usage**: Fewer retry attempts and better cleanup
- **Better reliability**: Exponential backoff prevents overwhelming devices
- **Improved stability**: Proper locking prevents race conditions

## Additional Notes

- The integration now uses direct `BleakClient` instead of `bleak_retry_connector` for better control
- Connection state is tracked per device, allowing independent management
- Devices remain "available" in Home Assistant even during temporary connection issues
- The integration will automatically recover from connection problems

## Next Steps

1. Test with your devices
2. Monitor logs for any issues
3. Report back with results
4. If issues persist, we can further tune the timeout values

## Configuration Options

If you need to adjust timeouts for your specific setup, edit `const.py`:

```python
# For slower devices, increase these:
CONNECTION_TIMEOUT = 10  # Increase to 15 if needed
INITIAL_CONNECTION_TIMEOUT = 15  # Increase to 20 if needed
RECONNECTION_TIMEOUT = 8  # Increase to 12 if needed

# For faster recovery, decrease these:
RETRY_DELAY = 1  # Keep at 1 second
MAX_CONNECTION_ATTEMPTS = 3  # Keep at 3
```

