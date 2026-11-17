# First session on the phone (Windows)

Milestones M0 to M2 from [ALIOTH-PLAN.md](ALIOTH-PLAN.md): back up the phone, read its device tree, and check that our code runs and can draw on the screen. **Nothing is flashed.** Every boot below is temporary (`fastboot boot`), and `fastboot reboot` always returns to your normal Android.

Time: about 30-45 minutes.

## What you need

- **An unlocked bootloader.** Check it in step 1. If it is still locked, Xiaomi's Mi Unlock tool makes you wait (often 7 days), so nothing else here can be done tonight.
- **[Android platform-tools](https://developer.android.com/tools/releases/platform-tools)** (adb and fastboot), unzipped, e.g. to `C:\platform-tools`.
- **Python 3** for Windows ([python.org](https://www.python.org/downloads/windows/)); tick "Add python.exe to PATH" when installing.
- **OrangeFox recovery for alioth** (from the official OrangeFox site), as a `.img` file. It is only booted, never installed.
- A good USB cable, preferably on a USB port directly on the PC.
- The repository folder: `Desktop\alioth\ios-alioth`. Open a Command Prompt there:

```bat
cd %USERPROFILE%\OneDrive\Desktop\alioth\ios-alioth
set PATH=C:\platform-tools;%PATH%
```

## 1. Check the bootloader

Power the phone off, then hold **Volume Down + Power** until "FASTBOOT" appears. Connect USB.

```bat
fastboot devices
fastboot getvar unlocked
fastboot getvar product
fastboot getvar current-slot
```

`unlocked: yes` and `product: alioth` are required. If `fastboot devices` shows nothing, install the USB driver (Windows Update usually offers it; otherwise the Google USB driver from Android Studio's SDK manager).

## 2. Back up and read the hardware (M0)

```bat
fastboot boot C:\path\to\OrangeFox-alioth.img
```

Wait until OrangeFox shows its home screen. If it asks for a PIN or pattern to decrypt, you can cancel: the backup does not need your data.

```bat
python tools\alioth-backup.py --adb C:\platform-tools\adb.exe
```

This reads (never writes) the phone's own partitions and saves them in `backup\`. It saves the device tree and a scan in `dtb\`. Every partition is checked with sha256. **Copy `backup\` to a second place** (another drive or cloud): `persist` and the modem partitions hold the phone's calibration and IMEI, and no download has them.

Then tell me "backup done". I can read `dtb\` from here and will check the values.

```bat
adb reboot bootloader
```

## 3. First boot of our code (M1, M2)

The test image is `Desktop\alioth\out\alioth-m1-v3.img`. It contains no iOS and no XNU. It only shows what it finds and tests the display.

```bat
fastboot boot ..\out\alioth-m1-v3.img
```

**What should happen:** within a few seconds the screen turns red with white text, about 20 lines: `SHIM`, `BOARD alioth`, `DISP ...`, `CTL ...`, `PP ...`, `SSPP ...`, `LOADER no SWEETXNU payload`, then `UFS ...` lines (a read-only test of the storage). About 3 minutes later the phone **restarts into fastboot by itself**.

**Please take clear photos of the screen**, one when the red screen appears and one just before it restarts, and put them in `Desktop\alioth\photos\`. Every number on that screen helps.

What other outcomes mean:

| You see | Meaning | Next |
| --- | --- | --- |
| Red screen with text | M1 and M2 done | photos, then step 4 |
| `fastboot` prints `FAILED (remote: ... Load Error ...)` | ABL refused a header v3 image | tell me; I build a v2 image with your phone's DTB from the backup |
| Fastboot screen or boot logo stays, phone returns to fastboot after 3-4 minutes | our code ran, but no picture: the panel did not take our frames | tell me; the probe still worked, next image tries the other display path |
| Black or frozen screen for more than 5 minutes | stuck | hold **Power + Volume Down** for ~15 s until the phone restarts, keep holding Volume Down to land in fastboot. Tell me what you saw |

Nothing is written to the phone in any of these cases.

## 4. Optional: start XNU (M3)

Only if step 3 showed the red screen with text. `Desktop\alioth\out\alioth-m3-v3.img` is the same shim with the XNU kernel (from the `kernel` branch, see `out\BUILD.txt`), one CPU, and no root file system.

```bat
fastboot boot ..\out\alioth-m3-v3.img
```

**What should happen:** the red shim screen, now with `RAM ok: in a memory bank, not reserved`, then the screen fills with white-on-black kernel log text that keeps scrolling. Success is the log ending in `waiting for root device` (there is no iOS on the phone yet). Take a photo every ~20 seconds, and one of the last screen.

| You see | Meaning |
| --- | --- |
| `RAM NOT inside a /memory bank` or `RSVD ...` and it stops | the 3 GiB RAM range does not fit this phone: photo, I adjust it |
| `KICK ...` line on the red screen | autorefresh did not work, the kernel sends frames itself (expected to still show the log) |
| red screen, then nothing changes for 2+ minutes | XNU started but its console is not visible, or it hung early: hold Power + Volume Down |
| a panic text | photo of the whole screen |

Then Power + Volume Down to get back to fastboot.

## 5. Back to Android

```bat
fastboot reboot
```

## After tonight

With the photos and `dtb\`, I check the display and RAM values and build the next images. New kernels are published to the repository's `kernel` branch by every successful CI run, so nothing needs to be downloaded by hand.
