# alioth hardware facts

Everything the port needs to know about the board, with where each value comes from.

**SRC** means the value was read from alioth's device tree source, before any phone was used. That source is LineageOS [`android_kernel_xiaomi_sm8250`](https://github.com/LineageOS/android_kernel_xiaomi_sm8250) (branch `lineage-24.0`), `arch/arm64/boot/dts/vendor/qcom/`, built as `kona-v2.1.dtb` with `alioth-sm8250-overlay.dtbo` applied, which is how ABL assembles it. Driver details come from Xiaomi's own [`Xiaomi_Kernel_OpenSource`](https://github.com/MiCode/Xiaomi_Kernel_OpenSource) branch `alioth-r-oss`. **LIVE** means it was confirmed on a phone with `tools/fdt-scan.py` (none yet).

To reproduce the SRC tree:

```sh
cpp -nostdinc -undef -x assembler-with-cpp -D__DTS__ -I <kernel>/include \
    -I <kernel>/arch/arm64/boot/dts/vendor/qcom kona-v2.1.dts > base.dts
cpp ... alioth-sm8250-overlay.dts > overlay.dts
dtc -@ -I dts -O dtb -o base.dtb base.dts
dtc -@ -I dts -O dtb -o overlay.dtbo overlay.dts
fdtoverlay -i base.dtb -o alioth-src.dtb overlay.dtbo
python3 tools/fdt-scan.py alioth-src.dtb
```

## Core

| What | Value | Source | sweet |
| --- | --- | --- | --- |
| SoC | SM8250-AC (kona v2.1), board-id 44 | SRC | SM7150 |
| CPUs | 8, MPIDR `0x000`-`0x700`; 0-3 A55, 4-7 A77 (capacity 1024 / 1894) | SRC | same MPIDR scheme |
| PSCI | `smc` | SRC | same |
| GIC | v3, GICD `0x17a00000` +`0x10000`, GICR `0x17a60000` +`0x100000` | SRC | same |
| Timer | 19.2 MHz; PPIs 13/14/11/12, so **virtual = INTID 27**, physical = 30 | SRC | 19 / 18 |
| Reset | PS_HOLD `0x0c264000`; IMEM restart reason `0x146bf65c` | SRC | `0x146aa65c` |
| UFS | `ufshc@1d84000` +`0x3000` (also `ufshc_card@1da4000`, unused) | SRC | same |

## Memory

ABL fills in the memory node at boot, so the RAM banks are **LIVE only**. Fixed carve-outs (SRC):

- `0x80000000`-`0x9e400000`: hyp, XBL/AOP, smem, removed region, PIL firmware (camera, WLAN, IPA, GPU, NPU, video, CVP, CDSP, SLPI, ADSP, SPSS), CDSP secure heap, `cont_splash` (`0x9c000000` +`0x2300000`), `dfps_data` (`0x9e300000` +1 MiB)
- `0xb0400000` +16 MiB: `disp_rdump_region` (no-map). This overlaps sweet's low RAM choice (`0xb0000000`), so the low option is not used on alioth.
- Dynamic pools (ADSP, SDSP, CDSP, qseecom, secure display, CNSS, CMA and others) are placed by Linux within `alloc-ranges` that end at `0xffffffff`.

Nothing fixed sits above 4 GiB, so the bank at `0x100000000` is the RAM candidate (`--highmem`), as on sweet. Its size comes from the live memory node.

## Display

| What | Value | Source |
| --- | --- | --- |
| Panel | `qcom,mdss_dsi_k11a_38_08_0a_dsc_cmd` (Samsung AMOLED) | SRC (the only k11a panel node) |
| Mode | **command mode**, DSC (slices 540x8, 2 per packet), 24 bpp | SRC |
| Size | 1080x2400 at 60, 90 and 120 Hz; 70x155 mm | SRC |
| TE | from the panel's TE pin | SRC |
| Splash buffer | `0x9c000000` +`0x2300000` | SRC |
| SDE (DPU) | `qcom,mdss_mdp@ae00000`; CTL `+0x2000 + 0x200n` (6), PP `+0x71000 + 0x800n` (6), INTF `+0x6b000 + 0x800n` (`dp, dsi, dsi, dp`: DSI0 = INTF_1), DSC `+0x81000 + 0x400n`, SSPP vig `0x5000/7000/9000/b000`, dma `0x25000/27000/29000/2b000` | SRC |
| Frame trigger | `CTL_START` (`+0x1c`) = 1; autorefresh = `PP_AUTOREFRESH_CONFIG` (`+0x30`) `BIT(31) \| frames` | Xiaomi `techpack/display/msm/sde/sde_hw_ctl.c`, `sde_hw_pingpong.c` |

A command-mode panel shows nothing new until a frame is sent. `shim/display.c` handles this: it finds the CTL that drives DSI0 and the pingpong with tear check on, turns autorefresh on, and falls back to one kick per draw. It also prints everything ABL left in place on the first boot.

## Input

| What | Value | Source |
| --- | --- | --- |
| Touch IC | FocalTech **FT3658U** (`focaltech,fts`), firmware `fw_ft3658_k11` | SRC + Xiaomi `drivers/input/touchscreen/focaltech_spi/` |
| Touch bus | **SPI** on GENI `spi@990000` (QUP0), chip select 0, 6 MHz | SRC |
| Touch GPIOs | IRQ TLMM 39, reset TLMM 33 | SRC |
| Touch power | `vdd`: PM8150A **L10** (RPMh `ldoc10`); `vcc_i2c`: PM8150A **L1** (`ldoc1`) | SRC |
| Power key | PM8150 (SID 0) PON `0x800`, KPDPWR | SRC (same as sweet) |
| Volume down | PM8150 (SID 0) PON `0x800`, RESIN | SRC (same as sweet) |
| Volume up | **PM8150 GPIO6** on SID 0 (block `0xc500`), active low | SRC (sweet: PM6150L GPIO2, SID 4) |
| SPMI arbiter | v5: core `0xc440000`, observer `0xe600000`, config `0xc40a000` | SRC (same as sweet) |

## Other

| What | Value | Source |
| --- | --- | --- |
| USB | primary DWC3 `ssusb@a600000` (same as sweet), second controller `a800000` | SRC |
| Battery | PM8150B, fuel gauge gen4, 4520 mAh profiles | SRC |
| Fingerprint | Goodix (side key), SPI | SRC |
| GPU | Adreno 650 | |
| Wi-Fi/BT | QCA6390 | |
