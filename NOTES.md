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
| Panel | **Aftermarket 60 Hz LCD** (replacement after a fall), not the original AMOLED. It reports itself as the original: ABL selects `qcom,mdss_dsi_k11a_38_08_0a_dsc_cmd` (command mode, DSC, 1080x2400 @120/60); `androidboot.oled_wp=000000000000` (no OLED white point). Android and the fastboot screen work on it. After ABL the splash path scans the buffer by itself (like video mode) and a `CTL_START` kick blanks it (boot 03). Display results from this phone may not hold for an original panel. |
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

### 2026-11-19  M5 preparation (nothing flashed)
- WSL works again (Virtual Machine Platform enabled). Ubuntu 24.04 has no `apfs-fuse` package: built from `sgan81/apfs-fuse` (`66b86bd`) with its `lzfse` submodule (the `lzfse` tool also decodes the DeviceTree im4p).
- `research/ipsw-x/d22ap.adt` from the 16.7.16 (20H392) IPSW's `DeviceTree.d22ap.im4p` (`EmbeddedDeviceTrees-7153.140.37.700.2`, 61 `/product` properties), fetched with `tools/remotezip.py`.
- `tools/build-alioth-win.py m5`: M5 boot-args as `tools/build-alioth.sh`. `out/new/alioth-m5-v3-cpus4.img` (`04a51c41...`, ADT with `/product`). Not booted: needs the iOS root on userdata.
- The IPSW download (5.75 GiB, sha256 `ece1194f...`, verified) was slow on this connection; WSL's network was ~20x slower than Windows', so the rest was fetched from Windows in ranges.
- WSL's kernel has no HFS+ (`# CONFIG_HFSPLUS_FS is not set`): built `hfsplus.ko` from Microsoft's `linux-msft-wsl-6.6.87.2` with the running config (vermagic matches) and loaded it with `insmod` (gone after a WSL restart).
- `tools/mkiosroot.sh` with OS `087-86698-044.dmg` (UDIF), SystemOS `087-86593-047.dmg`, AppOS `087-86715-047.dmg`: 12 GiB used of 16 GiB, 19 cryptex files linked, fsck OK. `tools/sweet-root-tweaks.py`: all changes applied except "no mobileactivationd system container in the image; skipped data ark" (activation comes from the ADT `/chosen` properties). `ios16-root.simg` (12.1 GB, sha256 `5759d761...`) in WSL `~/ios-build`, not in the repository. Not flashed.

### 2026-11-17  Windows build, display test images, PMIC reboot reason
- `tools/build-alioth-win.py`: builds the M1/M3 images on Windows without WSL (Arm GNU Toolchain 14.2.Rel1 `aarch64-none-elf`, AOSP `mkbootimg.py`), same flags, link and layout as `shim/build.sh`. Headers match the Linux-built images; the M3 payload differs only in the RAM range and the random seed.
- `--disp full|none|kick` (`DISP_TEST`) to find the display write that blanks the replacement LCD (answer: `CTL_START`, boot 03).
- After boot 03: `disp_init` wrote nothing only when INTF_1's frame counter moved (boot 04: it does not, screen blank). After boot 04: it writes nothing whenever no pingpong is in tear-check mode, and then there is no `sweetkick=` either; the counter is printed twice, 100 ms apart. An original AMOLED with no tear-check pingpong would now get no kicks: untested, no such phone. `out/new/alioth-m1-v3.img` (`4dedef42...`), `alioth-m3-v3.img` (`63c13d55...`, kernel `aebaed8`). Not booted yet.
- The shim's reset writes the PMIC reboot reason (PM8150 PON `SOFT_RB_SPARE`, SPMI arbiter v5) before the IMEM one: works (boot 03).

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

### 2026-11-20  boot 14: M5 with Wi-Fi/Bluetooth ADT nodes: lock screen
- Image: `out/new/alioth-m5-v3-cpus4-noconsole-wlan.img` (sha256 `b7b74fe1...`): boot 13's image plus the `radio_nodes` ADT fix. Power-off from OrangeFox (`adb shell reboot -p`), cold start with Volume Down + Power, `fastboot boot` by `run-wlan.sh`.
- **Result: the iOS 16 lock screen.** The wallpaper, the clock ("Wednesday, December 31", 4:03: the RTC is not read, so the clock starts at the epoch in local time), the charging battery icon, the camera button and the home indicator are all shown (`photos/boot14-m5-lockscreen.jpg`). MobileGestalt gets its Wi-Fi address, so LaunchServices seeding finishes and SpringBoard comes up.
- Touch does not respond: expected, the FT3658U long reads still fail the CRC check (err=94, boots 10-11).
- Next: fix the touch reads (kernel change, needs a CI kernel build). Later: RTC/time, the bluetoothd and fairplayd crash loops.

### 2026-11-19  boot 13: M5, logging lsd's IOKit calls
- Image: `out/new/alioth-m5-v3-cpus4-noconsole-iolsd.img` (sha256 `a3c7bc91...`): boot 12 + `sweetiolog=lsd,backboardd`. Cold start, `fastboot boot` at 18:51:33, Apple logo, Power + Volume Down 18:58, log `logs/boot13-m5.txt`.
- **Cause found.** lsd (MobileGestalt inside it) asks again and again:
  ```
  IOK lsd: matching1 <IONameMatch sdio> -> none
  IOK lsd: matching1 <IONameMatch wlan> -> none
  IOK lsd: matching1 <IONameMatch marconi-wifi> -> none
  IOK lsd: IOServiceMatched <IOProviderClass IONetworkController> -> notify
  ```
  MobileGestalt's Wi-Fi address: no `wlan` device, so it waits for a network controller that never comes; the install session ID, the LaunchServices seeding and SpringBoard all wait behind it.
- Fix (`tools/mkadt.py radio_nodes`, `'radio_nodes': True` in `tools/boards/alioth.py`): `/arm-io/wlan` and `/arm-io/bluetooth` nodes with synthetic locally administered `local-mac-address` (`02:00:01:48:00:01`, `02:00:02:48:00:01`). The platform expert publishes every `/arm-io` child but `gic` as a nub (patch 0046), so `IONameMatch wlan` finds it. sweet's ADT is unchanged. Image `out/new/alioth-m5-v3-cpus4-noconsole-wlan.img` (`b7b74fe1...`), same diagnostics boot-args. Not booted yet.

### 2026-11-19  boot 12: M5, sampling lsd
- Image: `out/new/alioth-m5-v3-cpus4-noconsole-smplsd.img` (sha256 `bd2a1c14...`): boot 11 + `sweetsample=lsd,SpringBoard`. Cold start, `fastboot boot` at 18:34:44; Apple logo until 18:47; log `logs/boot12-m5.txt`.
- lsd[97] (slide 0x3660c000), the same in all 6 samples, symbolicated:
  - t0: `__LSServerMain` -> `+[_LSInstallProgressService beginListening]` -> `-[_LSInstallProgressService performJournalRecovery]` -> `dispatch_sync`, waiting.
  - t5: `__LAUNCH_SERVICES_CLIENTS_ARE_WAITING_FOR_THE_DATABASE_TO_FINISH_SEEDING__` (this is what SpringBoard waits for).
  - t6: `-[_LSInstallProgressService restoreInactiveInstalls]` -> `dispatch_group_wait`.
  - **t2, the seeding thread**: `-[MIInstalledInfoGatherer _populatePlaceholderRecordValues:signingInfo:]` -> `-[MIExecutableBundle installationIdentitySettingIfNotSet:]` -> `+[MIInstallationIdentity installationIdentityForBundle:settingIfNotSet:]` -> `_GenerateBuiltInAppInstallSessionID` -> libMobileGestalt (unnamed functions, recursive answer lookups) -> `dispatch_semaphore_wait`. t1 runs a libMobileGestalt CFRunLoop waiting for a Mach message.
- So: **the LaunchServices database never finishes seeding because MobileGestalt never answers a question** asked while generating the built-in app install session ID; the answer it waits for arrives through an IOKit notification or a Mach service. Which MobileGestalt key it is needs the disassembly (`ipsw dyld disass` ran out of memory in WSL) or the IOKit calls lsd makes (`sweetiolog=lsd`, patch 0054, boot-arg only).

### 2026-11-19  boot 11: M5 without console text
- Image: `out/new/alioth-m5-v3-cpus4-noconsole.img` (sha256 `0065d9c4...`): boot 10 + `sweetfb_noconsole=1`. Cold start (`adb shell reboot -p` from OrangeFox, Volume Down + Power), `fastboot boot` at 18:16:43.
- Result: **the Apple logo stays up**, still at 18:28 (12 min). Power + Volume Down, OrangeFox, log pulled read-only (`logs/boot11-m5.txt`, flush #76).
- Log: only 3 framebuffer swaps (the logo); SpringBoard[26] and backboardd[56] alive; the same bluetoothd / fairplayd.H2 restart cycle and touch `err=94` for the whole run; `CRASH driverkitd[66] sig 9` once; sandbox denials (rapportd 12000, logd 1002, symptomsd 10003, identityservicesd 12001). **Buttons work**: `SWEET KEYS: key=0 down=1` / `key=2` -> `SWEET HID: key 0x30 / 0xea down (1 clients)` (the Power + Volume Down press).
- SpringBoard's main thread is in the same place in every sample (`t0 pc 0x1c9795ad0`, slide 0x7184000, deep synchronous stack), while backboardd's main thread sits in its run loop: **SpringBoard is blocked waiting for something** before it draws the lock screen. Symbolicating that stack (`tools/sweet-crash.py` needs `ipsw` and the shared cache from the root image) tells what it waits on; a crash-looping daemon (bluetoothd, fairplayd.H2) is the first suspect.
- Symbolicated (`ipsw` 3.1.749 `dyld a2s`, shared cache from the image, slide 0x7184000). SpringBoard t0, the same in all 6 samples:
  ```
  os_unfair_lock_lock_slow + 172
  _LSContextInitCommon(LSContext*, _LSDServiceDomain*, ...) + 212
  _LSContextInitWithOptions + 12
  LaunchServices::Database::Context::_get + 108
  -[LSApplicationRecord initWithBundleIdentifier:allowPlaceholder:error:] + 52
  -[CCSModuleRepository _queue_filterModuleMetadataByAssociatedBundleAvailability:] block + 84
  -[CCSModuleRepository _queue_updateAllModuleMetadata] + 56
  -[CCSModuleRepository _initWithDirectoryURLs:allowedModuleIdentifiers:] + 332 (dispatch_sync)
  ```
  SpringBoard builds its Control Center module list, asks LaunchServices for an app record and waits on the LaunchServices database lock: the database (from lsd, started once, no crash) never becomes available. lsd is not sampled by default; the sampler takes the boot-arg `sweetsample=` (patch 0054), so `sweetsample=lsd,SpringBoard` shows where lsd is, with no kernel rebuild.

### 2026-11-19  boot 10: M5, iOS userland from userdata
- Image: `out/new/alioth-m5-v3-cpus4.img` (sha256 `04a51c41...`), root `ios16-root.simg` on userdata. Cold start (`adb shell reboot -p` from OrangeFox, Volume Down + Power), `fastboot boot` at 18:07:25.
- Result (in progress, `photos/boot10-m5-*.jpg`): shim `RAM ok: in a memory bank, not reserved`; 4/4 CPUs; the root is found and **iOS userland runs**: launchd starts daemons (`exec xpcproxy`, securityd, sharingd, mediaserverd, bioned, contactsd, fairplayd.H2, spindump, assetsd, suggestd, searchpartyd, bluetoothd, medialibraryd, symptomsd-diag ...), backboardd keeps matching `IOAcceleratorES`, AppleKeyStore calls answered. **The Apple logo appeared briefly**, then a dark screen with a small white shape in the centre, kernel text still drawn over it (no `sweetfb_noconsole`).
- `ALIOTH TOUCH: report err=94 irq=0x1c000001`: the touch driver gets interrupts but a report read fails (94 = EBADMSG, probably the CRC check). First run of patch 0086 on the phone.
- `SWEET Sandbox: (aggregated) privilege 1002 denied` for symptomsd.
- ~5 min in (`-d.jpg`): `SMP` thread samples of backboardd (t5-t15) and **SpringBoard[26]** (patch 0054 sampler, not a crash), then a repeating cycle `exec xpcproxy / fairplayd.H2 / bluetoothd` with `ALIOTH TOUCH: report err=94 irq=0x4c000081` each round: fairplayd and bluetoothd restart over and over. No lock screen visible under the console text.
- Log pulled read-only from OrangeFox (`logs/boot10-m5.txt`, 150 KB, ring flush #28; `tools/sweet-log-pull.sh` steps by hand, `/dev/block/sda35` last 1025 blocks):
  - `SWEET UFS: "userdata" on LUN 0: first block 0x2a8000, 108847 MiB, read-write`, `BSD root: ufsroot0`; launchd 7.0.0 boot tasks run (mount-phase-1/2, data-protection, ...).
  - Display: backboardd opens the framebuffer (`SWEET FB: display on`), creates two 1125x2436 BGRA surfaces and swaps **6 frames** (the Apple logo), then no more swaps in the flushed part of the log. SpringBoard[26] runs (AKS calls, sampler) but has not drawn a lock screen yet.
  - `CRASH driverkitd[67] sig 9` once; bluetoothd restarted 28 times and fairplayd.H2 as often (no matching hardware).
  - Touch: init works on the phone: `TLMM reset/irq`, GENI SE4 fw 0x101, `chip id err=0/0 56:52 fw=0x1d`, `FT3658U ready`. Every report read (`at_read(0x01, ...)`, the long read) fails the CRC-16 check (`err=94` EBADMSG) after 3 tries; the 1-byte reads (0xa3, 0x9f, 0xa6) pass. So the long-read framing or CRC span differs from the vendor driver on this chip; needs the received bytes and both CRCs printed once (kernel change).
- Next: same image with `sweetfb_noconsole=1` (boot-arg only) to see what iOS draws under the log; then a kernel build (GitHub CI) with touch read diagnostics.

### 2026-11-19  flash: iOS root to userdata (M5 step 3)
- With the owner's explicit go-ahead for this one command (no Android data kept): `fastboot -S 512M flash userdata ios16-root.simg` (sha256 `5759d761...`, 24 sparse chunks) 17:54:40-18:01:24, all OKAY, 403.6 s. `userdata` 0x1A92FFB000 bytes. Android's data is gone; going back means formatting userdata.
- Afterwards fastboot stopped answering `getvar` (as on sweet after a large flash). Power + Volume Down: fastboot again, screen dark (warm state). OrangeFox booted (`fastboot boot`, 18:03:23); read-only check: `/dev/block/sda35` sector 2 starts `HX` 00 05 (HFSX, case-sensitive): the image is on userdata. OrangeFox's own display driver also showed backlight only (no picture): the LCD stays dead after a warm reset until a power cut. With the owner's OK: `adb shell reboot -p` (18:06:58), then Volume Down + Power from off.

### 2026-11-19  boot 09: M4, all 8 CPUs
- Image: `out/new/alioth-m3-v3-cpus8.img` (sha256 `3c29b49f...`): as boot 08 with `cpus=8`. Android -> power off -> Volume Down + Power, `fastboot boot` at 15:44:45, slot `_b`.
- Changed: `cpus=4` -> `cpus=8`.
- Result: **8/8 CPUs up** (`photos/boot09-m4-cpus8-a.jpg` shim screen, `-b.jpg` kernel log):
  ```
  SWEET CPU: requested=8 selected=8 (limit=8)
  SWEET CPU: cpu=N CPU_ON target=0xN00 entry_pa=0x18148e000 context=N; PSCI CPU_ON rc=0   (N = 1..7)
  arm_cpu_init(): cpu N online; entered initCPU mpidr=0xN00 EL1; came alive; SGI1 OK
  SWEET CPU: 8/8 CPUs initialized, SGI1 verified
  ml_processor_register: cpu_number 6, 7 ... cluster_id 0, type 0
  ```
  Shim screen: `INTF1 f0=1D4 f+100ms=1DA` (60 Hz again), `INITRD lo=ADFBD000 hi=AFFFEB19`.
- Reading: the A77 cores 4-6 and the prime core 7 start through PSCI like the A55s, and each takes SGIs. All 8 are registered as one cluster of one type (the ADT gives every CPU `qcom,kryo470`): fine for now; a separate performance cluster is later work.
- Last screen (`-c.jpg`): `mcache: 8 CPU(s)`, all Skywalk and DLIL self-tests PASSED, then `Waiting on <dict ...IOMedia ... Apple_HFS ...>` and `Failed to write boot-picker-bringup-reason to NVRAM.` (no NVRAM on this board; harmless). **M4 done.**
- Next: M5 (root file system) needs the iOS image and the decision about userdata.

### 2026-11-19  boot 08: M4, 4 CPUs (the Cortex-A55 cluster)
- Image: `out/new/alioth-m3-v3-cpus4.img` (sha256 `4a4f9932...`): as boot 07 with boot-args `cpus=4`. `fastboot boot` at 15:40:09, slot `_b`.
- Changed: `cpus=1` -> `cpus=4`.
- Result: **4/4 CPUs up**, then the same root wait as boot 07 (`photos/boot08-m4-cpus4.jpg`; the console had wrapped, so the CPU 1-3 lines sit at the bottom and top):
  ```
  SWEET CPU: cpu=2 CPU_ON target=0x200 entry_pa=0x18148e000 context=2
  SWEET CPU: cpu=2 PSCI CPU_ON rc=0
  arm_cpu_init(): cpu 2 online
  SWEET CPU: cpu=2 entered initCPU mpidr=0x200 EL1 IRQs=0
  SWEET CPU: cpu=2 mpidr=0x200 came alive; SGI1 OK
  (cpu=1 mpidr=0x100 and cpu=3 mpidr=0x300 the same)
  SWEET CPU: 4/4 CPUs initialized, SGI1 verified
  mcache: 4 CPU(s), 64 bytes CPU cache line size
  Waiting on <dict ...IOMedia ... Apple_HFS ...>
  ```
- Reading: PSCI `CPU_ON` works on alioth's firmware (rc=0), the secondaries start at the entry point inside our RAM range (`0x18148e000`), the MPIDRs 0x100-0x300 match the device tree, and the GIC delivers SGIs to each.
- Next: `cpus=8` (adds the Cortex-A77 cores 4-6 and the A77 prime core 7, a second cluster).

### 2026-11-17  boot 07: M3, first XNU start on alioth
- Image: `out/new/alioth-m3-v3.img` (sha256 `63c13d55...`): shim as boot 06, kernel `aebaed8` (kernel branch, `kernel.development.sweet` sha256 `604d21f2...`), ADT `--board alioth --highmem` (RAM `0x180000000` +3 GiB), boot-args `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress wdt=-1`. Cold start (Android power off, Volume Down + Power), `fastboot boot` at 23:51:51, slot `_b`.
- Changed: first M3: XNU with the new RAM range and the no-writes display path.
- Result: **M3 passed.** The XNU log, white on black, filled the screen and ended at the root wait (`photos/boot07-m3-a.jpg` earlier, `-b.jpg` last):
  ```
  zone_init: map VM/RO/GEN0-3/DATA ... VM bootstrap done: 85 maps, 165 entries and 502 holes left
  iBoot version: sweet-shim
  SWEET: starting device-tree platform expert / platform expert registered
  SWEET AKS, WDT, SURF, HID buttons, HID touch registered
  SWEET BATTERY: static fallback, 100% 4200mV external=1 charging=0
  SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1, presented as 1125x2436
  SWEET CPU: cpu=0 mpidr=0x0 came alive; SGI1 OK ... 1/1 CPUs initialized, SGI1 verified
  MAC Framework successfully initialized; SWEET AMFI, Sandbox, HFS registered
  mbinit: done [64 MB total pool size, (42/21) split]
  Skywalk self-tests ... PASSED; DLIL SUM16 self-tests ... PASSED
  bsd_autoconf: calling kminit; ifnet_attach lo0, gif0, stf0
  Waiting on <dict ID="0"><key>IOProviderClass</key><string ID="1">IOMedia</string><key>Content</key><string ID="2">Apple_HFS</string></dict>
  ```
- Reading:
  - **XNU runs on alioth**: the RAM range at `0x180000000` is accepted (zone maps sized from 3 GiB), the virtual timer (INTID 27) and the GIC work (scheduler runs, kernel threads get scheduled, SGI1 verified), the board's platform expert and SWEET drivers attach. It gets past "ATM subsystem is initialized" and `skmem_region_init`, where QEMU stopped.
  - **Display without kicks**: XNU's framebuffer console writes to `0x9c000000` and the LCD shows it, with no `sweetkick=`.
  - The stop is the expected one: there is no root file system (the M3 image carries none).
- Power + Volume Down: fastboot at 23:57:02. End of session: phone back in Android (MTP seen at 00:04).
- Next: root file system (M4+), more CPUs (`--cpus`), a hard reset in the shim so tests do not need a power-off.

### 2026-11-17  boot 06: M1 from a cold start
- Image: `out/new/alioth-m1-v3.img` (sha256 `4dedef42...`, same as boot 05). Before it: `fastboot reboot` to Android, power off, Volume Down + Power. `fastboot boot` at 23:47:15, slot `_b`.
- Changed: only the start: cold instead of after our reset.
- Result: **M1 passed with the full image.** Back in fastboot by itself at 23:50:45 (23:47:15 + 200 s = 23:50:35). Red console, all text (`photos/boot06-m1.jpg`):
  ```
  DISP   no tear check: no writes
  DISP   ctl=00000000 pp=FFFFFFFF
  CTL    top=00020000 intf=00000002 dsc=00000001 status=00000001
  INTF1  frames=000000A8 status=00000000
  INTF1  f0=00000095 f+100ms=0000009B
  SSPP   off=00005000 addr=9C000000 size=09600438 stride=000010E0 fmt=000237FF
  UFS    utrlba=9B144000 (boot 03: 9B143000), all else as boot 03
  ```
- Reading:
  - **The warm start was the problem in boots 04-05, not the shim.** After our reset ABL's own FASTBOOT screen stays dark, and nothing drawn reaches the panel. **Each test needs a cold start** (Android power off, then Volume Down + Power) until the reset is changed.
  - **INTF_1's frame counter does move** from a cold start: +6 in 100 ms = 60 Hz, the LCD's refresh rate. So the path runs like video mode, and boot 04's static counter was another sign of the dead warm state. The "no tear-check pingpong: no writes" rule stays: it matches boots 03 and 06.
- Next: M3 (`out/new/alioth-m3-v3.img` `63c13d55...`) from a cold start. Later: make the shim's reset a PMIC hard reset (PS_HOLD reset type) instead of a warm one, so the display comes back without a power-off.

### 2026-11-17  boot 05: M1, no writes without a tear-check pingpong
- Image: `out/new/alioth-m1-v3.img` (sha256 `4dedef42...`), shim `691cebb` + local `display.c` change, built on Windows. `fastboot boot` at 23:43:39, slot `_b`. Fastboot had been reached by the shim's own reset (boot 04), not from power-off.
- Changed: no display writes whenever no pingpong is in tear-check mode (same writes as boot 03's `--disp none`, plus a 100 ms wait).
- Result: screen blank (no photo). Back in fastboot at **23:45:02, only 83 s after the boot**, because Power + Volume Down was held (a full run takes ~200 s).
- Reading (open): the display code now matches boot 03, so suspect the warm start. Boots 04-05 started from a fastboot reached by our reset; boot 03 from fastboot entered from power-off. Boot 01 already showed Android's screen staying dark after a warm reset. After this boot ABL's own FASTBOOT screen was dark too (PC saw `PID_D00D` at 23:46:18), so the display stays dark after the warm reset with none of our code running. `fastboot reboot` to Android at 23:46:29.
- Next: full power-off, fastboot with Volume Down + Power, same image again.

### 2026-11-17  boot 04: M1, "no writes when INTF_1 counts frames"
- Image: `out/new/alioth-m1-v3.img` (sha256 `568ac0fc...`, since overwritten), shim `691cebb` + local `display.c` change, built on Windows. `fastboot boot` at 23:39:33, slot `_b`.
- Changed: `disp_init` skipped all writes only if INTF_1's frame counter moved over 100 ms with no tear-check pingpong.
- Result: screen blank (no photo). The phone came back in fastboot by itself at 23:43:03 (23:39:33 + 200 s = 23:42:53): the shim ran to the end and the PMIC reboot reason works again.
- Reading: the counter did not move, so the shim fell back to `CTL_START` kicks, and the panel went black as in boots 01-02. INTF_1's frame counter does not show that this path refreshes by itself (boot 03 only showed one value, 0x369). **Corrected by boot 06:** this boot started from a fastboot reached by our warm reset, where the display path is dead anyway; from a cold start the counter moves at 60 Hz.
- Next: write nothing whenever no pingpong is in tear-check mode, and print the counter twice, 100 ms apart (`out/new/alioth-m1-v3.img` `4dedef42...`, `alioth-m3-v3.img` `63c13d55...`).

### 2026-11-17  boot 03: M1 shim, display read-only (`--disp none`)
- Image: `out/new/alioth-m1-v3-dispnone.img` (sha256 `b06d4956...`, header v3, no payload; shim from local commit `691cebb`, built on Windows with `tools/build-alioth-win.py`, Arm GNU Toolchain 14.2.Rel1). `fastboot boot` at 23:33:57, slot `_b`.
- Changed: the shim writes nothing to the display controller (`DISP_TEST=1`); first boot with the PMIC reboot reason (PON `SOFT_RB_SPARE`).
- Result: **M1 passed.** The red console screen with all text readable (`photos/boot03-m1-dispnone-a.jpg`, `-b.jpg`). The phone came back **in fastboot by itself** at 23:37:27 (USB watcher: `PID_D00D`), no buttons pressed.
- What the screen showed:
  ```
  DISP   test none: read only
  DISP   ctl=00000000 pp=FFFFFFFF
  CTL    top=00020000 intf=00000002
  CTL    dsc=00000001 status=00000001
  CTL    flush=00000000 start=00000000
  INTF1  frames=00000369 status=00000000
  SSPP   off=00005000 addr=9C000000
  SSPP   size=09600438 stride=000010E0
  SSPP   fmt=000237FF fb?=00000001
  CONSOLE 000000009C000000
  INITRD lo=AEF94000 hi=AFFFE51E
  LOADER no SWEETXNU payload
  UFS    ver=00000300 cap=1587031F hce=00000001 hcs=0000010F
  UFS    TUR/CAP/READ rc=0, LUN0 lastlba=01D3AFFF blk=00001000
  UFS    MBR sig=AA55 type=EE, GPT entries=0x40 lba=2
         persist 0xA000, persistbak 0xE000, logdump 0x14000, minidump 0x18000,
         rawdump 0x1E000, exaid 0x26000, cust 0x3E000 (ext4), super 0x7E000,
         rescue 0x2A0000, userdata 0x2A8000 (0x1A92F MiB, fs other)
  UFS    probe done, reset in ~3 min
  ```
- Reading:
  - **Display:** with no writes at all, text drawn into ABL's splash buffer (`0x9c000000`, pipe `0x5000`, 1080x2400, 4320-byte stride) appears. So the controller scans that buffer continuously by itself; a command-mode panel would have kept ABL's last frame. With this replacement LCD the path behaves like **video mode**: `pp=FFFFFFFF` (no pingpong in tear-check mode) and `INTF1 frames` counting. In boots 01-02 the full sequence took the "no tear-check pingpong" branch, which writes no autorefresh but does write `CTL_START` once at init and once per draw, so **the `CTL_START` kicks blanked this panel**.
  - **Reboot reason fixed:** the PMIC `SOFT_RB_SPARE` write makes ABL stop in fastboot. 23:33:57 + 180 s + 20 s = 23:37:17, fastboot at 23:37:27.
  - **UFS** read-only probe: LUN 0 GPT read with no errors; `userdata` start and size agree with the M0 scan.
- Next: the shim makes no display writes when the path is already scanning by itself (no tear-check pingpong and the INTF frame counter moving), passes no `sweetkick=`, then M1 (full) to confirm, then M3 with the `0x180000000` RAM range.

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
