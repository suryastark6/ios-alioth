# Porting plan: iOS 16 on alioth (POCO F3 / Redmi K40 / Mi 11X)

Starting point: [ios-sweet](https://github.com/dipa-studio/ios-sweet) (Redmi Note 10 Pro, SM7150), which boots the iPhone X iOS 16.7.16 userland to the home screen. This repository carries that work and adds what alioth needs.

alioth has a **Snapdragon 870 (SM8250-AC)**. That is a different chip from sweet's 732G, but it is built from the same blocks: GICv3, RPMh, QUP/GENI serial engines, a UFS host, DWC3 USB and a 19.2 MHz timer. Many of the addresses match. The work is in the board layer: memory map, display, touch, buttons, power rails.

Rule for every milestone: **change one thing per boot, and write every boot down in [NOTES.md](../NOTES.md).**

## What carries over and what changes

| Piece | sweet | alioth | Effort |
| --- | --- | --- | --- |
| iOS root image (`mkiosroot.sh`, `sweet-root-tweaks.py`) | iPhone X 16.7.16 | same image | none |
| Kernel CI (`.github/workflows/xnu.yml`) | `MACHINE_CONFIG=SWEET` | same | none |
| Generic kernel patches (toolchain, HFS+, AMFI, sandbox, HID, IOSurface, diagnostics) | yes | same | none |
| GIC | `0x17a00000` / `0x17a60000` | same on SM8250 (verify) | check |
| UFS host | `ufshc@1d84000` | same on SM8250 (verify) | check |
| PS_HOLD reset | `0x0c264000` | same on SM8250 (verify) | check |
| IMEM restart reason | `0x146aa65c` | likely `0x146bf65c` (verify) | small |
| RAM map | upper bank `0x100000000 + 0xfcc00000` | 6 or 8 GiB, different carve-outs | **must measure** |
| CPUs | 6x A55 + 2x A76 | 4x A55 + 3x A77 + 1x A77 prime; ARMv8.2, 16K pages OK | small |
| Framebuffer | `0x9c000000`, video-mode panel | splash region size differs; Samsung AMOLED with DSC, probably **command mode** | **medium-large** |
| Touch | Goodix GT9896, I²C on GENI SE7, LDO11 via RPMh | on **SPI** (see the postmarketOS alioth notes); chip and rail from the DT | **large** (new driver) |
| Buttons | PM6150 PON + PM6150L GPIO2 | PM8150 PON + a PM8150-family GPIO | small |
| Battery | static IOPMPowerSource | same static stand-in first | none |
| USB live log (0072-0077, 0081) | DWC3 `0xa600000`, QUSB2 PHY | DWC3 at the same address; different HS PHY | medium |
| Boot image | header v2 | probably header v3 + `vendor_boot` | **M1 risk** |

## Kernel patches that touch board details

Everything else in `xnu/patches/` runs unchanged.

| Patch | What is board-specific | alioth action |
| --- | --- | --- |
| 0010, 0012 | Early framebuffer at `0x9c000000`, 1080 px wide (stride 4320) | Unchanged if the alioth splash is also at `0x9c000000` and 1080 wide; otherwise make the address come from the ADT |
| 0028-0034 | UFS host driver (address from ADT) | Should work: same Qualcomm UFS v3 host family. 0034 (DMA above 4 GiB) matters with the high bank |
| 0046, 0056 | CPU copy into the ABL framebuffer | Command-mode panel: add a "kick" after each copy (M2) |
| 0060 | SPMI keys (PON SID0, PM6150L GPIO2 SID4); touch over GENI I²C | Keys: new PON/GPIO bits for PM8150. Touch: replaced by an SPI driver (M7) |
| 0062 | RPMh vote for LDO11C (touch rail); battery | New rail name from the DT (M7) |
| 0063 | Goodix GT9896 protocol | Replaced by alioth's touch IC protocol (M7) |
| 0065, 0078 | SMP via PSCI, MPIDR order | Check MPIDRs; A77 cores need no changes (M4) |
| 0071 | Edge touches for the home gesture | Same logic, new panel coordinates |
| 0072-0077, 0081 | DWC3 device mode, QSCRATCH VBUS override | Same DWC3/QSCRATCH addresses; check the PHY state ABL leaves (M8) |
| 0079 | Display power via the panel's continuous splash | Command mode: send DSI display off/on, or skip at first |

## Milestones

### M0. Back up and collect the hardware description

1. Unlock the bootloader (Mi Unlock). Install the latest stock MIUI/HyperOS firmware for your variant first, and write down the variant: global, Indian `aliothin`, or Chinese K40.
2. Boot OrangeFox/TWRP temporarily: `fastboot boot recovery.img`.
3. `tools/alioth-backup.sh` saves `persist`, `modemst1/2`, `fsg`, `fsc`, `boot`, `dtbo`, `vbmeta`, `vendor_boot` and pulls the live device tree to `dtb/alioth-live.dtb`. **Copy `backup/` somewhere safe and keep it out of git.**
4. `python3 tools/fdt-scan.py dtb/alioth-live.dtb` prints the memory banks and carve-outs, the splash region, the panel mode, GIC, timer, CPUs, UFS, IMEM, the touch node and its bus, and the buttons.
5. Get Xiaomi's kernel source for alioth (MiCode `Xiaomi_Kernel_OpenSource`, branch `alioth-*`). It has the touch driver and the panel's DSI command sequences.

**Done when** `fdt-scan.py` output is saved in `NOTES.md` and every `VERIFY` line in `tools/boards/alioth.py` and `shim/board.h` is confirmed or corrected.

### M1. Own code runs

1. Check the stock boot header version (`unpack_bootv2.py` stops on v3+). If ABL accepts a v2 image through `fastboot boot`, use `shim/build.sh` as-is with `BOARD=alioth DTB=dtb/boot_unpacked/dtb`. If it does not, there are two fallbacks: build a v3 image whose DTB comes from `vendor_boot`, or hide the payload inside the kernel image (the Redmi Note 12 port had to do this).
2. Find out whether ABL leaves a watchdog running. The shim should print and stay alive for at least 60 s.
3. Test reboot-to-bootloader from the shim (IMEM restart reason + PS_HOLD). This becomes your escape hatch.

**Done when** the shim draws its diagnostics screen and can return to fastboot by itself.

### M2. Picture and log

1. Fill `fb`, `fb_size`, `fb_w`, `fb_h` in `tools/boards/alioth.py` from the splash region.
2. If the panel is `dsi_cmd_mode` (the ABL `dsi_display0` name ends in `_cmd`), pixels only appear after a frame is triggered. Implement a minimal kick in the shim first: flush and start the DPU control path ABL configured for continuous splash. Use Linux `drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c` (SM8250 DPU) as the reference. The Pixel 4 port solved this on the very similar SM8150. Move the same kick into the kernel's framebuffer copy (0046/0056) afterwards.
3. The log: the persistent ring at the end of `userdata` (0047, `tools/sweet-log-pull.sh`) needs no changes beyond the UFS LUN check.

**Done when** shim text is visible on the panel and a kernel log can be pulled from recovery.

### M3. XNU starts

1. Fill the memory fields from `fdt-scan.py`. Prefer one large range above 4 GiB that no carve-out touches (as sweet's `--highmem` does). Keep clear of the dynamic pools' alloc-ranges.
2. `python3 tools/mkadt.py shim/out/alioth.adt --board alioth --highmem`, then `mkpayload.py` and `BOARD=alioth shim/build.sh` (README steps 3-4), with `cpus=1` first.
3. Use the sweet kernel unchanged for this boot. If 0010/0012's framebuffer address is wrong for alioth, the early console stays blank until that is fixed.

**Done when** the kernel log reaches "waiting for root device" (or further).

### M4. All cores

`cpus=4` (the A55s), then `cpus=8`. Check the MPIDRs against `fdt-scan.py`. If secondaries hang, compare the GIC redistributor wake-up in 0065 with the alioth DT.

### M5. Storage and root

1. Build the iOS root image exactly as in the sweet README, step 2. The image does not depend on the phone.
2. alioth's `userdata` is much larger than 16 GiB, so the same image fits. Check the UFS LUN and partition index (`sda34` on sweet; probably different on alioth) in the log-pull script and in the kernel's root lookup.
3. `fastboot -S 512M flash userdata ios16-root.simg`, then boot with `rd=ufsroot0 ufsrw=1 rootrw=1`.

**Done when** launchd starts and the Apple logo appears.

### M6. Lock screen

This should need no alioth-specific work: ios-sweet's root tweaks and kernel stand-ins already get SpringBoard up. The panel size the kernel presents stays 1125x2436 (0061). The panel is also 1080x2400, so the centered presentation matches sweet's.

### M7. Touch and buttons

1. Read the touch node `fdt-scan.py` found: chip compatible, SPI controller (QUP SE index), chip select, IRQ and reset GPIOs, and supplies.
2. Write `bsd/dev/alioth_touch.c` on the GENI SPI engine, with the same `sweet_hid_touch(finger, down, x, y)` output as the Goodix driver. Port the chip protocol from Xiaomi's Linux driver.
3. Power: RPMh vote for the touch rail (reuse `sweet_rpmh.c` from 0062, new resource name).
4. Buttons: PM8150 PON (power, RESIN = volume down) and the volume-up GPIO, in `sweet_keys.c`.
5. Edge touches (0071) with alioth's coordinate range.

**Done when** you can unlock, open Settings and swipe home.

### M8. Nice to have

USB live log and SSH (0072-0077), real battery level (PM8150B fuel gauge), display power off/on for a command-mode panel. GPU (Adreno 650) and Wi-Fi (QCA6390) are separate projects.

## Risks to settle early

- **Boot image format (M1).** Everything waits on ABL accepting our image.
- **Command-mode panel (M2).** Without a kick you see nothing. The same problem would freeze the GUI later.
- **Touch on SPI (M7).** ios-sweet has no SPI driver yet. This is the largest new piece of code.
- **RAM variants.** 6 GB and 8 GB phones have different memory nodes. Record which one each board file was measured on.

## Contributing

Open an issue or PR with your variant, the milestone you reached, the `fdt-scan.py` output (strip serial numbers) and the relevant boot log lines. Never commit partition backups, live device trees, or any Apple firmware or root images.
