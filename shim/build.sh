#!/bin/bash
# Build the shim and wrap it in a boot.img v2 that mirrors the stock PixelOS header.
#   BOARD=sweet|alioth (default sweet) selects the addresses in board.h.
#   DTB=path (default ../dtb/boot_unpacked/dtb): the phone's stock DTB from
#   tools/unpack_bootv2.py or tools/unpack_vendor_boot.py; ABL needs the DTB
#   it expects for this phone.
#   HEADER=2|3 (default 2): boot image header version. 3 = no DTB in the
#   image; ABL uses the phone's vendor_boot (Virtual A/B phones like alioth).
set -euo pipefail
cd "$(dirname "$0")"
CC=aarch64-linux-gnu-gcc
OBJCOPY=aarch64-linux-gnu-objcopy
BOARD=${BOARD:-sweet}
DTB=${DTB:-../dtb/boot_unpacked/dtb}
HEADER=${HEADER:-2}	# 3: boot image v3, DTB from the phone's vendor_boot (alioth)
case "$HEADER" in 2|3) ;; *) echo "error: HEADER=$HEADER (2 or 3)" >&2; exit 1 ;; esac
if [ "$HEADER" = 2 ] && [ ! -f "$DTB" ]; then echo "error: DTB=$DTB not found" >&2; exit 1; fi
case "$BOARD" in
	sweet) BOARD_DEF= ;;
	alioth) BOARD_DEF=-DBOARD_ALIOTH ;;
	*) echo "error: unknown BOARD=$BOARD (sweet, alioth)" >&2; exit 1 ;;
esac
CFLAGS="$BOARD_DEF -O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c display.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done
# The image runs wherever ABL puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$(aarch64-linux-gnu-readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o out/display.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o out/display.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$((0x$(aarch64-linux-gnu-nm out/shim.elf | awk '$3=="_end"{print $1}')))
truncate -s "$size" out/Image
# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty
# newc cpio (ABL dislikes a zero-size ramdisk on some builds) -> diagnostics.
if [ -n "${1:-}" ]; then
	cp "$1" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi
if [ "$HEADER" = 3 ]; then
	# v3: no DTB here; ABL takes it (and the vendor ramdisk, placed before
	# ours) from the phone's own vendor_boot. loader.c finds the payload.
	mkbootimg --header_version 3 --kernel out/Image --ramdisk out/ramdisk.bin \
		--os_version 17.0.0 --os_patch_level 2035-06 \
		--cmdline "console=null" -o out/shim-boot.img
else
	mkbootimg --header_version 2 --kernel out/Image --ramdisk out/ramdisk.bin \
		--dtb "$DTB" --base 0 --kernel_offset 0x8000 --ramdisk_offset 0x1000000 \
		--tags_offset 0x100 --dtb_offset 0x1f00000 --pagesize 4096 \
		--os_version 17.0.0 --os_patch_level 2035-06 \
		--cmdline "console=null" -o out/shim-boot.img
fi
# Host render of the console layout.
gcc -O1 -Wall -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image out/shim-boot.img
