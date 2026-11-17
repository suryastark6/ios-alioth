# alioth working notes

One entry per boot: what changed, what happened, what is next. Newest on top.
For the full history of the sweet bring-up this port is built on, see the
[ios-sweet NOTES.md](https://github.com/dipa-studio/ios-sweet/blob/main/NOTES.md).

## Test phone

| | |
| --- | --- |
| Variant | Mi 11X `aliothin` (M2012K11AI, hwc INDIA, hwversion 9.29.0) |
| RAM / storage | 8 GB (MemTotal 7828380 kB) / 128 GB UFS (sda 122601472 KiB) |
| Firmware | Evolution X, Android 14 (AP1A.240305.019.A1), not stock MIUI; slot `_b`, verifiedbootstate orange |
| Boot header version | boot v3 + vendor_boot v3 (3 DTBs in vendor_boot); `fastboot boot` of our header v3 image is accepted |
| Panel | **Aftermarket 60 Hz LCD** (replacement after a fall), not the original AMOLED. It reports itself as the original: ABL selects `qcom,mdss_dsi_k11a_38_08_0a_dsc_cmd` (command mode, DSC, 1080x2400 @120/60); `androidboot.oled_wp=000000000000` (no OLED white point). Android and the fastboot screen work on it. Display results from this phone may not hold for an original panel. |
| Touch | `focaltech,fts` on `spi@990000` (GENI), irq GPIO 39, reset GPIO 33, vcc_i2c L1C, vdd L10C |
| userdata | `/dev/block/sda35` (UFS LUN 0) |

## M0: hardware description

2026-11-17, from OrangeFox R12.0_1 (`fastboot boot`), `tools/alioth-backup.py`.
Everything matches the values taken from the device tree source except the
RAM banks: ABL splits the high memory at `0x180000000`, so the planned
`0x100000000` +3 GiB crossed a bank edge and the shim's RAM check would have
refused it. `high_phys_base` is now `0x180000000` (+3 GiB, inside the 4 GiB
bank, no reserved region above 4 GiB). `/proc/iomem` shows System RAM
continuous from `0xffc20000` to `0x27fffffff`; `0xffc00000` +128K is
`mailbox_region` (dynamic, no-map). The scan's low suggestion (`0xc0000000`)
is not usable: every dynamic pool can be placed below 4 GiB.

```

== Identity ==
model: Qualcomm Technologies, Inc. xiaomi alioth
compatible: qcom,kona-mtp, qcom,kona, qcom,mtp
panel selected by ABL: msm_drm.dsi_display0=qcom,mdss_dsi_k11a_38_08_0a_dsc_cmd:

== Memory (step 3: dram-base / dram-size) ==
  bank 0x80000000 size 0x3bb00000 (0.93 GiB)  [/memory]
  bank 0x180000000 size 0x100000000 (4.00 GiB)  [/memory]
  bank 0xc0000000 size 0xc0000000 (3.00 GiB)  [/memory]
  reserved-memory: 34 entries
        0x80000000 +0x600000     hyp_region@80000000 no-map
        0x80600000 +0x260000     xbl_aop_region@80700000 no-map
        0x80860000 +0x20000      reserved-memory@80860000 no-map
        0x80880000 +0x14000      res_xbl_uefi_log_region@80880000 no-map
        0x80900000 +0x200000     smem_region@80900000 no-map
        0x80b00000 +0x5300000    removed_region@80b00000 no-map
        0x86200000 +0x500000     pil_camera_region@86200000 no-map
        0x86700000 +0x100000     pil_wlan_fw_region@86700000 no-map
        0x86800000 +0x10000      pil_ipa_fw_region@86800000 no-map
        0x86810000 +0xa000       pil_ipa_gsi_region@86810000 no-map
        0x8681a000 +0x2000       pil_gpu_region@8681a000 no-map
        0x86900000 +0x500000     pil_npu_region@86900000 no-map
        0x86e00000 +0x500000     pil_video_region@86e00000 no-map
        0x87300000 +0x500000     pil_cvp_region@87300000 no-map
        0x87800000 +0x1400000    pil_cdsp_region@87800000 no-map
        0x88c00000 +0x2f00000    pil_slpi_region@88c00000 no-map
        0x8bb00000 +0x2500000    pil_adsp_region@8bb00000 no-map
        0x8e000000 +0x100000     pil_spss_region@8e000000 no-map
        0x8e100000 +0x4600000    cdsp_secure_heap@8e100000 no-map
           dynamic                adsp_region (size [0, 12582912], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                sdsp_region (size [0, 8388608], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                cdsp_region (size [0, 4194304], alloc-ranges [0, 0, 0, 4294967295])
        0x9c000000 +0x2300000    cont_splash_region@9c000000
        0xb0400000 +0x1000000    disp_rdump_region@9c000000 no-map
        0x9e300000 +0x100000     dfps_data_region@9e300000
           dynamic                mem_dump_region (size [0, 41943040], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                sp_region (size [0, 16777216], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                user_contig_region (size [0, 16777216], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                qseecom_region (size [0, 20971520], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                qseecom_ta_region (size [0, 16777216], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                secure_display_region (size [0, 171966464], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                cnss_wlan_region (size [0, 20971520], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                linux,cma (size [0, 33554432], alloc-ranges [0, 0, 0, 4294967295])
           dynamic                mailbox_region no-map (size [0, 131072], alloc-ranges [0, 0, 0, 4294967295])
  largest free ranges (16K aligned):
    0x180000000 size 0x100000000 (4096 MiB)
    0xc0000000 size 0xc0000000 (3072 MiB)
    0x9e400000 size 0x12000000 (288 MiB)
    0xb1400000 size 0xa700000 (167 MiB)
    0x92700000 size 0x9900000 (153 MiB)
  NOTE: dynamic pools (no reg) can land anywhere in their alloc-ranges; keep clear of them.

== Framebuffer (step 2: early console) ==
  /reserved-memory/cont_splash_region@9c000000: 0x9c000000 size 0x2300000
  panel qcom,mdss_dsi_k11a_38_08_0a_dsc_cmd: dsi_cmd_mode DSC 1080x2400@120, 1080x2400@60  <- selected by ABL
  dsi_cmd_mode = command-mode panel: needs a refresh kick (see docs/ALIOTH-PLAN.md, M2).

== Interrupt controller and timer (step 3) ==
  /soc/interrupt-controller@17a00000: 0x17a00000+0x10000, 0x17a60000+0x100000
  timer /soc/timer: PPIs [13, 14, 11, 12] -> INTIDs [29, 30, 27, 28] (order: secure phys, non-secure phys, virtual, hyp)
  clock-frequency 19200000

== CPUs (step 4) ==
  cpu@0: reg 0x0 qcom,kryo capacity [1024]
  cpu@100: reg 0x100 qcom,kryo capacity [1024]
  cpu@200: reg 0x200 qcom,kryo capacity [1024]
  cpu@300: reg 0x300 qcom,kryo capacity [1024]
  cpu@400: reg 0x400 qcom,kryo capacity [1894]
  cpu@500: reg 0x500 qcom,kryo capacity [1894]
  cpu@600: reg 0x600 qcom,kryo capacity [1894]
  cpu@700: reg 0x700 qcom,kryo capacity [1894]
  psci: method smc

== Storage, reset, USB (steps 1 and 5) ==
  imem restart_reason: 0x146bf65c (shim IMEM_RESTART_REASON)
  pshold /soc/restart@c264000: 0xc264000
  ufs /soc/ufshc@1d84000: 0x1d84000+0x3000
  ufs /soc/ufshc_card@1da4000: 0x1da4000+0x3000
  usb wrapper /soc/ssusb@a600000: 0xa600000
  dwc3 /soc/ssusb@a600000/dwc3@a600000: 0xa600000
  usb wrapper /soc/ssusb@a800000: 0xa800000
  dwc3 /soc/ssusb@a800000/dwc3@a800000: 0xa800000

== Touch (step 7) ==
  /soc/spi@990000/focaltech@0: focaltech,fts
    bus spi@990000 (qcom,spi-geni) reg ['0x990000'] status ok
    device reg [0] spi-max-frequency [6000000]
    focaltech,irq-gpio: /soc/pinctrl@f000000 [39, 8200]
    focaltech,reset-gpio: /soc/pinctrl@f000000 [33, 0]
    vcc_i2c-supply: /soc/rsc@18200000/rpmh-regulator-ldoc1/regulator-pm8150a-l1 []
    vdd-supply: /soc/rsc@18200000/rpmh-regulator-ldoc10/regulator-pm8150a-l10 []
  /soc/fingerprint_goodix: goodix,fingerprint
    bus soc (simple-bus) reg [] status None
    device reg [] spi-max-frequency []
    fp_vdd_vreg-supply: /soc/rsc@18200000/rpmh-regulator-ldoa13/regulator-pm8150-l13 []
    goodix,gpio-irq: /soc/pinctrl@f000000 [23, 0]
    goodix,gpio-reset: /soc/pinctrl@f000000 [24, 1]
  /soc/xiaomi_touch: xiaomi-touch
    bus soc (simple-bus) reg [] status None
    device reg [] spi-max-frequency []

== Buttons (step 7) ==
  /soc/qcom,spmi@c440000/qcom,pm8150@0/qcom,power-on@800: qcom,qpnp-power-on reg ['0x800', '0x100'] (PMIC SID 0)
    qcom,pon_1: linux,code 116 (POWER) pon-type KPDPWR (power)
    qcom,pon_2: linux,code 114 (VOLUMEDOWN) pon-type RESIN
  /soc/gpio_keys: gpio-keys reg []
    vol_up: linux,code 115 (VOLUMEUP) gpios /soc/qcom,spmi@c440000/qcom,pm8150@0/pinctrl@c000 [6, 1]

== Suggested tools/boards/alioth.py values (check each by hand) ==
    'phys_base': 0xc0000000,
    'mem_size': 0xc0000000,
    'high_phys_base': 0x180000000,
    'high_mem_size': 0x100000000,
    'fb': 0x9c000000,
    'fb_size': 0x2300000,
    'gicd': 0x17a00000,
    'gicd_size': 0x10000,
    'gicr': 0x17a60000,
    'gicr_size': 0x100000,
    'timebase': 19200000,
    'vtimer_intid': 27,
    'ufs': 0x1d84000,
    # MPIDRs: ['0x0', '0x100', '0x200', '0x300', '0x400', '0x500', '0x600', '0x700']
```

## Build log

### 2026-11-17  first session on the phone: backup, scan, RAM fix
- `tools/alioth-backup.py` hung in OrangeFox: `adb wait-for-device` only matches the Android state `device`, never `recovery`. It now polls `adb get-state` for `device` or `recovery`. Rerun: all partitions sha256 ok.
- RAM range moved to `0x180000000` +3 GiB (see M0). `out/alioth-m3-v3.img` (kernel `aebaed8`) still has `0x100000000` and needs a rebuild; WSL does not start on this PC (`HCS_E_SERVICE_NOT_AVAILABLE`, Virtual Machine Platform missing).

### 2026-11-17  refresh fallback, touch driver, kernel branch, QEMU
- **Kernel fallback for the command-mode panel** (0085): the shim passes `sweetkick=<CTL_START>` when autorefresh did not start (and `sweetfbpa=` when it moved the console). XNU's framebuffer console then kicks after lines (at most every 20 ms) and a thread call kicks at 30 Hz from `EARLY_BOOT`. Host-tested boot-args append.
- **Touch** (0086): `alioth_touch.c`, FT3658U on QUP0 SE4 GENI SPI; rails L1C 1.8 V and L10C 3.2 V through `sweet_rpmh.c` (alioth allowlist, cmd-db from the ADT). Host tests: protocol against a simulated IC (chip id, two fingers with sub-pixel decoding, lift, CRC error, busy status, out of range) and the FIFO engine against a GENI register model (1-71 byte reads, 16- and 4-word FIFOs). CI: compiles, only the style warnings sweet's files also have.
- **CI publishes the kernel** to the `kernel` branch (run 44033252467 onwards).
- **QEMU** with the alioth ADT and the CI kernel: stopped after "ATM subsystem is initialized" while sweet's ADT got further. Bisecting the ADT showed the cause: the boot CPU driver matches `qcom,kryo470`, and alioth's ADT said `qcom,kryo585`. Fixed in `tools/boards/alioth.py`; now identical progress to sweet (`skmem_region_init`, as far as QEMU gets).
- Images for the phone: `out/alioth-m1-v3.img`, `out/alioth-m3-v3.img` (kernel `aebaed8`).

### 2026-11-17  pre-flight review before the first session on the phone
Problems found by reading the code and sources, and fixed before any boot:
- **Boot image format.** alioth is Virtual A/B with `vendor_boot` (header v3). A v3 image puts the vendor ramdisk *before* ours, so the payload was no longer at `initrd-start`. The loader now searches for it and realigns it. `HEADER=3` builds a v3 image; `unpack_vendor_boot.py` gets the stock DTB for v2. Host-tested with payloads at offsets 0, 8, 13, 4096, 12345 and 1000003.
- **sweet drivers that would have run on alioth** (patch 0084): touch init votes LDO11C to 3.2 V (a different rail on alioth) and drives sweet's TLMM at `0x03900000`; the USB probe programs sweet's QUSB2 PHY. Both are skipped when the ADT says `xiaomi,alioth`. `userdata` is also searched on LUNs 1-3.
- **Display check.** `INTF_FRAME_COUNT` is a video-mode counter and would not show autorefresh working on a command-mode panel. Detection now uses the pingpong write pointer, as Xiaomi's driver does, and autorefresh is switched off again before falling back to kicks. Simulated under qemu-aarch64 with a fake register block: autorefresh works / idle / scanout from another buffer.
- **RAM.** 3 GiB at `0x100000000` (fits 6 GB and 8 GB phones) and the shim refuses to start XNU unless that range is inside ABL's live memory node and clear of every reserved region. Host-tested on alioth's source tree with 6 GB- and 8 GB-like memory nodes. sweet's old low choice (`0xb0000000`) is correctly rejected: it overlaps `disp_rdump_region`.
- **Screen text.** `con_hex2` prints 32-bit values; addresses above 4 GiB now use `con_hex`. All new strings fit the 37 columns after the label (rendered on the host).
- Windows: `tools/alioth-backup.py` (tested against a fake adb, including a corrupted transfer) and `docs/FIRST-BOOT.md`.

### 2026-11-16  kernel CI back on GitHub-hosted runners
- The `macos-14` image (the last with Xcode 15) was retired by GitHub on 2026-11-02; the xnu job was cancelled with "configuration 'macos-14-arm64-us-default' is not supported".
- Moved to `macos-15` (Xcode 16.2 selected). Xcode 16's iig needs `IORPC.kernelContent`: patch 0083 adds it.
- Run 43829221926: all patches 0001-0083 applied, no compile errors, `kernel.development.sweet` 17,205,096 bytes. Artifact `xnu-kernel`.
- **Not boot-tested.** This is the first kernel from Xcode 16 for this tree; the last known-good phone kernel (sweet, 0069-0081) was built with Xcode 15. If an early boot regresses, the compiler change is a suspect.
- Includes 0082 (alioth volume-up from the ADT).

### 2026-11-16  values from alioth's device tree source
- Built alioth's tree from LineageOS `android_kernel_xiaomi_sm8250` (kona-v2.1 + alioth overlay) and ran `fdt-scan.py` on it. Results in `docs/ALIOTH-HARDWARE.md`.
- Differences from sweet that would have broken the first boot: virtual timer INTID 27 (not 19), command-mode DSC panel, `disp_rdump_region` at `0xb0400000` (sweet's low RAM base), touch on SPI (FT3658U), volume-up on PM8150 GPIO6.

## Boot log

### 2026-11-17  boot 02: M1 shim probe, repeated
- Image: `out/alioth-m1-v3.img` (same as boot 01), `fastboot boot` at 20:03:14.
- Changed: nothing; this time with photos and a USB watcher, no buttons pressed.
- Result: the panel showed no picture from the shim: backlight only (the LCD glows blue-grey on a black frame) and a thin white line along the top edge. The phone came back **in Android** (MTP) at 20:07:08 by itself.
- Reading:
  - **The shim ran to the end.** 20:03:14 + 180 s wait + 20 s reset delay = 20:06:34, plus ~35 s of Android boot = 20:07:08. A fault would have reset after 40 s (Android by ~20:05), and a hang would not have reset at all.
  - **The reset ignores our "reboot to bootloader" flag.** The shim writes `0x77665500` to IMEM `restart_reason` only. On this phone the PM8150 PON node has `qcom,store-hard-reset-reason`, so ABL takes the reason from the PMIC (PON `SOFT_RB_SPARE`, written over SPMI by Linux's `qpnp_pon_set_restart_reason`). Until the shim writes it too, hold Volume Down when the reset is due to land in fastboot.
  - **Display:** the first frame request after ABL's splash leaves the replacement LCD black (boot 01: "many colours", then dark; Android's screen stayed dark after the warm reset until a full power cycle). The shim enables autorefresh and/or writes `CTL_START`; one of those, or the frame it sends, is not something this panel's bridge accepts. No register values could be read, since the screen is the only output.
- Next: images that change one thing at a time (no autorefresh / kicks only / no writes at all) to find which write blanks the panel; a second output channel that does not depend on the display; PMIC reboot reason in the shim.

### 2026-11-17  boot 01: M1 shim probe
- Image: `out/alioth-m1-v3.img` (sha256 `08568eeb...`, header v3, no payload), `fastboot boot` from slot `_b`.
- Changed: first run of our code on alioth.
- Result: ABL accepted the v3 image (no Load Error). The screen showed many colours instead of the red console screen, then went dark; no photo. The phone was later found in Android (MTP) with a dark screen. Power + Volume Down reached fastboot; `fastboot reboot` back to Android with a working screen.
- Next: repeat with photos (boot 02).

<!--
### YYYY-MM-DD  boot NN: <short title>
- Image: shim/out/...  kernel ...  ADT ...  boot-args ...
- Changed: (one thing)
- Result:
- Next:
-->
