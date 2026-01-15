# Raspberry Pi OS Selection Guide

## Recommended: Raspberry Pi OS Lite (Legacy) - 32-bit

**Why this one?**
- ✅ Includes Python 2.7 (required for `server_py2.py`)
- ✅ 32-bit (compatible with Pi 3)
- ✅ Lightweight (no desktop, perfect for headless server)
- ✅ Still maintained and secure
- ✅ Small download size

**How to find it in Raspberry Pi Imager:**
1. Open Raspberry Pi Imager
2. Click "Choose OS"
3. Scroll down to "Raspberry Pi OS (other)"
4. Select **"Raspberry Pi OS Lite (Legacy)"**
   - This is the 32-bit version
   - Released around 2022-2023
   - Last version with Python 2.7

## Alternative Options

### Option 2: Raspberry Pi OS (Legacy) - 32-bit with Desktop
- ✅ Includes Python 2.7
- ✅ Has desktop GUI (if you want to use Pi directly)
- ❌ Larger download (~1.5GB vs ~400MB)
- ❌ Uses more resources

**When to use:** If you want to use the Pi with a monitor/keyboard sometimes

### Option 3: Migrate to Python 3 (Advanced)
- ✅ Use latest Raspberry Pi OS (64-bit or 32-bit)
- ✅ Modern Python 3 support
- ❌ Requires updating `server_py2.py` to Python 3
- ❌ More work upfront

**When to use:** If you want to future-proof and don't mind updating code

## Step-by-Step: Selecting OS in Imager

1. **Download Raspberry Pi Imager** from https://www.raspberrypi.com/software/
2. **Open Imager** and click "Choose OS"
3. **Scroll down** past the main options
4. **Click "Raspberry Pi OS (other)"**
5. **Select "Raspberry Pi OS Lite (Legacy)"**
   - Look for the one that says "(Legacy)" and "Lite"
   - Should show "32-bit" in description
6. **Click "Choose Storage"** and select your SD card
7. **Click the gear icon** (⚙️) to configure:
   - ✅ Enable SSH
   - Set username (default: `pi`)
   - Set password
   - Set hostname (optional: `bubblebot`)
   - Configure WiFi (if using WiFi instead of Ethernet)
8. **Click "Write"** and wait for it to finish
9. **Insert SD card** into Pi and boot

## Verification After Boot

Once Pi boots, verify Python 2 is available:

```bash
ssh pi@192.168.2.108
python --version
# Should show: Python 2.7.x

python -c "import RPi.GPIO; print('GPIO works')"
# Should work without errors
```

## Why Legacy?

Raspberry Pi OS Legacy is the last version that includes Python 2.7 by default. Newer versions (2024+) only include Python 3. Since your server code (`server_py2.py`) uses Python 2 syntax, Legacy is the easiest path.

## Future Migration Path

If you want to use newer OS later, you can:
1. Update `server_py2.py` to Python 3 syntax
2. Use Python 3 libraries (mido instead of pygame.midi)
3. Install latest Raspberry Pi OS

But for now, **Raspberry Pi OS Lite (Legacy) is the best choice** for a quick, working setup.
