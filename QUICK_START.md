# Quick Start - Bluetooth Connection Fixes

## What Was Fixed

Your Govee BLE lights were timing out because:
1. Connection timeout was too long (30s → 10s)
2. Devices were marked as non-connectable (fixed!)
3. No proper retry logic with backoff
4. Poor error handling causing devices to become unavailable

## How to Apply the Fixes

### Step 1: Restart Home Assistant
```
Settings > System > Restart Home Assistant
```

### Step 2: Watch the Logs
```
Settings > System > Logs
Filter by: "govee_light_ble"
```

### Step 3: Expected Behavior

**Good Connection:**
```
✓ Successfully connected to [address] on attempt 1
```

**Retry (Normal):**
```
⚠ Connection timeout for [address], attempt 1
✓ Successfully connected to [address] on attempt 2
```

**Device Unavailable (Will Retry):**
```
✗ Failed to connect after 3 attempts (failure count: 1)
ℹ Will retry with exponential backoff
```

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Device won't connect | Check if device is powered on and in range |
| Connection timeout | Normal for first attempt, should succeed on retry |
| "Connection backoff active" | Device failed multiple times, wait 30s or reload integration |
| Device shows unavailable | Reload the integration: Settings > Devices > [device] > Reload |

## Key Improvements

✅ **Faster connections** - 10s timeout instead of 30s  
✅ **Smart retries** - Exponential backoff prevents hammering devices  
✅ **Better recovery** - Devices stay available during temporary issues  
✅ **Proper cleanup** - Fresh connection attempts every time  
✅ **Fixed connectable flag** - Critical bug fix!  

## Testing Your Devices

1. **Turn on your Govee lights**
2. **Restart Home Assistant**
3. **Check logs** - Should see "Successfully connected" messages
4. **Test control** - Turn lights on/off, change colors
5. **Check reliability** - Should work consistently now

## If Issues Persist

1. Check Bluetooth adapter range
2. Reduce number of connected BLE devices
3. Check for Bluetooth interference
4. Consider upgrading Bluetooth adapter if using built-in

## Files Changed

- `const.py` - Updated timeout values
- `api.py` - Complete connection rewrite
- `coordinator.py` - Better error handling
- `__init__.py` - Fixed connectable flag

## Need Help?

Check `BLUETOOTH_CONNECTION_FIXES.md` for detailed technical information.

