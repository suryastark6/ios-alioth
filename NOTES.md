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

## Boot log

<!--
### YYYY-MM-DD  boot NN: <short title>
- Image: shim/out/...  kernel ...  ADT ...  boot-args ...
- Changed: (one thing)
- Result:
- Next:
-->
