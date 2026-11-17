# alioth working notes

One entry per boot: what changed, what happened, what is next. Newest on top.
For the full history of the sweet bring-up this port is built on, see the
[ios-sweet NOTES.md](https://github.com/dipa-studio/ios-sweet/blob/main/NOTES.md).

## Test phone

| | |
| --- | --- |
| Variant | (global POCO F3 / Mi 11X `aliothin` / Redmi K40) |
| RAM / storage | |
| Stock firmware | (MIUI / HyperOS version) |
| Boot header version | (from `unpack_bootv2.py` / `unpack_bootimg.py`) |
| Panel | (`dsi_display0` from `fdt-scan.py`; cmd or video mode) |
| Touch | (compatible, SPI SE, supplies) |

## M0: hardware description

Paste the `tools/fdt-scan.py dtb/alioth-live.dtb` output here (remove serial numbers).

## Build log

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

<!--
### YYYY-MM-DD  boot NN: <short title>
- Image: shim/out/...  kernel ...  ADT ...  boot-args ...
- Changed: (one thing)
- Result:
- Next:
-->
