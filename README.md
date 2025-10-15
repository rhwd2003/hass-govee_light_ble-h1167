# Govee Bluetooth Lights Integration with H1167 Music Box Support 🏠🎵

[![GitHub Release](https://img.shields.io/github/v/release/rhwd2003/hass-govee_light_ble-h1167?sort=semver&style=for-the-badge&color=green)](https://github.com/rhwd2003/hass-govee_light_ble-h1167/releases/)
[![GitHub Release Date](https://img.shields.io/github/release-date/rhwd2003/hass-govee_light_ble-h1167?style=for-the-badge&color=green)](https://github.com/rhwd2003/hass-govee_light_ble-h1167/releases/)
[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Overview

**Enhanced version of the Govee Bluetooth Lights integration with full H1167 Music Box support!**

This integration allows you to integrate your Govee Bluetooth lights (without the cloud!) with your Home Assistant setup, including **complete support for the H1167 Music Box** with all its advanced lighting show modes.

### ✨ **New H1167 Features:**
- **24+ Music & Lighting Effects**: Rhythm, Beat, Spectrum, Waves, Brilliant, Pulsate, Dynamic, Calm, and more!
- **Enhanced Connection Handling**: Improved BLE connection stability and retry logic
- **Smart Device Detection**: Automatic H1167 detection and feature enablement
- **Full Home Assistant Integration**: All effects available as light effects in the UI

### 🎵 **Supported H1167 Modes:**
- **Music Reactive**: Rhythm, Sprouting, Shiny, Beat, Waves, Spectrum, Rolling, Hopping, Starlight, Piano Keys, Jumping, Luminous
- **Carnival Effects**: Brilliant, Pulsate, Dazzle, Fascination, Aspiring, Cadence, Revel, Fluctuate, Funny, Shimmer  
- **Basic Modes**: Dynamic, Calm

### 📱 **Standard Features:**
- Power control (on/off)
- Brightness adjustment (0-255)
- RGB color control
- Real-time state synchronization

## Installation

### HACS (recommended)

This integration is available in HACS (Home Assistant Community Store).

1. Install HACS if you don't have it already
2. Open HACS in Home Assistant
3. Go to any of the sections (integrations, frontend, automation).
4. Click on the 3 dots in the top right corner.
5. Select "Custom repositories"
6. Add following URL to the repository `https://github.com/rhwd2003/hass-govee_light_ble-h1167`.
7. Select Integration as category.
8. Click the "ADD" button
9. Search for "Govee Bluetooth Lights"
10. Click the "Download" button

### Manual

To install this integration manually you have to download [_govee_light_ble.zip_](https://github.com/rhwd2003/hass-govee_light_ble-h1167/releases/latest/) and extract its contents to `config/custom_components/govee_light_ble` directory:

```bash
mkdir -p custom_components/govee_light_ble
cd custom_components/govee_light_ble
wget https://github.com/rhwd2003/hass-govee_light_ble-h1167/releases/latest/download/govee_light_ble.zip
unzip govee_light_ble.zip
rm govee_light_ble.zip
```

## Configuration

### Using UI

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=govee_light_ble)

From the Home Assistant front page go to `Configuration` and then select `Devices & Services` from the list.
Use the `Add Integration` button in the bottom right to add a new integration called `Govee Bluetooth Lights`.

### H1167 Music Box Setup

1. **Put H1167 in pairing mode**: Remove from Govee app or reset the device
2. **Device should appear as**: "H1167_XXXX" (where XXXX are the last 4 characters of MAC address)
3. **Configuration options**:
   - **Segmented**: Set to `True` for H1167 (recommended)
   - **Music Mode Support**: Will auto-detect for H1167 devices
4. **Effects**: Once configured, all 24+ lighting effects will be available in the light entity's effect dropdown

### Troubleshooting H1167

- **Connection Issues**: The integration includes enhanced retry logic for BLE connection slot errors
- **Device Not Found**: Ensure H1167 is in pairing mode and visible in Govee app
- **Effects Not Working**: Verify "Music Mode Support" is enabled in device configuration

## Help and Contribution

If you find a problem, feel free to report it and I will do my best to help you.
If you have something to contribute, your help is greatly appreciated!
If you want to add a new feature, add a pull request first so we can discuss the details.

## Disclaimer

This custom integration is not officially endorsed or supported by Govee.
Use it at your own risk and ensure that you comply with all relevant terms of service and privacy policies.
