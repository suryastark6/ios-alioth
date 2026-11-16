# ios-alioth

**Porting Apple's iOS 16 to the POCO F3 / Redmi K40 / Mi 11X (`alioth`, Snapdragon 870).**

This project builds on [ios-sweet](https://github.com/dipa-studio/ios-sweet) by dipa-studio. ios-sweet runs the unmodified iPhone X iOS 16.7.16 userland on the Redmi Note 10 Pro (`sweet`, SM7150) up to the home screen, on Apple's open-source XNU kernel. ios-alioth takes that kernel, boot shim and tooling and adapts the phone-specific layer to alioth.

> **Status: bring-up prepared, nothing has booted on alioth yet.** Don't expect a working image. The board configuration is filled in from alioth's device tree source, and the first test images (shim with a command-mode display probe; kernel with alioth key wiring) build. Nothing has been tested on a phone. Each milestone is updated as it boots on real hardware.

## Plan

The full milestone plan is in [docs/ALIOTH-PLAN.md](docs/ALIOTH-PLAN.md). In short:

| # | Milestone | State |
| --- | --- | --- |
| M0 | Back up the phone, read its live device tree, confirm every address | values from source done; needs the phone for RAM size |
| M1 | Our shim boots through `fastboot boot` (boot image format, watchdog, return to fastboot) | image builds; needs the phone |
| M2 | Picture and log (framebuffer; command-mode AMOLED panel refresh) | shim autorefresh/kick written; needs the phone |
| M3 | XNU starts (memory map, GIC, timer) | to do |
| M4 | All 8 cores (A55 + A77) | to do |
| M5 | UFS root: launchd and the Apple logo | to do |
| M6 | Lock screen and home screen | to do |
| M7 | Touch (FT3658U on SPI) and buttons (PM8150) | buttons done (patch 0082); touch to do |
| M8 | USB live log, battery, display power | to do |

Hardware facts with sources: [docs/ALIOTH-HARDWARE.md](docs/ALIOTH-HARDWARE.md). Boot logs and findings go in [NOTES.md](NOTES.md).

## What is different from ios-sweet

- `tools/boards/`: per-phone hardware descriptions. `tools/mkadt.py --board alioth` builds the Apple Device Tree from `tools/boards/alioth.py`. It refuses to build while any required value is still unknown. `--board sweet` (the default) produces byte-identical output to upstream.
- `shim/board.h`: the shim's physical addresses and timer interrupts per phone. Build with `BOARD=alioth DTB=path/to/stock.dtb shim/build.sh PAYLOAD`.
- `shim/display.c`: alioth's AMOLED is a command-mode panel, which only shows a new image when the display controller sends a frame. The shim turns on autorefresh before anything is drawn, falls back to one frame per draw, and prints the display state ABL left.
- `xnu/patches/0082`: the key driver reads the volume-up GPIO from the device tree (alioth: PM8150 GPIO6). Without the node, sweet's wiring is unchanged.
- `tools/fdt-scan.py`: reads a live device tree and prints everything a port needs, such as memory banks and carve-outs, splash framebuffer, panel mode, GIC, timer, CPUs, UFS, touch bus and buttons. It also suggests values for `tools/boards/alioth.py`.
- `tools/alioth-backup.sh`: from OrangeFox/TWRP, backs up `persist`, modem partitions, `boot`, `dtbo`, `vbmeta`, `vendor_boot` and pulls the live device tree.
- `tools/unpack_bootv2.py`: now stops with a clear message on boot header v3/v4 instead of misreading them.

The kernel patches, iOS root image tooling and diagnostics are unchanged from ios-sweet so far. The original documentation is in [docs/SWEET-README.md](docs/SWEET-README.md), and the full upstream engineering log is the [ios-sweet NOTES.md](https://github.com/dipa-studio/ios-sweet/blob/main/NOTES.md).

## Getting started (M0)

You need a POCO F3 / Redmi K40 / Mi 11X with an **unlocked bootloader**, a Linux PC with `adb`, `fastboot`, `python3`, `dtc` and `aarch64-linux-gnu-gcc`, and OrangeFox or TWRP for alioth.

```sh
fastboot boot orangefox-alioth.img          # temporary, nothing is flashed
tools/alioth-backup.sh backup/              # partitions + dtb/alioth-live.dtb
python3 tools/fdt-scan.py dtb/alioth-live.dtb
```

Compare the output with the `SRC` values in `tools/boards/alioth.py` and `shim/board.h`, fill in the RAM bank (`high_phys_base`, `high_mem_size`), and record the scan in `NOTES.md`. Then continue with M1 in the plan.

> Installing iOS (M5) erases Android's `userdata`. Keep your `backup/` folder safe. `persist` and the modem partitions hold calibration data that can't be downloaded anywhere.

## Building

Unchanged from ios-sweet (see [docs/SWEET-README.md](docs/SWEET-README.md), sections 1-3), with the board selected:

```sh
# kernel: GitHub Actions on your fork
gh workflow run xnu.yml -R YOU/ios-alioth
# device tree and boot image
python3 tools/mkadt.py shim/out/alioth.adt --board alioth --highmem
python3 tools/mkpayload.py xnu/out/kernel.development.sweet shim/out/alioth.adt shim/out/payload.bin --cmdline '... cpus=1 ...'
(cd shim && BOARD=alioth DTB=../dtb/boot_unpacked/dtb ./build.sh ../shim/out/payload.bin)
```

## Contributing

Results from real phones are the most useful contribution. Please include your variant (global, `aliothin`, K40), RAM size, the milestone you reached, the `fdt-scan.py` output (without serial numbers) and the relevant log lines. Never commit partition backups, live device trees, Apple firmware or iOS images. `.gitignore` already excludes `backup/`, `dtb/`, `recovery/` and `research/`.

## Credits

- [ios-sweet](https://github.com/dipa-studio/ios-sweet) by dipa-studio and contributors: the kernel port, shim, drivers and tooling this project is built on (MIT).
- Apple's open-source releases (xnu, IOHIDFamily, libpthread, hfs), [BearSSL](https://bearssl.org), [blacktop/darwin-xnu-build](https://github.com/blacktop/darwin-xnu-build), [ipsw](https://github.com/blacktop/ipsw).
- The [postmarketOS alioth notes](https://wiki.postmarketos.org/wiki/Xiaomi_POCO_F3_/_Redmi_K40_/_Mi_11X_(xiaomi-alioth)) and Xiaomi's published kernel sources for hardware details.

iOS is Apple's software and is not distributed here.
